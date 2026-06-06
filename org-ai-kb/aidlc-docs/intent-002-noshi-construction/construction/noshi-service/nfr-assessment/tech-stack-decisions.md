# Tech Stack Decisions — noshi-service

人間が選定（nfr-assessment ゲート）。各決定は ID（TSD-n）・理由・関連NFR・代替（却下）・トレードオフ・OWASP 整合を持つ。

## TSD-1 バックエンド: Python 3.12 + FastAPI
- 理由: AI/OCR 連携の親和性、pydantic で入力検証（A03）、Lambda/コンテナ両対応。
- 関連NFR: NFR-P2/P3（性能）、NFR-SE5（入力検証）、NFR-S1（スケール）。
- 代替（却下）: Node/TS（フロントと統一できるが AI 連携で Python 優位）、Go（高速だが MVP 開発速度で劣後）。
- トレードオフ: フロント（TS）と言語が分かれ、型定義を二重管理（OpenAPI 自動生成で緩和）。
- デプロイ: AWS Lambda + API Gateway。重い抽出ワーカーは別 Lambda/コンテナ。

## TSD-2 フロントエンド: React + TypeScript（Vite）
- 理由: wireframes と整合する SPA、PWA 視野、型安全。
- 関連NFR: **NFR-4（モバイルファースト・WCAG 2.1 AA）**、NFR-P1（画面 p95）。
- 代替（却下）: Next.js（SSR は MVP に過剰）、SvelteKit（チーム親和性低）。
- トレードオフ: SPA は初回バンドルが増えやすい → コード分割/遅延読込で NFR-P1 を担保。
- 配信: S3 + CloudFront。

## TSD-3 データストア: DynamoDB（NoSQL）
- 理由: サーバレス・オンデマンドスケール、運用レス、PITR で RPO。
- 関連NFR: NFR-S3（スケール）、NFR-A2（RPO）、NFR-D1/D2（データ）、NFR-SE3（本人スコープをキーに内包）。
- **アクセスパターン駆動設計**（論理 data-models→キー設計）:
  - User by id（PK=USER#<userId>）
  - GiftRecord 一覧/相手別（PK=USER#<userId>, SK=RECORD#<occurredAt>#<id>、GSI: party）
  - GiftEvent by user/status（GSI: status）、未完了一覧（status≠done）
  - ExtractionJob（PK=USER#<userId>, SK=JOB#<id>、candidates は TTL）
  - AuditEntry（PK=USER#<actorId>, SK=AUDIT#<at>）
  - **本人スコープを PK に内包**して A01 をキー設計で強制。
- 代替（却下）: PostgreSQL（関係に自然だが運用/スケールで DynamoDB を選好）。
- トレードオフ: アドホッククエリ不可・後からのアクセスパターン追加が高コスト → 設計時に確定（上記）。集計は事前計算 or GSI。

## TSD-4 非同期ジョブ: Amazon SQS（+ DLQ）
- 理由: マネージド・スケール・リトライ/DLQ、抽出の平滑化。
- 関連NFR: NFR-R2（信頼性）、NFR-S2（スケール）、NFR-A3（可用性）、NFR-P2（抽出）。
- 代替（却下）: DB-backed 簡易（依存最小だがスケール/可観測性で劣後）、Redis（基盤追加コスト）。
- トレードオフ: 完全非同期で UI は結果取得にポーリング/通知が必要（loading 画面＋jobStatus で対応）。
- フロー: BFF→SQS→抽出ワーカー Lambda→Completed/Failed→DynamoDB 更新。冪等キー=jobId。

## TSD-5 画像ストレージ: Amazon S3
- 理由: 撮影画像保管、署名付き URL で直接アップロード（BFF 負荷減）、KMS 暗号化。
- 関連NFR: NFR-SE2（暗号化）、NFR-P1/P2（アップロード負荷分散）、NFR-A2（バージョニング）。
- 代替（却下）: DynamoDB に格納（サイズ/コストで不可）。
- トレードオフ: 署名付き URL の発行・有効期限管理が必要 → 短命URL＋userId プレフィックスで制御。

## TSD-6 AI/OCR: OcrLlmPort 抽象
- 理由: application-design と整合、ベンダー非依存、テスト容易。
- 関連NFR: NFR-R1（フォールバック）、NFR-SE5（送信最小化）、NFR-P2。
- MVP: **モック/スタブ実装**で E2E 成立。実プロバイダ（Bedrock/Textract 等）は環境変数で差し替え。
- 代替（却下）: 特定プロバイダ直結（テスト/移植性で劣後）。
- トレードオフ: 抽象層の追加コスト ↔ ベンダーロックイン回避・モックでの高速テスト。

## TSD-7 認証: OIDC（外部 IdP）+ メール
- 理由: 標準・委譲、トークン失効・有効期限・レート制限。
- 関連NFR: NFR-SE4（A07 認証）。
- 代替（却下）: 自前パスワード管理のみ（資格情報保持リスク増）。
- トレードオフ: IdP 依存 ↔ 資格情報の自前保持を最小化（restricted 削減）。

## TSD-8 ローカル開発: Docker Compose
- 理由: クラウド非依存のローカル E2E、移植性。
- 関連NFR: 開発生産性（NFR 値の検証可能性）、NFR-A（本番同型でリスク低減）。
- 構成: DynamoDB Local、LocalStack（SQS/S3）、FastAPI（uvicorn）、Vite。環境変数で AWS↔ローカル切替。
- 代替（却下）: 各自クラウド開発（コスト/到達性で劣後）。
- トレードオフ: ローカルとクラウドの微差（LocalStack 制約）→ CI で実 AWS スモークを補完。

## OWASP 整合まとめ
- A01: PK に userId を内包しキー設計で本人スコープ強制（TSD-3）。BFF でも検証（多層）。
- A02: at rest（KMS: DynamoDB/S3）/ in transit（TLS）。restricted は平文保存・ログ禁止。
- A03: pydantic/エッジ検証、画像形式・サイズ、署名付きURL（TSD-1,5）。
- A07: OIDC・トークン失効・レート制限（TSD-7）。
- A09: AuditLog（DynamoDB 追記）＋ CloudWatch。
- 外部送信（OcrLlmPort/Catalog）は最小化・マスキング（TSD-6）。
