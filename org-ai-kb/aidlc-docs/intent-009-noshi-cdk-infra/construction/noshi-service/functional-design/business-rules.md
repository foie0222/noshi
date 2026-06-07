# Business Rules — noshi CDK infra（intent-009, unit: noshi-service）
intent-002..008 を保持。本 intent はインフラ実装規約。

## BR-9-IAC IaC 規約（新規）
- **Stories:** S9-1, S9-2
- **BR-9-IAC-1 (hard):** ステートフル資源（DynamoDB/S3/KMS）は RemovalPolicy=RETAIN（削除保護）。
- **BR-9-IAC-2 (hard):** 暗号化（KMS at rest / TLS in transit）・S3 BlockPublicAccess・最小権限 IAM（grant 単位）。
- **BR-9-IAC-3 (hard):** DynamoDB は PK=USER#<userId> 内包で本人スコープ（A01）。PITR・TTL・GSI。
- **BR-9-IAC-4 (soft):** SQS は DLQ・可視性60s・maxReceive3。
- **BR-9-IAC-5 (hard):** cdk synth が成功すること（CloudFormation 生成）。
