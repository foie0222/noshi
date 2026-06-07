import { Stack, StackProps, Duration } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as apigw from "aws-cdk-lib/aws-apigatewayv2";
import { HttpLambdaIntegration } from "aws-cdk-lib/aws-apigatewayv2-integrations";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as sqs from "aws-cdk-lib/aws-sqs";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as iam from "aws-cdk-lib/aws-iam";

interface ApiStackProps extends StackProps {
  table: dynamodb.Table;
  queue: sqs.Queue;
  imageBucket: s3.Bucket;
  userPoolId: string; // Cognito 世帯認証（JWT を RS256/JWKS で検証）
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
      handler: "app.lambda_handler.handler", // Mangum(app) — backend/app/lambda_handler.py
      // backend/ をアセット同梱（.venv/tests/キャッシュは除外）。本番デプロイ時は依存(fastapi/mangum/boto3)を
      // Lambda Layer もしくは bundling で同梱する（requirements.txt 参照）。
      code: lambda.Code.fromAsset("../../backend", {
        exclude: [".venv", "__pycache__", "**/__pycache__", "tests", ".pytest_cache", "*.md"],
      }),
      timeout: Duration.seconds(15),
      memorySize: 256,
      environment: {
        NOSHI_TABLE: props.table.tableName,
        EXTRACTION_QUEUE_URL: props.queue.queueUrl,
        IMAGE_BUCKET: props.imageBucket.bucketName,
        NOSHI_COGNITO_POOL_ID: props.userPoolId, // JWT 検証を Cognito に切替
        NOSHI_USE_BEDROCK: "1",                  // 実 OCR/LLM（Bedrock/Claude）
      },
    });

    // 最小権限（least privilege）
    props.table.grantReadWriteData(apiFn);
    props.queue.grantSendMessages(apiFn);
    props.imageBucket.grantReadWrite(apiFn);
    // Bedrock(Claude) 推論呼び出しのみ許可（OCR/礼状生成）
    apiFn.addToRolePolicy(new iam.PolicyStatement({
      actions: ["bedrock:InvokeModel"],
      resources: [`arn:aws:bedrock:${this.region}::foundation-model/*`,
                  `arn:aws:bedrock:${this.region}:${this.account}:inference-profile/*`],
    }));

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
