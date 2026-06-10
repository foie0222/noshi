import { Stack, StackProps, Duration, CfnOutput, RemovalPolicy } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as cognito from "aws-cdk-lib/aws-cognito";
import * as route53 from "aws-cdk-lib/aws-route53";
import * as ses from "aws-cdk-lib/aws-ses";

export interface AuthStackProps extends StackProps {
  /** 認証メールの送信ドメイン（例: noshi.me）。 */
  domainName: string;
  /** 送信ドメインの Route53 ホストゾーン（DKIM/MAIL FROM/DMARC レコードを発行する）。 */
  hostedZoneId: string;
  hostedZoneName: string;
}

/**
 * AuthStack — 家族共有のユーザー認証（Amazon Cognito User Pool）。
 * メール＋パスワードでサインアップ/ログイン。発行された JWT を API が検証する
 * （backend の NOSHI_COGNITO_POOL_ID に poolId を渡すと RS256/JWKS 検証に切替わる）。
 *
 * 認証メール（パスワードリセット・確認コード等）は Cognito 既定送信
 * （no-reply@verificationemail.com）だと SPF/DKIM/DMARC の整合が取れず迷惑メールに
 * 振り分けられやすい。そこで noshi ドメインから SES 送信する(#90)。
 *
 * 本コミットは Part 1：SES 送信ドメイン（DKIM/SPF/DMARC）の整備のみ。Cognito を SES に
 * アタッチするのは、ドメイン検証(DKIM)完了後に別 PR（Part 2）で行う。
 */
export class AuthStack extends Stack {
  public readonly userPool: cognito.UserPool;
  public readonly userPoolClient: cognito.UserPoolClient;

  constructor(scope: Construct, id: string, props: AuthStackProps) {
    super(scope, id, props);

    // 既存の Route53 ホストゾーンに DKIM(CNAME×3) / MAIL FROM(MX・SPF TXT) を自動発行する。
    const zone = route53.PublicHostedZone.fromPublicHostedZoneAttributes(this, "Zone", {
      hostedZoneId: props.hostedZoneId,
      zoneName: props.hostedZoneName,
    });
    new ses.EmailIdentity(this, "NoshiEmailIdentity", {
      identity: ses.Identity.publicHostedZone(zone),
      // バウンスの SPF 整合のためカスタム MAIL FROM を使う（mail.noshi.me）。
      mailFromDomain: `mail.${props.domainName}`,
    });
    // DMARC は監視モード(p=none)から開始。受信側に SPF/DKIM 整合のポリシーを宣言する。
    new route53.TxtRecord(this, "DmarcRecord", {
      zone,
      recordName: "_dmarc",
      values: ["v=DMARC1; p=none"],
    });

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
