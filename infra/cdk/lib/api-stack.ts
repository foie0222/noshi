import { Stack, StackProps, Duration, CfnOutput } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as apigw from "aws-cdk-lib/aws-apigatewayv2";
import { HttpLambdaIntegration } from "aws-cdk-lib/aws-apigatewayv2-integrations";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as sqs from "aws-cdk-lib/aws-sqs";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as iam from "aws-cdk-lib/aws-iam";
import { backendLambdaCode } from "./lambda-code";

interface ApiStackProps extends StackProps {
  table: dynamodb.Table;
  queue: sqs.Queue;
  imageBucket: s3.Bucket;
  userPoolId: string; // Cognito 世帯認証（JWT を RS256/JWKS で検証）
  catalogTable: dynamodb.Table;
}

/**
 * ApiStack — BFF/API（API Gateway HTTP API + Lambda(FastAPI+Mangum)）。
 * 最小権限 IAM（必要な DynamoDB/SQS/S3 アクションのみ付与）。
 */
export class ApiStack extends Stack {
  public readonly apiUrl: string;

  constructor(scope: Construct, id: string, props: ApiStackProps) {
    super(scope, id, props);

    const apiFn = new lambda.Function(this, "BffFn", {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "app.lambda_handler.handler", // Mangum(app) — backend/app/lambda_handler.py
      code: backendLambdaCode(), // 依存ライブラリ込みでバンドル（fastapi/mangum/pyjwt 等）

      timeout: Duration.seconds(15),
      memorySize: 256,
      environment: {
        NOSHI_TABLE: props.table.tableName,
        NOSHI_USE_DYNAMO: "1",                   // 本番は DynamoDB 永続化（必須）
        EXTRACTION_QUEUE_URL: props.queue.queueUrl,
        NOSHI_IMAGE_BUCKET: props.imageBucket.bucketName, // #35: 撮影画像のS3バケット
        NOSHI_CATALOG_TABLE: props.catalogTable.tableName,

        NOSHI_USE_BEDROCK: "1",                  // 実 OCR/LLM（Bedrock/Claude）
        // 既定で Cognito 認証を強制（安全側、#101）。POOL_ID 注入で JWT(RS256/JWKS) 検証が有効になる。
        // デモ/ローカル等でスタブ認証(X-User-Id)を使う場合のみ context `allowStubAuth=true` を指定する。
        ...(this.node.tryGetContext("allowStubAuth") ? {} : { NOSHI_COGNITO_POOL_ID: props.userPoolId }),
      },
    });

    // 最小権限（least privilege）
    props.table.grantReadWriteData(apiFn);
    props.queue.grantSendMessages(apiFn);
    props.imageBucket.grantReadWrite(apiFn);
    props.catalogTable.grantReadData(apiFn); // カタログ読み取り
    // クリック記録（CLICK# への put）。テーブルは公開データ専用なので write 許容
    // （ユーザーテーブルとは分離済み。スペック§8 の IAM 分離）
    props.catalogTable.grantWriteData(apiFn);
    // Bedrock(Claude) 推論呼び出しのみ許可（OCR/礼状生成）。
    // jp./apac. 等のクロスリージョン推論プロファイルは複数リージョンの基盤モデルへ
    // ルーティングするため、foundation-model は全リージョン(*)を許可する。
    apiFn.addToRolePolicy(new iam.PolicyStatement({
      actions: ["bedrock:InvokeModel"],
      resources: ["arn:aws:bedrock:*::foundation-model/*",
                  `arn:aws:bedrock:*:${this.account}:inference-profile/*`],
    }));
    // アカウント削除（#118）: 本人の Cognito ユーザーを削除する。
    apiFn.addToRolePolicy(new iam.PolicyStatement({
      actions: ["cognito-idp:AdminDeleteUser"],
      resources: [`arn:aws:cognito-idp:${this.region}:${this.account}:userpool/${props.userPoolId}`],
    }));

    const api = new apigw.HttpApi(this, "NoshiHttpApi", {
      apiName: "noshi-api",
      corsPreflight: {
        // 本番フロントのオリジンに限定（#72）。dev は vite プロキシ＝同一オリジンのため CORS 不要。
        // 旧 CloudFront ドメインは noshi.me 移行期の併用として当面許可する。
        allowOrigins: ["https://noshi.me", "https://d1u0sgslky88ja.cloudfront.net"],
        allowMethods: [apigw.CorsHttpMethod.ANY],
        allowHeaders: ["authorization", "content-type"],
      },
    });
    api.addRoutes({
      path: "/api/{proxy+}",
      methods: [apigw.HttpMethod.ANY],
      integration: new HttpLambdaIntegration("BffIntegration", apiFn),
    });

    this.apiUrl = api.apiEndpoint;
    new CfnOutput(this, "ApiUrl", { value: api.apiEndpoint });
  }
}
