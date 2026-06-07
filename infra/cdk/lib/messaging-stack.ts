import { Stack, StackProps, Duration } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as sqs from "aws-cdk-lib/aws-sqs";

/**
 * MessagingStack — 抽出ジョブの非同期基盤（SQS + DLQ）。
 * 可視性タイムアウト 60s / maxReceiveCount 3 → DLQ（nfr-design BR/P-ASY）。
 */
export class MessagingStack extends Stack {
  public readonly extractionQueue: sqs.Queue;
  public readonly deadLetterQueue: sqs.Queue;

  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    this.deadLetterQueue = new sqs.Queue(this, "ExtractionDLQ", {
      queueName: "noshi-extraction-dlq",
      retentionPeriod: Duration.days(14),
      enforceSSL: true,
    });

    this.extractionQueue = new sqs.Queue(this, "ExtractionQueue", {
      queueName: "noshi-extraction",
      visibilityTimeout: Duration.seconds(60),
      enforceSSL: true,
      deadLetterQueue: { queue: this.deadLetterQueue, maxReceiveCount: 3 },
    });
  }
}
