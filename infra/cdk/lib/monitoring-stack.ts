import { Stack, StackProps, Duration } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as sqs from "aws-cdk-lib/aws-sqs";
import * as sns from "aws-cdk-lib/aws-sns";
import * as subs from "aws-cdk-lib/aws-sns-subscriptions";
import * as cw from "aws-cdk-lib/aws-cloudwatch";
import * as cwActions from "aws-cdk-lib/aws-cloudwatch-actions";
import * as apigw from "aws-cdk-lib/aws-apigatewayv2";

interface MonitoringStackProps extends StackProps {
  email: string; // アラート通知先（既定は PO の Gmail。context alertEmail で上書き）
  httpApi: apigw.HttpApi;
  apiFn: lambda.IFunction;
  workerFn: lambda.IFunction;
  reminderFn: lambda.IFunction;
  catalogFn: lambda.IFunction;
  deadLetterQueue: sqs.IQueue;
}

/**
 * MonitoringStack — 障害検知のアラーム＋メール通知（#124）。
 * 課金アラートは CostStack（#122）が担当し、ここではエラー系のみを扱う。
 * 小規模個人運用のため「エラーが1件でも出たら知らせる」割り切り（過検知より見逃し防止を優先）。
 */
export class MonitoringStack extends Stack {
  constructor(scope: Construct, id: string, props: MonitoringStackProps) {
    super(scope, id, props);

    const topic = new sns.Topic(this, "AlertTopic", { topicName: "noshi-alerts" });
    topic.addSubscription(new subs.EmailSubscription(props.email));
    const notify = new cwActions.SnsAction(topic);

    const alarm = (idSuffix: string, metric: cw.Metric, description: string) => {
      const a = new cw.Alarm(this, idSuffix, {
        metric,
        threshold: 1,
        evaluationPeriods: 1,
        comparisonOperator: cw.ComparisonOperator.GREATER_THAN_OR_EQUAL_TO_THRESHOLD,
        // データ欠損（リクエストなし）は正常扱い（夜間の誤検知防止）
        treatMissingData: cw.TreatMissingData.NOT_BREACHING,
        alarmDescription: description,
      });
      a.addAlarmAction(notify);
      return a;
    };

    // Lambda エラー（5分間に1件以上）
    const fnError = (fn: lambda.IFunction) =>
      fn.metricErrors({ period: Duration.minutes(5), statistic: "Sum" });
    alarm("ApiFnErrors", fnError(props.apiFn) as cw.Metric, "API(BFF) Lambda でエラーが発生");
    alarm("WorkerFnErrors", fnError(props.workerFn) as cw.Metric, "OCR worker Lambda でエラーが発生");
    alarm(
      "ReminderFnErrors",
      fnError(props.reminderFn) as cw.Metric,
      "お返し期限リマインド Lambda でエラーが発生",
    );
    alarm(
      "CatalogFnErrors",
      fnError(props.catalogFn) as cw.Metric,
      "カタログ日次バッチ Lambda でエラーが発生",
    );

    // API Gateway 5xx（統合エラー等。4xx はスロットリング(429)含むため対象外）
    alarm(
      "Api5xx",
      new cw.Metric({
        namespace: "AWS/ApiGateway",
        metricName: "5xx",
        dimensionsMap: { ApiId: props.httpApi.apiId, Stage: "$default" },
        period: Duration.minutes(5),
        statistic: "Sum",
      }),
      "API Gateway が 5xx を返却",
    );

    // OCR 抽出の DLQ 滞留（3回リトライ失敗＝ユーザーの読み取りが失われている）
    alarm(
      "ExtractionDlqBacklog",
      props.deadLetterQueue.metricApproximateNumberOfMessagesVisible({
        period: Duration.minutes(5),
        statistic: "Maximum",
      }) as cw.Metric,
      "OCR 抽出ジョブが DLQ に滞留（3回失敗）",
    );
  }
}
