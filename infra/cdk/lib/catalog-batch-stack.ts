import { Stack, StackProps, Duration } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as events from "aws-cdk-lib/aws-events";
import * as targets from "aws-cdk-lib/aws-events-targets";
import * as iam from "aws-cdk-lib/aws-iam";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import { backendLambdaCode } from "./lambda-code";

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
    const fn = new lambda.Function(this, "CatalogJob", {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "app.catalog.job.handler",
      code: backendLambdaCode(),
      timeout: Duration.minutes(15),
      memorySize: 1024,
      environment: { NOSHI_CATALOG_TABLE: props.catalogTable.tableName },
    });
    props.catalogTable.grantWriteData(fn); // バッチは書き込みのみ（IAM分離、スペック§8）
    fn.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["bedrock:InvokeModel"],
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
          `arn:aws:ssm:${this.region}:${this.account}:parameter/noshi/rakuten/*`,
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
