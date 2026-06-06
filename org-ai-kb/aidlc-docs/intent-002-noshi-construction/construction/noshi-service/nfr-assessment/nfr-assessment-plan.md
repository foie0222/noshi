# NFR Assessment — Plan（unit: noshi-service）

確定スタック: **Python(FastAPI) + React(TypeScript) + DynamoDB / デプロイ AWS・ローカル Docker / SQS / AI・OCR はポート抽象**。

## nfr-requirements.md
- [x] Unit scope（noshi-service / owning components / 機能複雑度サマリ）
- [x] 性能（NFR-1: 画面 p95<2.5s、抽出 p95<10s）— ワークフロー参照
- [x] スケーラビリティ（消費者向け・バースト想定、サーバレス/オートスケール方針）
- [x] 可用性（NFR-3: 99%、単一リージョン MVP、RTO/RPO 目安）
- [x] セキュリティ（NFR-2: エンティティ別分類、暗号化 at rest/in transit、本人スコープ、APPI）
- [x] 信頼性（外部ポート障害時フォールバック、SQS リトライ/DLQ）
- [x] 可観測性（メトリクス/ログ/トレース、監査）
- [x] データ（DynamoDB 容量目安・保持・リージョン）
- [x] NFR トレーサビリティ（requirements.md NFR-1..5 へ）

## tech-stack-decisions.md
- [x] バックエンド: Python 3.x + FastAPI（Lambda or ECS）。理由・代替。
- [x] フロント: React + TypeScript（Vite、PWA 視野）。
- [x] データストア: **DynamoDB**（NoSQL）。→ アクセスパターン駆動設計／単一テーブル方針の注記。data-models（関係型）を DynamoDB のキー設計へ写像する方針。
- [x] 非同期: SQS（抽出ジョブ）＋ DLQ。ワーカー（Lambda/コンテナ）。
- [x] ストレージ: S3（撮影画像、署名付きURL）。
- [x] AI/OCR: OcrLlmPort 抽象（MVP はモック、実接続は環境変数）。
- [x] 認証: 外部 IdP（OIDC）＋ メール。トークン失効。
- [x] ローカル開発: Docker（DynamoDB Local、LocalStack で SQS/S3、FastAPI、Vite）。
- [x] 各決定の理由・トレードオフ・却下案。OWASP との整合（暗号化・最小権限・監査）。
