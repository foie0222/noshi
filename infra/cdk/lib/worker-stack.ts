import { Stack, StackProps, Duration } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as lambda from "aws-cdk-lib/aws-lambda";
import { SqsEventSource } from "aws-cdk-lib/aws-lambda-event-sources";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as sqs from "aws-cdk-lib/aws-sqs";
import { backendLambdaCode } from "./lambda-code";

interface WorkerStackProps extends StackProps { table: dynamodb.Table; queue: sqs.Queue; }

/**
 * WorkerStack — 抽出ワーカー Lambda（SQS イベントソース）。OcrLlmPort 実行→DynamoDB 更新。
 */
export class WorkerStack extends Stack {
  constructor(scope: Construct, id: string, props: WorkerStackProps) {
    super(scope, id, props);
    const worker = new lambda.Function(this, "ExtractionWorker", {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "app.worker.handler", // backend/app/worker.py
      code: backendLambdaCode(),
      timeout: Duration.seconds(30),
      memorySize: 512,
      environment: { NOSHI_TABLE: props.table.tableName, NOSHI_USE_DYNAMO: "1" },
    });
    props.table.grantReadWriteData(worker);
    worker.addEventSource(new SqsEventSource(props.queue, { batchSize: 5 }));
  }
}
