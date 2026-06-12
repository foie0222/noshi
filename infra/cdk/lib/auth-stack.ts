import { Stack, StackProps, Duration, CfnOutput, RemovalPolicy, SecretValue } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as cognito from "aws-cdk-lib/aws-cognito";
import * as route53 from "aws-cdk-lib/aws-route53";
import * as ses from "aws-cdk-lib/aws-ses";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as iam from "aws-cdk-lib/aws-iam";
import { backendLambdaCode } from "./lambda-code";

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
 * 振り分けられやすい。そこで noshi ドメイン（DKIM/SPF/DMARC 整備済み）から
 * SES で no-reply@noshi.me として送信する(#90)。
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
    const emailIdentity = new ses.EmailIdentity(this, "NoshiEmailIdentity", {
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
      // 認証メールを noshi.me から SES 送信する（迷惑メール対策・#90）。
      email: cognito.UserPoolEmail.withSES({
        fromEmail: `no-reply@${props.domainName}`,
        fromName: "noshi",
        sesVerifiedDomain: props.domainName,
      }),
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
    // 送信ドメインの検証(EmailIdentity)が User Pool より先に作られるようにする。
    this.userPool.node.addDependency(emailIdentity);

    // ---- ソーシャルログイン（Google + LINE）。スペック: 2026-06-12-social-login-design.md ----

    // Hosted UI ドメイン（画面は使わず /oauth2/authorize・/oauth2/token のみ利用）。
    // prefix "noshi-me" が取得済みで deploy が失敗する場合は "noshi-app" に変更する（スペック§3）。
    const domain = this.userPool.addDomain("NoshiCognitoDomain", {
      cognitoDomain: { domainPrefix: "noshi-me" },
    });

    // IdP の клиентID/シークレットは Secrets Manager "noshi/social-login"（デプロイ前に手動登録必須）。
    const secretJson = (field: string) =>
      SecretValue.secretsManager("noshi/social-login", { jsonField: field });

    const googleIdp = new cognito.UserPoolIdentityProviderGoogle(this, "GoogleIdp", {
      userPool: this.userPool,
      clientId: secretJson("googleClientId").unsafeUnwrap(),
      clientSecretValue: secretJson("googleClientSecret"),
      scopes: ["openid", "email", "profile"],
      attributeMapping: {
        email: cognito.ProviderAttribute.GOOGLE_EMAIL,
        // email_verified を取り込み、Pre-signup の乗っ取りガードに使う（スペック§4）
        custom: { email_verified: cognito.ProviderAttribute.other("email_verified") },
      },
    });

    // LINE は OIDC 準拠（discovery 自動）。プロバイダ名 "LINE" は cognito.ts の
    // identity_provider と同一文字列で統一（スペック§3）。
    const lineIdp = new cognito.UserPoolIdentityProviderOidc(this, "LineIdp", {
      userPool: this.userPool,
      name: "LINE",
      clientId: secretJson("lineChannelId").unsafeUnwrap(),
      clientSecret: secretJson("lineChannelSecret").unsafeUnwrap(),
      issuerUrl: "https://access.line.me",
      scopes: ["openid", "profile", "email"],
      attributeRequestMethod: cognito.OidcAttributeRequestMethod.GET,
      attributeMapping: { email: cognito.ProviderAttribute.other("email") },
    });

    // 自動統合トリガ（backend/app/auth_triggers.py）。pool_id は event から取るため env 不要
    //（env で pool_id を渡すと UserPool⇔Lambda の循環参照になる）。
    const presignupFn = new lambda.Function(this, "PresignupTrigger", {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "app.auth_triggers.presignup_handler",
      code: backendLambdaCode(),
      timeout: Duration.seconds(10),
      memorySize: 256,
    });
    presignupFn.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["cognito-idp:ListUsers", "cognito-idp:AdminLinkProviderForUser"],
        resources: [this.userPool.userPoolArn],
      }),
    );
    this.userPool.addTrigger(cognito.UserPoolOperation.PRE_SIGN_UP, presignupFn);

    // SPA 用クライアント（シークレットなし）。既存の SRP/パスワード認証に加え、
    // ソーシャル用の認可コードグラントを有効化。
    // 注意: Cognito は public client でも PKCE を強制しない。フロント実装が常に
    // code_challenge/verifier を付与することで担保する（スペック§3）。
    this.userPoolClient = this.userPool.addClient("NoshiWebClient", {
      userPoolClientName: "noshi-web",
      generateSecret: false,
      authFlows: { userSrp: true, userPassword: true },
      oAuth: {
        flows: { authorizationCodeGrant: true },
        scopes: [cognito.OAuthScope.OPENID, cognito.OAuthScope.EMAIL, cognito.OAuthScope.PROFILE],
        // 本番 origin のみ（localhost を含めない＝コード横取りの足場を作らない。スペック§3）
        callbackUrls: ["https://noshi.me/"],
        logoutUrls: ["https://noshi.me/"],
      },
      supportedIdentityProviders: [
        cognito.UserPoolClientIdentityProvider.COGNITO,
        cognito.UserPoolClientIdentityProvider.GOOGLE,
        cognito.UserPoolClientIdentityProvider.custom("LINE"),
      ],
      idTokenValidity: Duration.hours(1),
      accessTokenValidity: Duration.hours(1),
      refreshTokenValidity: Duration.days(30),
      preventUserExistenceErrors: true,
    });
    // IdP の作成完了後にクライアントを作る（supportedIdentityProviders の参照整合）
    this.userPoolClient.node.addDependency(googleIdp);
    this.userPoolClient.node.addDependency(lineIdp);

    new CfnOutput(this, "UserPoolId", { value: this.userPool.userPoolId });
    new CfnOutput(this, "UserPoolClientId", { value: this.userPoolClient.userPoolClientId });
    new CfnOutput(this, "Issuer", {
      value: `https://cognito-idp.${this.region}.amazonaws.com/${this.userPool.userPoolId}`,
    });
    new CfnOutput(this, "CognitoDomain", { value: domain.baseUrl() });
  }
}
