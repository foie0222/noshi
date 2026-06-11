#!/usr/bin/env node
import { App } from "aws-cdk-lib";
import { DataStack } from "../lib/data-stack";
import { MessagingStack } from "../lib/messaging-stack";
import { AuthStack } from "../lib/auth-stack";
import { ApiStack } from "../lib/api-stack";
import { WorkerStack } from "../lib/worker-stack";
import { FrontendStack } from "../lib/frontend-stack";
import { GithubOidcStack } from "../lib/github-oidc-stack";
import { CertificateStack } from "../lib/certificate-stack";
import { CatalogBatchStack } from "../lib/catalog-batch-stack";
import { CostStack } from "../lib/cost-stack";

// noshi インフラ（infrastructure-design.md / deployment-architecture.md）。リージョン ap-northeast-1。
const app = new App();
// Route 53 参照・ACM DNS 検証・クロスリージョン参照には account が必要。
const account = process.env.CDK_DEFAULT_ACCOUNT ?? "688567287706";
const env = { account, region: "ap-northeast-1" };

// 独自ドメイン（#72）。ホストゾーンは手動作成（属性参照）。
const DOMAIN = "noshi.me";
const HOSTED_ZONE_ID = "Z05828342UROTXZ54NZBT";

// CI/CD: GitHub Actions(OIDC) 用のデプロイロール。初回のみ手動 deploy（自動デプロイ対象外）。
new GithubOidcStack(app, "NoshiGithubOidcStack", { env, githubRepo: "foie0222/noshi" });

const data = new DataStack(app, "NoshiDataStack", { env });
const messaging = new MessagingStack(app, "NoshiMessagingStack", { env });
const auth = new AuthStack(app, "NoshiAuthStack", {
  env,
  domainName: DOMAIN,
  hostedZoneId: HOSTED_ZONE_ID,
  hostedZoneName: DOMAIN,
});
new ApiStack(app, "NoshiApiStack", { env, table: data.table, queue: messaging.extractionQueue, imageBucket: data.imageBucket, userPoolId: auth.userPool.userPoolId, catalogTable: data.catalogTable });
new WorkerStack(app, "NoshiWorkerStack", { env, table: data.table, queue: messaging.extractionQueue });
new CatalogBatchStack(app, "NoshiCatalogBatchStack", { env, catalogTable: data.catalogTable });

// コスト予算アラート（#122）。通知先は context budgetEmail で上書き可。
const budgetEmail = (app.node.tryGetContext("budgetEmail") as string) ?? "daikinoue0222@gmail.com";
new CostStack(app, "NoshiCostStack", { env, email: budgetEmail, monthlyLimitUsd: 20 });

// CloudFront 用 ACM 証明書は us-east-1 必須。別リージョンの FrontendStack から参照する。
const cert = new CertificateStack(app, "NoshiCertificateStack", {
  env: { account, region: "us-east-1" },
  crossRegionReferences: true,
  domainName: DOMAIN,
  hostedZoneId: HOSTED_ZONE_ID,
  hostedZoneName: DOMAIN,
});
new FrontendStack(app, "NoshiFrontendStack", {
  env,
  crossRegionReferences: true,
  domainName: DOMAIN,
  hostedZoneId: HOSTED_ZONE_ID,
  hostedZoneName: DOMAIN,
  certificate: cert.certificate,
});
