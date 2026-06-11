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
 * CatalogBatchStack — お返し品カタログの日次バッチ（スペック2026-06-11 §7）。
 * JST 5:00/17:00 に楽天API→スコアリング→LLM→カタログテーブル総入れ替え。
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
    // JST 5:00 = UTC 20:00（前日）/ JST 17:00 = UTC 8:00
    for (const [name, hour] of [["Morning", "20"], ["Evening", "8"]] as const) {
      new events.Rule(this, `CatalogJob${name}`, {
        schedule: events.Schedule.cron({ minute: "0", hour }),
        targets: [new targets.LambdaFunction(fn, { retryAttempts: 0 })], // リトライ0（手動再実行のみ）
      });
    }
  }
}
