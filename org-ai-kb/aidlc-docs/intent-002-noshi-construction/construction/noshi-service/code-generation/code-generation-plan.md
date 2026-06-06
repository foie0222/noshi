# Code Generation — Plan（unit: noshi-service / 動く MVP バーティカルスライス）

レイヤーごとに生成→ビルド/テスト検証。確定スタック: Python(FastAPI) + React(TS/Vite) + DynamoDB（InMemory も）+ モックポート。

## Layer 1: ドメイン（技術非依存ロジック）
- [x] backend/app/domain/entities.py（dataclass: User, Party, GiftRecord, ExtractionJob, GiftEvent, ReturnSuggestion, Letter, AuditEntry）
- [x] backend/app/domain/rules.py（半返し計算 BR-HR、検証 BR-VAL、ステータス、信頼度しきい値）
- [x] backend/tests/test_rules.py（半返し各用途・丸め・上書き、検証）

## Layer 2: ポート＆データ層
- [x] backend/app/ports.py（OcrLlmPort, GiftCatalogPort インターフェース＋モック実装）
- [x] backend/app/repository.py（Repository 抽象 + InMemoryRepository + DynamoRepository[boto3]）
- [x] backend/tests/test_repository.py（InMemory の本人スコープ・CRUD）

## Layer 3: サービス層
- [x] backend/app/services.py（記録/台帳/お返し/イベント/監査、本人スコープ強制 A01）
- [x] backend/tests/test_services.py（記録→台帳→半返し→提案→礼状→完了、他人データ拒否）

## Layer 4: API（BFF, FastAPI）
- [x] backend/app/main.py（FastAPI、スタブ認証依存、ルート: auth/home/capture/ledger/returns/event）
- [x] backend/app/schemas.py（pydantic 入出力・入力検証 A03）
- [x] backend/tests/test_api.py（TestClient で主要エンドポイント）
- [x] backend/requirements.txt, pyproject/pytest 設定

## Layer 5: フロント（React + TS / Vite）
- [x] frontend/（Vite + React + TS、api クライアント、画面: login/home/capture/ledger/half-return/suggest/letter/event）
- [x] 和の意匠（mockup 準拠）。型チェック/ビルド検証。

## Layer 6: ローカル基盤＆ドキュメント
- [x] docker-compose.yml（DynamoDB Local, LocalStack, backend, frontend）、backend/Dockerfile
- [x] infra/（CDK スタック雛形: Data/Api/Worker/Frontend のスケルトン）
- [x] README.md（起動手順）、CODE_SUMMARY.md（生成物・決定・規約）

## 検証
- [x] backend: `pytest` 全緑（InMemory・外部依存なし）
- [x] frontend: 型チェック/ビルド（可能なら）
- [x] OWASP: 本人スコープ・入力検証・汎用エラー・監査・restricted非ログを実装で担保
