# CODE_SUMMARY — noshi CDK infra（intent-009 N4 IaC）

infrastructure-design（intent-002）を AWS CDK(TypeScript) で実装。`infra/cdk/`。

## スタック（deployment-architecture 準拠）
- DataStack: DynamoDB（PAY_PER_REQUEST, PITR, TTL=ttl, GSI gsi-status, KMS CMK, RETAIN）/ S3 画像（BlockPublicAccess, SSE-KMS, versioned, enforceSSL, RETAIN）/ KMS（rotation）。
- MessagingStack: SQS（可視性60s, enforceSSL）+ DLQ（maxReceive3, 14日保持）。
- ApiStack: API Gateway(HTTP API, /api/{proxy+}) + Lambda(Python3.12, BFF placeholder) + 最小権限（table RW / queue send / bucket RW）。
- WorkerStack: 抽出ワーカー Lambda + SqsEventSource(batch5) + table RW。
- FrontendStack: S3 + CloudFront（OAC, REDIRECT_TO_HTTPS, SPA 403/404→index.html）。
- bin/noshi.ts: 5スタックを ap-northeast-1 に構成、依存注入（Api/Worker→Data/Messaging）。

## 検証（実行済み）
- `tsc --noEmit` 0 errors / `cdk synth` → **5 CloudFormation テンプレート生成**（AWS 認証不要・未デプロイ）。

## 設計/OWASP 対応
- FR-9-1→5スタック、FR-9-2→KMS/TLS/BlockPublicAccess/最小権限/PK内包(A01)、FR-9-3→synth 成功。BR-9-IAC 実装。
- アプリ実体の Lambda bundling（backend/ の同梱）と CI/CD、実デプロイは段階的（本 intent はインフラ骨子＋synth検証）。
