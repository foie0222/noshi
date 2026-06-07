# Requirements — noshi CDK infra（intent-009, N4 IaC）

## Intent summary
- Type: feature（IaC）/ Scope: 単一サービス noshi-service / Classification: brownfield / Affected repos: noshi
- 源泉: design-review-002 N4 ＋ intent-002 infrastructure-design。

## Functional requirements
- **FR-9-1 CDK スタック実装**
  - FR-9-1.1 DataStack: DynamoDB(PK=USER#内包, PITR, TTL, GSI, 削除保護) / S3(画像, SSE-KMS, 非公開, versioned) / KMS(rotation)。
  - FR-9-1.2 MessagingStack: SQS + DLQ（可視性60s, maxReceive3）。
  - FR-9-1.3 ApiStack: API Gateway(HTTP API) + Lambda(BFF) + 最小権限 IAM。
  - FR-9-1.4 WorkerStack: 抽出ワーカー Lambda(SQS イベントソース) + 最小権限。
  - FR-9-1.5 FrontendStack: S3 + CloudFront（SPA フォールバック, OAC, TLS）。
- **FR-9-2 セキュリティ既定（OWASP）**
  - FR-9-2.1 暗号化（KMS at rest / TLS in transit）、S3 非公開（BlockPublicAccess）、最小権限 IAM、本人スコープを PK 設計に内包。
- **FR-9-3 検証**
  - FR-9-3.1 `cdk synth` が成功し CloudFormation テンプレートを生成すること（AWS 認証不要・未デプロイ）。

## Non-functional requirements
- NFR は intent-001..008 を維持。リージョン ap-northeast-1。ステートフル資源は削除保護。
- 確定的（IaC はコードで宣言）。デプロイは別途（本 intent は synth 検証まで）。

## Assumptions
- AWS への実デプロイは本 intent のスコープ外（認証情報なし）。アプリ実体の Lambda bundling は段階的（骨子は placeholder）。

## Out of scope
- 実 AWS デプロイ・パイプライン(CI/CD)・実 OCR/LLM/Cognito 接続・カスタムドメイン/証明書
