import { Stack, StackProps, Duration, CfnOutput, RemovalPolicy } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as cognito from "aws-cdk-lib/aws-cognito";

/**
 * AuthStack — 家族共有のユーザー認証（Amazon Cognito User Pool）。
 * メール＋パスワードでサインアップ/ログイン。発行された JWT を API が検証する
 * （backend の NOSHI_COGNITO_POOL_ID に poolId を渡すと RS256/JWKS 検証に切替わる）。
 */
export class AuthStack extends Stack {
  public readonly userPool: cognito.UserPool;
  public readonly userPoolClient: cognito.UserPoolClient;

  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    this.userPool = new cognito.UserPool(this, "NoshiUserPool", {
      userPoolName: "noshi-users",
      selfSignUpEnabled: true,
      signInAliases: { email: true },
      autoVerify: { email: true },
      standardAttributes: { email: { required: true, mutable: false } },
      passwordPolicy: {
        minLength: 8,
        requireLowercase: true,
        requireDigits: true,
        requireUppercase: false,
        requireSymbols: false,
        tempPasswordValidity: Duration.days(3),
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY,
      removalPolicy: RemovalPolicy.RETAIN, // ユーザー資産は誤削除しない
    });

    // SPA 用クライアント（クライアントシークレットなし、SRP/ユーザーパスワード認証）
    this.userPoolClient = this.userPool.addClient("NoshiWebClient", {
      userPoolClientName: "noshi-web",
      generateSecret: false,
      authFlows: { userSrp: true, userPassword: true },
      idTokenValidity: Duration.hours(1),
      accessTokenValidity: Duration.hours(1),
      refreshTokenValidity: Duration.days(30),
      preventUserExistenceErrors: true,
    });

    new CfnOutput(this, "UserPoolId", { value: this.userPool.userPoolId });
    new CfnOutput(this, "UserPoolClientId", { value: this.userPoolClient.userPoolClientId });
    new CfnOutput(this, "Issuer", {
      value: `https://cognito-idp.${this.region}.amazonaws.com/${this.userPool.userPoolId}`,
    });
  }
}
