# Infrastructure Design — Plan（unit: noshi-service）

論理コンポーネント（logical-components.md）を AWS 具体サービスへ割当。ローカルは Docker 同型。

## infrastructure-design.md
- [x] 論理→具体マッピング（LC-1..7 + アプリ/フロント）
- [x] 各サービスの構成・最小権限 IAM・暗号化・スケール設定・NFR 充足
- [x] ローカル開発の対応（DynamoDB Local / LocalStack）

## deployment-architecture.md
- [x] 全体アーキ図（テキスト）: クライアント→CloudFront/S3(フロント)→API Gateway→Lambda(BFF)→DynamoDB/SQS/S3、抽出ワーカー Lambda←SQS、外部ポート
- [x] 環境（dev/prod）・リージョン（ap-northeast-1）・IaC（CDK）・CI/CD 概要
- [x] セキュリティ境界・データフロー・障害時挙動
