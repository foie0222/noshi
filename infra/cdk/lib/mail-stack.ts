import { Stack, StackProps, RemovalPolicy, Duration } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as path from "path";
import * as s3 from "aws-cdk-lib/aws-s3";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as ses from "aws-cdk-lib/aws-ses";
import * as sesActions from "aws-cdk-lib/aws-ses-actions";
import * as iam from "aws-cdk-lib/aws-iam";
import * as route53 from "aws-cdk-lib/aws-route53";

interface MailStackProps extends StackProps {
  domainName: string; // noshi.me（MX を張る apex）
  hostedZoneId: string;
  hostedZoneName: string;
  recipient: string; // 受信アドレス（例: contact@noshi.me）。転送の送信元にも使う
  forwardTo: string; // 転送先（例: 個人の Gmail）
}

/**
 * MailStack — 問い合わせ窓口の受信メール転送（#135）。**us-east-1 必須**
 * （SES 受信は東京リージョン非対応）。受信メールを S3 に保存し Lambda が転送する。
 * デプロイ後、ReceiptRuleSet をアクティブ化すること（CDK では作成のみ）。
 */
export class MailStack extends Stack {
  readonly ruleSetName = "noshi-inbound";

  constructor(scope: Construct, id: string, props: MailStackProps) {
    super(scope, id, props);

    const bucket = new s3.Bucket(this, "InboundMail", {
      blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
      encryption: s3.BucketEncryption.S3_MANAGED,
      enforceSSL: true,
      lifecycleRules: [{ expiration: Duration.days(30) }], // 受信メールは短期保持
      removalPolicy: RemovalPolicy.DESTROY,
      autoDeleteObjects: true,
    });
    // SES が受信メールを put できるように許可（同一アカウントからのみ）。
    bucket.addToResourcePolicy(
      new iam.PolicyStatement({
        principals: [new iam.ServicePrincipal("ses.amazonaws.com")],
        actions: ["s3:PutObject"],
        resources: [bucket.arnForObjects("inbound/*")],
        conditions: { StringEquals: { "aws:SourceAccount": this.account } },
      }),
    );

    const fn = new lambda.Function(this, "Forwarder", {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "handler.handler",
      code: lambda.Code.fromAsset(path.join(__dirname, "../lambda/forwarder")),
      timeout: Duration.seconds(30),
      memorySize: 256,
      environment: {
        BUCKET: bucket.bucketName,
        PREFIX: "inbound/",
        FORWARD_TO: props.forwardTo,
        SENDER: props.recipient,
      },
    });
    bucket.grantRead(fn);
    fn.addToRolePolicy(
      new iam.PolicyStatement({ actions: ["ses:SendRawEmail"], resources: ["*"] }),
    );

    const ruleSet = new ses.ReceiptRuleSet(this, "RuleSet", {
      receiptRuleSetName: this.ruleSetName,
    });
    ruleSet.addRule("ForwardRecipient", {
      recipients: [props.recipient],
      actions: [
        new sesActions.S3({ bucket, objectKeyPrefix: "inbound/" }), // 先に保存
        new sesActions.Lambda({ function: fn }), // 続けて転送
      ],
    });

    // MX: noshi.me 宛を us-east-1 の SES 受信エンドポイントへ。
    const zone = route53.PublicHostedZone.fromPublicHostedZoneAttributes(this, "Zone", {
      hostedZoneId: props.hostedZoneId,
      zoneName: props.hostedZoneName,
    });
    // SES 受信・転送送信のため、この受信リージョン(us-east-1)でも noshi.me を検証する（DKIM）。
    // 未検証だと受信が拒否され、Lambda の転送送信もできない（送信用の auth-stack は別リージョン）。
    new ses.EmailIdentity(this, "Identity", {
      identity: ses.Identity.publicHostedZone(zone),
    });
    new route53.MxRecord(this, "Mx", {
      zone,
      recordName: props.domainName,
      values: [{ priority: 10, hostName: `inbound-smtp.${this.region}.amazonaws.com` }],
    });
  }
}
