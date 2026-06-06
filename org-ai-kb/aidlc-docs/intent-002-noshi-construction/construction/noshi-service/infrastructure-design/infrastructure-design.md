# Infrastructure Design — noshi-service

論理コンポーネント（logical-components.md）/ アプリ層を **AWS** 具体サービスへ割当。ローカルは Docker で同型。リージョン: ap-northeast-1。IaC: AWS CDK。

## アプリ層
### BFF / API
- サービス: **API Gateway (HTTP API) + AWS Lambda**（Python/FastAPI を Mangum でラップ）。
- 構成: 認可は Lambda 内（本人スコープ＋トークン検証）、最小権限 IAM（必要な DynamoDB/SQS/S3 アクションのみ）。
- NFR: NFR-P1/P3（オートスケール）、NFR-S1。

### 抽出ワーカー
- サービス: **AWS Lambda**（SQS イベントソース）。
- 構成: SQS から消費→OcrLlmPort 実行→DynamoDB 更新。冪等(jobId)。タイムアウトはジョブ特性に合わせ設定。
- NFR: NFR-P2, NFR-S2。

## LC-1 JobQueue + DLQ → **Amazon SQS（standard）+ DLQ**
- 可視性タイムアウト 60s、maxReceiveCount 3→DLQ。DLQ 深さを CloudWatch Alarm。

## LC-2 ObjectStore → **Amazon S3**
- バケットは userId プレフィックス、ブロックパブリックアクセス、署名付きURL（TTL 5分）、SSE-KMS、バージョニング。

## LC-3 ResiliencePolicy → アプリ内（アダプタ）
- AWS SDK のタイムアウト/リトライ＋アプリのサーキットブレーカ。外部呼び出しに適用。

## LC-4 TokenManager → **Amazon Cognito（OIDC）**（または外部 IdP 連携）
- トークン有効期限（アクセス15分/リフレッシュ14日）、失効、認証レート制限（WAF/Cognito）。

## LC-5 AuditSink → **DynamoDB（AuditEntry, 追記）＋ CloudWatch Logs**
- 追記専用、restricted は識別子/マスクのみ。

## LC-6 Observability → **CloudWatch（Logs/Metrics/Alarms）+ X-Ray（トレース）**
- 構造化ログ・相関ID、p95/エラー/DLQ/認可失敗メトリクス、アラート。

## LC-7 KeyManagement → **AWS KMS**
- DynamoDB/S3 の暗号化鍵、ローテーション有効。

## データストア → **Amazon DynamoDB**
- per-entity テーブル + GSI（status/party）、PITR 有効、TTL（ExtractionJob.candidates）、オンデマンドキャパシティ。PK に userId 内包（A01）。

## フロント配信 → **Amazon S3 + CloudFront**
- React ビルド成果物を S3、CloudFront 配信（TLS、キャッシュ、SPA フォールバック）。

## シークレット → **AWS Secrets Manager**
- 外部プロバイダのキー等。Lambda は最小権限で取得。

## コスト概算（MVP・ap-northeast-1・想定負荷 NFR-D1=数千ユーザー/月、NFR-S1=季節バースト）

オンデマンド/サーバレス中心のため負荷連動。月額の概算レンジ（USD、低トラフィック MVP 前提）:

| サービス | 概算/月 | 根拠（想定負荷） |
|---|---|---|
| Lambda（BFF+ワーカー） | $0〜5 | 無料枠内〜数十万リクエスト。NFR-S1 のバーストもオートスケールで従量 |
| API Gateway (HTTP API) | $0〜3 | $1.0/百万リクエスト。MVP は数十万/月 |
| DynamoDB（オンデマンド） | $2〜10 | 数千ユーザー×数百レコード、PITR 含む。NFR-D1 |
| S3（画像）+ リクエスト | $1〜5 | 画像数 GB＋取得。署名URL直アップロードで転送最小 |
| SQS | $0〜1 | 100万リクエストまで無料。抽出ジョブは少量 |
| CloudFront | $1〜5 | フロント配信、無料枠＋少量転送 |
| Cognito | $0 | MAU 5万まで無料枠内（数千ユーザー） |
| KMS | $1〜2 | キー数＋暗号化リクエスト |
| Secrets Manager | $0.4/シークレット | 数個のシークレット |
| CloudWatch/X-Ray | $1〜5 | ログ/メトリクス/トレース量に連動 |
| **合計（概算）** | **約 $10〜40/月** | MVP 低トラフィック時。トラフィック増で従量増加 |

注: 確定見積りではなく桁感。ピーク（年末年始/お中元、NFR-S1）は一時的に上振れするが従量課金で吸収。実コストは負荷計測後に再評価。

## ローカル開発（Docker 同型）
- DynamoDB Local（データ）、LocalStack（SQS/S3、必要なら Cognito 代替）、FastAPI（uvicorn）、Vite（フロント）。
- 環境変数でエンドポイントを AWS↔ローカル切替。OcrLlmPort はモック実装。
