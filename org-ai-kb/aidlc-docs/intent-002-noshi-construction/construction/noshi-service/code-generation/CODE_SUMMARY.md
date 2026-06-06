# CODE_SUMMARY — noshi-service（code-generation）

スコープ: 動く MVP バーティカルスライス。TDD（pytest / vitest、各テストに日本語の検証説明）。

## 生成物

### backend/（Python 3.12 + FastAPI）
- `app/domain/entities.py` — ドメインエンティティ（dataclass、分類コメント）
- `app/domain/rules.py` — 業務ルール（半返し計算 BR-HR、抽出しきい値 BR-EX、入力検証 BR-VAL）
- `app/ports.py` — OcrLlmPort / GiftCatalogPort（Protocol）＋モック実装（決定論的）
- `app/repository.py` — Repository（Protocol）＋ InMemoryRepository ＋ DynamoRepository（boto3 遅延 import、PK に userId 内包）
- `app/services.py` — NoshiService（記録/台帳/お返し/イベント/監査、本人スコープ強制 A01、ValidationError/ForbiddenError）
- `app/schemas.py` — pydantic 入出力（エッジ検証 A03）
- `app/main.py` — FastAPI BFF（スタブ認証 X-User-Id、汎用エラー、DI で Repo/ポート差し替え可）
- `tests/` — pytest 31 件（rules / repository / ports / services / api）

### frontend/（React + TypeScript + Vite）
- `src/lib/format.ts` — 表示フォーマット（純粋関数、TDD）
- `src/components/SummaryBar.tsx` — 収支表示（TDD）
- `src/api.ts` — API クライアント（X-User-Id）
- `src/App.tsx` — 中核画面（login/home/capture/review/ledger/half/suggest/letter/event）＋下部タブ
- `src/styles.css` — 和の意匠（生成り/水引/明朝）
- `src/**/*.test.ts(x)` — vitest 4 件（format / SummaryBar）

### infra/・docker
- `infra/README.md` — AWS CDK スタック雛形（Network/Data/Messaging/Auth/Api/Worker/Frontend）
- `backend/Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`（DynamoDB Local + LocalStack）
- ルート `README.md`（起動手順）

## 検証結果（実行済み）
- backend: `pytest` → **34 passed**
- frontend: `tsc --noEmit` → **0 errors** / `vitest run` → **6 passed** / `vite build` → **成功**
- ローカル起動の実 HTTP 確認: 記録作成→台帳→半返し→お返し→礼状→ステータス、認証なし401、他人データ遮断。

## UX 改善（人間レビュー反映）
- ステータス表示を日本語化（受領/検討中/完了、`statusLabel` を TDD で追加）。
- イベント表示を ID ではなく **相手・用途・金額** に（`pending_views`/`event_view`/`event_for_record` を TDD で追加、`GET /api/records/{id}/event`）。台帳タップ→イベント詳細→お返し導線が繋がる。

## 設計→実装の対応
- functional-design の BR-* を rules.py / services.py に実装。
- application-design のコンポーネント（Identity/Ledger/Extraction/HalfReturn/Suggestion/Letter/GiftEvent/Audit/BFF）を services + main にマッピング。
- nfr-assessment の技術スタック（Python/React/DynamoDB/SQS/AWS）を採用、ポート抽象でベンダー非依存。
- OWASP: 本人スコープ（A01: repository/service/main の三層＋DynamoDB PK）、入力検証（A03: pydantic）、汎用エラー、監査（A09）、外部送信最小化（礼状生成）。

## 規約・決定
- 外部依存なしでテストできるよう Repository/ポートを抽象化（InMemory + モックで pytest/vitest がオフライン実行可）。
- 認証は MVP スタブ（X-User-Id）。実 OIDC は環境変数で後付け。
- SQS/抽出ワーカーの非同期実体は雛形（MVP は同期モック抽出）。本番化時に SQS イベントソースへ。

## 未実装（次段階）
- 実 SQS ワーカー / 実 OCR・LLM プロバイダ接続 / Cognito 実認証 / CDK 実装 / 全画面状態の作り込み / build-and-test ステージ（AI-DLC v2 未実装）。
