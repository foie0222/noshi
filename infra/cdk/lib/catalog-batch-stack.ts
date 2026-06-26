import { Stack, StackProps, Duration } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as path from "path";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as events from "aws-cdk-lib/aws-events";
import * as targets from "aws-cdk-lib/aws-events-targets";
import * as iam from "aws-cdk-lib/aws-iam";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";

// キュレーションは Claude Agent SDK（Node + claude CLI 同梱コンテナ）で実行する。
const BACKEND_DIR = path.resolve(__dirname, "../../../backend");
const LAMBDA_IMAGE_EXCLUDE = [".venv", "__pycache__", "**/__pycache__", "tests", ".pytest_cache"];

interface CatalogBatchStackProps extends StackProps {
  catalogTable: dynamodb.Table;
}

/**
 * CatalogBatchStack — お返し品カタログの日次バッチ（スペック2026-06-11 §7 / 2026-06-17 改）。
 * 用途63バケツ @ JST 9:00 / 品目84バケツ @ JST 9:20 の2ジョブ分割（15分制約マージン確保）。
 * 二重実行ガード: DynamoDB 条件付き書き込みのジョブロック（job.handler 内）＋
 * 非同期リトライ0。reserved concurrency はアカウントの同時実行数上限が小さく
 * 確保できないため使わない（最低 Unreserved 10 を割るとデプロイ不可）。
 */
export class CatalogBatchStack extends Stack {
  constructor(scope: Construct, id: string, props: CatalogBatchStackProps) {
    super(scope, id, props);
    const fn = new lambda.DockerImageFunction(this, "CatalogJob", {
      // Node + claude CLI 同梱コンテナ（backend/Dockerfile.lambda）。CMD をバッチハンドラに上書き。
      code: lambda.DockerImageCode.fromImageAsset(BACKEND_DIR, {
        file: "Dockerfile.lambda",
        cmd: ["app.catalog.job.handler"],
        exclude: LAMBDA_IMAGE_EXCLUDE,
      }),
      timeout: Duration.minutes(15),
      memorySize: 1024,
      environment: {
        NOSHI_CATALOG_TABLE: props.catalogTable.tableName,
        NOSHI_LLM_PROVIDER: "claude_agent",                  // キュレーションは Claude サブスク(OAuth)
        NOSHI_CLAUDE_TOKEN_SSM: "/noshi/claude/oauth-token", // OAuth トークン（SSM SecureString）
      },
    });
    props.catalogTable.grantWriteData(fn); // バッチは書き込みのみ（IAM分離、スペック§8）
    fn.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["bedrock:InvokeModel"],
        // NOSHI_LLM_PROVIDER=bedrock フォールバック時のみ使用。
        // クロスリージョン推論プロファイル（jp.）は inference-profile/* でカバー（api-stack と同一パターン）
        resources: [
          "arn:aws:bedrock:*::foundation-model/*",
          `arn:aws:bedrock:*:${this.account}:inference-profile/*`,
        ],
      }),
    );
    fn.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["ssm:GetParameter"],
        resources: [
          // 楽天 API 認証情報 + Claude OAuth トークン。
          `arn:aws:ssm:${this.region}:${this.account}:parameter/noshi/rakuten/*`,
          `arn:aws:ssm:${this.region}:${this.account}:parameter/noshi/claude/*`,
        ],
      }),
    );
    // 15分制約のマージン確保のため用途/品目を別ジョブに分割（Haiku運用）。
    // 用途63バケツ @ JST 9:00（UTC0:00）/ 品目84バケツ @ JST 9:20（UTC0:20）。別ロックIDで相互非ブロック。
    for (const [name, minute, set] of [
      ["Purpose", "0", "purpose"],
      ["Item", "20", "item"],
    ] as const) {
      new events.Rule(this, `CatalogJob${name}`, {
        schedule: events.Schedule.cron({ minute, hour: "0" }),
        targets: [
          new targets.LambdaFunction(fn, {
            retryAttempts: 0, // リトライ0（手動再実行のみ）
            event: events.RuleTargetInput.fromObject({ set }),
          }),
        ],
      });
    }
  }
}
