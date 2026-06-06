# Deployment Architecture — noshi-service

## アーキテクチャ概要（テキスト図）

```
[モバイル/PCブラウザ]
      │ HTTPS(TLS)
      ▼
[CloudFront] ──(静的)──> [S3: フロント(React/TS ビルド)]
      │ /api/*
      ▼
[API Gateway (HTTP API)]
      │  (JWT 検証 / WAF レート制限)
      ▼
[Lambda: BFF/API (FastAPI+Mangum)] ──┬─> [DynamoDB] (userId スコープ, GSI, PITR, TTL, KMS)
      │                               ├─> [S3] 署名付きURL発行 (画像)
      │                               ├─> [SQS] 抽出ジョブ enqueue
      │                               └─> [Secrets Manager] 外部キー
                                       
[S3:画像] <──直接アップロード(署名付きURL)── [ブラウザ]

[SQS] ──イベント──> [Lambda: 抽出ワーカー] ──> [OcrLlmPort(外部/モック)]
                          │                         (失敗→DLQ, 手入力fallback)
                          └─> [DynamoDB] ジョブ/レコード更新
   └─(maxReceive超過)─> [SQS DLQ] ──> [CloudWatch Alarm]

[認証] [Cognito(OIDC) / 外部IdP]  ← BFF がトークン検証
[監視] 全 Lambda → [CloudWatch Logs/Metrics/Alarms] + [X-Ray]
[監査] セキュリティイベント → [DynamoDB AuditEntry] + CloudWatch
[鍵]  [KMS] が DynamoDB/S3 を暗号化
```

## 環境
- **dev / prod** の2環境（別アカウント or 別スタック）。リージョン ap-northeast-1。
- **ローカル**: Docker Compose（DynamoDB Local / LocalStack(SQS,S3) / FastAPI / Vite）。本番同型。

## IaC / CI/CD
- IaC: **AWS CDK**（TypeScript or Python）。全リソースをコード化。
- **スタック/モジュール境界**:
  - `NetworkStack`（共有: WAF, 証明書, CloudFront 基盤）
  - `DataStack`（DynamoDB テーブル＋GSI, S3 バケット, KMS キー — ステートフル, 削除保護）
  - `MessagingStack`（SQS, DLQ）
  - `AuthStack`（Cognito ユーザープール / 外部IdP 連携）
  - `ApiStack`（API Gateway, BFF Lambda, IAM ロール, Secrets 参照）
  - `WorkerStack`（抽出ワーカー Lambda, SQS イベントソース）
  - `FrontendStack`（S3 静的ホスティング, CloudFront ディストリビューション）
  - ステートフル（Data/Auth）とステートレス（Api/Worker/Frontend）を分離し、再デプロイ時のデータ保全とライフサイクル差を吸収。
- 環境分離: dev/prod は別スタックインスタンス（環境別パラメータ/アカウント）。
- CI/CD: ビルド→テスト→`cdk deploy`（dev→承認→prod）。フロントは S3 同期＋CloudFront 無効化。

## セキュリティ境界（OWASP）
- エッジ: CloudFront/API Gateway（TLS, WAF レート制限）。
- 認可: BFF Lambda で本人スコープ強制（A01）＋ DynamoDB PK 内包の多層。
- データ: KMS 暗号化（at rest）、TLS（in transit）、S3 非公開＋短命署名URL。
- 最小権限 IAM（各 Lambda は必要アクションのみ）。シークレットは Secrets Manager。
- 監査: セキュリティイベントを追記（A09）。

## 障害時挙動
- 外部ポート障害: リトライ→CB→fallback（手入力/候補なし/メールログイン）。
- 抽出失敗: DLQ 隔離＋アラート、ユーザーは手入力。
- リージョン障害: MVP は単一リージョン（NFR-A1 99%）。PITR で復旧（RTO≤4h/RPO≤24h）。

## データレジデンシー
- すべて ap-northeast-1（国内）。第三者PII を含むため APPI 準拠（NFR-D3/SE7）。
