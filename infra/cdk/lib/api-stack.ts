import { Stack, StackProps, Duration } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as apigw from "aws-cdk-lib/aws-apigatewayv2";
import { HttpLambdaIntegration } from "aws-cdk-lib/aws-apigatewayv2-integrations";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as sqs from "aws-cdk-lib/aws-sqs";
import * as s3 from "aws-cdk-lib/aws-s3";

interface ApiStackProps extends StackProps {
  table: dynamodb.Table;
  queue: sqs.Queue;
  imageBucket: s3.Bucket;
}

/**
 * ApiStack — BFF/API（API Gateway HTTP API + Lambda(FastAPI+Mangum)）。
 * 最小権限 IAM（必要な DynamoDB/SQS/S3 アクションのみ付与）。
 */
export class ApiStack extends Stack {
  constructor(scope: Construct, id: string, props: ApiStackProps) {
    super(scope, id, props);

    const apiFn = new lambda.Function(this, "BffFn", {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "app.lambda.handler", // Mangum(app)
      code: lambda.Code.fromInline(
        "def handler(event, context):\n    return {'statusCode': 200, 'body': 'placeholder'}\n"
      ), // 実体は backend/ を bundling（本 intent はインフラ骨子）
      timeout: Duration.seconds(15),
      memorySize: 256,
      environment: {
        NOSHI_TABLE: props.table.tableName,
        EXTRACTION_QUEUE_URL: props.queue.queueUrl,
        IMAGE_BUCKET: props.imageBucket.bucketName,
      },
    });

    // 最小権限（least privilege）
    props.table.grantReadWriteData(apiFn);
    props.queue.grantSendMessages(apiFn);
    props.imageBucket.grantReadWrite(apiFn);

    const api = new apigw.HttpApi(this, "NoshiHttpApi", {
      apiName: "noshi-api",
      corsPreflight: {
        allowOrigins: ["*"], // 本番はフロントのオリジンに限定
        allowMethods: [apigw.CorsHttpMethod.ANY],
        allowHeaders: ["*"],
      },
    });
    api.addRoutes({
      path: "/api/{proxy+}",
      methods: [apigw.HttpMethod.ANY],
      integration: new HttpLambdaIntegration("BffIntegration", apiFn),
    });
  }
}
