# Infrastructure Design — Clarification（unit: noshi-service）

tech-stack-decisions（TSD-1..8）で AWS デプロイ＋ローカル Docker が確定済み。論理→具体サービスの割当は決定済みで、推奨値を記録して進める（人間は plan/artifact ゲートで確認）。

### Q1: 論理コンポーネント → AWS サービス割当
[Answer]: BFF/API=API Gateway+Lambda(FastAPI/Mangum) / 抽出ワーカー=Lambda / JobQueue=SQS+DLQ / ObjectStore=S3(署名付きURL) / データ=DynamoDB(GSI,PITR,TTL) / 認証=Cognito(OIDC)（または外部IdP）/ 鍵=KMS / 監視=CloudWatch(Logs/Metrics/Alarms) / フロント配信=S3+CloudFront / IaC=AWS CDK(or SAM)

### Q2: リージョン / データレジデンシー
[Answer]: ap-northeast-1（東京）。データ国内（NFR-D3）

### Q3: 環境
[Answer]: dev / prod の2環境。ローカルは Docker(DynamoDB Local + LocalStack)

### Q4: ネットワーク/セキュリティ境界
[Answer]: API Gateway をエッジ、Lambda は最小権限 IAM、S3/DynamoDB はプライベートアクセス、暗号化既定（KMS/TLS）、シークレットは Secrets Manager
