# NFR Assessment — Clarification Questions（unit: noshi-service）

NFR 値は requirements.md（NFR-1..5）から導出済み（性能 p95<2.5s / 抽出<10s、可用性99%、APPI、モバイルファースト等）。
ここでは **技術スタックの決定**を中心に確認する。MVP・モバイルファースト Web・BFF・非同期抽出・外部LLM/OCR・PII保護が前提。

### Q1: 主要技術スタック

a) **TypeScript フルスタック**（Next.js[PWA] フロント＋ Node/TypeScript の BFF/API ＋ Prisma ＋ PostgreSQL）。1言語で MVP 最速。ローカルで生成コードのビルド/テストが容易。
b) **Python バックエンド**（FastAPI）＋ React/Next フロント ＋ PostgreSQL。AI/OCR 連携に強い。
c) **Go バックエンド**＋ React フロント ＋ PostgreSQL。高性能・低リソース。

**Recommendation:** a) TypeScript フルスタック（MVP速度・単一言語・本環境で実ビルド検証が容易）。

[Answer]: Python バックエンド（FastAPI）＋ React(TypeScript) フロント。データストアは DynamoDB

### Q2: データベース＆ホスティング

a) **マネージド**（PostgreSQL: Neon/Supabase 等 ＋ フロント/関数を Vercel）。運用最小。
b) **AWS**（RDS PostgreSQL ＋ ECS/Lambda ＋ S3）。AWS 前提・拡張性。
c) **セルフホスト**（Docker Compose: Postgres＋アプリ）。ローカル完結・移植性。

**Recommendation:** a) マネージド（MVP の運用負荷最小）。※生成コードはどれでも動くよう環境変数で抽象化。

[Answer]: デプロイ=AWS、ローカル開発=Docker（DynamoDB Local / LocalStack 等）

### Q3: 非同期ジョブ（抽出）基盤

a) **DB-backed 簡易キュー**（jobs テーブル＋ワーカー）。MVP に十分・依存最小。
b) **Redis** ベース（BullMQ 等）。
c) **マネージドキュー**（SQS 等）。

**Recommendation:** a) DB-backed 簡易（MVP・単一サービス。将来差し替え可）。

[Answer]: マネージドキュー（SQS 等）

### Q4: AI/OCR プロバイダの扱い

a) **外部 LLM/OCR をポート抽象**（OcrLlmPort の背後。実装はアダプタ差し替え可・モック可）。MVP はモック/スタブで動作、実プロバイダは環境変数で接続。
b) 特定プロバイダに直結

**Recommendation:** a) ポート抽象（application-design と整合・テスト容易・ベンダー非依存）。

[Answer]: 外部 LLM/OCR をポート抽象（OcrLlmPort、モック/スタブ可）
