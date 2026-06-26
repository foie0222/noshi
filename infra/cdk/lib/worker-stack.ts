import { Stack, StackProps, Duration } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as path from "path";
import * as lambda from "aws-cdk-lib/aws-lambda";
import { SqsEventSource } from "aws-cdk-lib/aws-lambda-event-sources";
import * as iam from "aws-cdk-lib/aws-iam";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as sqs from "aws-cdk-lib/aws-sqs";
import * as s3 from "aws-cdk-lib/aws-s3";

// OCR は Claude Agent SDK（Node + claude CLI 同梱コンテナ）で実行する。
const BACKEND_DIR = path.resolve(__dirname, "../../../backend");
const LAMBDA_IMAGE_EXCLUDE = [".venv", "__pycache__", "**/__pycache__", "tests", ".pytest_cache"];

interface WorkerStackProps extends StackProps {
  table: dynamodb.Table;
  queue: sqs.Queue;
  imageBucket: s3.Bucket;
}

/**
 * WorkerStack — 抽出ワーカー Lambda（SQS イベントソース）。S3 の画像を OCR→DynamoDB 更新。
 * OCR は API Gateway の 30s 統合上限を超え得るため、API から切り離してここで実行する
 * （timeout 余裕あり）。Claude Agent SDK 利用のため Node + claude CLI 同梱コンテナで動かす。
 */
export class WorkerStack extends Stack {
  constructor(scope: Construct, id: string, props: WorkerStackProps) {
    super(scope, id, props);
    const worker = new lambda.DockerImageFunction(this, "ExtractionWorker", {
      code: lambda.DockerImageCode.fromImageAsset(BACKEND_DIR, {
        file: "Dockerfile.lambda",
        cmd: ["app.worker.handler"],
        exclude: LAMBDA_IMAGE_EXCLUDE,
      }),
      // OCR は ~8-20s + コンテナのコールドスタート余裕。SQS 可視性(180s)未満であること（SQS+Lambda 制約）。
      timeout: Duration.seconds(120),
      memorySize: 1024,
      environment: {
        NOSHI_TABLE: props.table.tableName,
        NOSHI_USE_DYNAMO: "1",
        NOSHI_IMAGE_BUCKET: props.imageBucket.bucketName,
        NOSHI_LLM_PROVIDER: "claude_agent",
        NOSHI_CLAUDE_TOKEN_SSM: "/noshi/claude/oauth-token",
      },
    });
    props.table.grantReadWriteData(worker);
    props.imageBucket.grantRead(worker); // S3 の撮影画像を読む
    worker.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["ssm:GetParameter"],
        resources: [`arn:aws:ssm:${this.region}:${this.account}:parameter/noshi/claude/*`],
      }),
    );
    // 1メッセージ=1OCR（遅い画像が他をブロックしない／SQS が並列にスケール）。
    worker.addEventSource(new SqsEventSource(props.queue, { batchSize: 1 }));
  }
}
