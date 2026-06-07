# User Stories — noshi CDK infra（intent-009）
## IaC
### S9-1 インフラをコードで定義する
As a 運用者, I want noshi のインフラを CDK でコード定義したい, so that 再現可能・レビュー可能にデプロイできる。
- AC1: Data/Messaging/Api/Worker/Frontend のスタックが CDK で定義される。
- AC2: `cdk synth` が成功し CloudFormation を生成する。
- Requirements: FR-9-1, FR-9-3
### S9-2 セキュアな既定
As a 運用者, I want 暗号化・最小権限・S3非公開を既定にしたい, so that 安全に運用できる。
- AC1: KMS暗号化・TLS・BlockPublicAccess・最小権限IAM・PK内包の本人スコープがコードに含まれる。
- Requirements: FR-9-2
## 補足
- 実デプロイ・CI/CD は out of scope。
