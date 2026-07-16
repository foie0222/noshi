import { Stack, StackProps, Duration } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as dynamodb from "aws-cdk-lib/aws-dynamodb";
import * as events from "aws-cdk-lib/aws-events";
import * as targets from "aws-cdk-lib/aws-events-targets";
import * as iam from "aws-cdk-lib/aws-iam";
import { backendLambdaCode } from "./lambda-code";

interface ReminderStackProps extends StackProps {
  table: dynamodb.Table;
  /** SES 送信ドメイン（例: noshi.me）。送信元は no-reply@<domain>。 */
  domainName: string;
}

/**
 * ReminderStack — お返し期限のリマインド（#178）。
 *
 * 「お返しを忘れない」をユーザーの記憶力に頼らず実現する。日次の EventBridge ルールが
 * Lambda（backend/app/reminders.handler）を起動し、全世帯のお返し期限が1週間前・当日の
 * イベントを抽出して、世帯メンバーへ落ち着いたトーンのメールを SES で送る。
 *
 * 送信元は AuthStack と同じ no-reply@noshi.me（DKIM/SPF/DMARC 整備済み）。
 */
export class ReminderStack extends Stack {
  public readonly reminderFn: lambda.Function; // 監視（#124）から参照

  constructor(scope: Construct, id: string, props: ReminderStackProps) {
    super(scope, id, props);

    const fromEmail = `no-reply@${props.domainName}`;

    // iOS プッシュ通知（#205）。APNs 鍵は CFN に載せず、SNS プラットフォームアプリは
    // 一度だけ CLI で作成し ARN を context で渡す（未設定ならメールのみ＝段階導入可能）:
    //   aws sns create-platform-application --name noshi-ios --platform APNS \
    //     --attributes PlatformCredential="$(aws ssm get-parameter --name /noshi/apns/signing-key \
    //       --with-decryption --query Parameter.Value --output text)",PlatformPrincipal=<KeyID>,ApplePlatformTeamID=<TeamID>,ApplePlatformBundleID=me.noshi.app
    const apnsAppArn = (this.node.tryGetContext("apnsPlatformAppArn") as string) ?? "";

    const fn = new lambda.Function(this, "ReturnReminder", {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "app.reminders.handler", // backend/app/reminders.py
      code: backendLambdaCode(),
      timeout: Duration.seconds(120),
      memorySize: 256,
      environment: {
        NOSHI_TABLE: props.table.tableName,
        NOSHI_USE_DYNAMO: "1",
        NOSHI_FROM_EMAIL: fromEmail,
        ...(apnsAppArn ? { NOSHI_APNS_PLATFORM_APP_ARN: apnsAppArn } : {}),
      },
    });

    // 全世帯の走査（Scan）＋イベント/メンバー読取＋送信済みマーカー書込のため RW を付与。
    props.table.grantReadWriteData(fn);

    // SES 送信は noshi.me の検証済みアイデンティティに限定する。
    fn.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["ses:SendEmail", "ses:SendRawEmail"],
        resources: [
          `arn:aws:ses:${this.region}:${this.account}:identity/${props.domainName}`,
        ],
      }),
    );

    // APNs プッシュ送信（#205）。エンドポイント作成・publish・属性更新を許可。
    // publish の対象はプラットフォームアプリ配下のエンドポイント（endpoint/APNS/...）。
    if (apnsAppArn) {
      fn.addToRolePolicy(
        new iam.PolicyStatement({
          actions: [
            "sns:CreatePlatformEndpoint",
            "sns:Publish",
            "sns:SetEndpointAttributes",
          ],
          resources: [
            apnsAppArn,
            `arn:aws:sns:${this.region}:${this.account}:endpoint/APNS/*`,
          ],
        }),
      );
    }

    // 毎日 08:00 JST（23:00 UTC）に実行。朝の落ち着いた時間にそっと届ける。
    new events.Rule(this, "DailyReminderSchedule", {
      schedule: events.Schedule.cron({ minute: "0", hour: "23" }),
      targets: [new targets.LambdaFunction(fn)],
    });
    this.reminderFn = fn;
  }
}
