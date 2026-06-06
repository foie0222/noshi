# noshi infra (AWS CDK skeleton)

infrastructure-design.md / deployment-architecture.md に対応する CDK スタック構成（雛形）。

スタック境界:
- NetworkStack    — WAF / 証明書 / CloudFront 基盤
- DataStack       — DynamoDB(テーブル+GSI, PITR, TTL) / S3(画像, SSE-KMS) / KMS（ステートフル・削除保護）
- MessagingStack  — SQS + DLQ
- AuthStack       — Cognito(OIDC) / 外部IdP
- ApiStack        — API Gateway + BFF Lambda(FastAPI+Mangum) + 最小権限IAM + Secrets参照
- WorkerStack     — 抽出ワーカー Lambda（SQS イベントソース）
- FrontendStack   — S3 + CloudFront（React ビルド配信）

環境: dev / prod（別スタックインスタンス）。リージョン: ap-northeast-1。
実装は本 intent のスコープ外（雛形）。`cdk init app --language typescript` を起点に上記スタックを追加する。
