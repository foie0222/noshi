import { Stack, StackProps } from "aws-cdk-lib";
import { Construct } from "constructs";
import * as budgets from "aws-cdk-lib/aws-budgets";

interface CostStackProps extends StackProps {
  /** アラート通知先メール。 */
  email: string;
  /** 月次予算（USD）。 */
  monthlyLimitUsd: number;
}

/**
 * CostStack — 月次コストの予算アラート（#122）。
 * Bedrock OCR 等の変動費が暴走しないよう、実績80%/100%・予測100%でメール通知する。
 */
export class CostStack extends Stack {
  constructor(scope: Construct, id: string, props: CostStackProps) {
    super(scope, id, props);
    const subscribers = [{ subscriptionType: "EMAIL", address: props.email }];
    new budgets.CfnBudget(this, "MonthlyCostBudget", {
      budget: {
        budgetName: "noshi-monthly",
        budgetType: "COST",
        timeUnit: "MONTHLY",
        budgetLimit: { amount: props.monthlyLimitUsd, unit: "USD" },
      },
      notificationsWithSubscribers: [
        {
          notification: {
            notificationType: "ACTUAL",
            comparisonOperator: "GREATER_THAN",
            threshold: 80,
            thresholdType: "PERCENTAGE",
          },
          subscribers,
        },
        {
          notification: {
            notificationType: "ACTUAL",
            comparisonOperator: "GREATER_THAN",
            threshold: 100,
            thresholdType: "PERCENTAGE",
          },
          subscribers,
        },
        {
          notification: {
            notificationType: "FORECASTED",
            comparisonOperator: "GREATER_THAN",
            threshold: 100,
            thresholdType: "PERCENTAGE",
          },
          subscribers,
        },
      ],
    });
  }
}
