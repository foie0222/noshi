# Code Generation — Clarification（unit: noshi-service）

確定スタック（TSD-1..8）。スコープ=**動く MVP バーティカルスライス**（中核ループ）。
genuine ambiguity は無く、推奨を記録して進める（人間は plan/artifact ゲートで確認）。

### Q1: リポジトリ構成
[Answer]: repo 直下に backend/（FastAPI）, frontend/（React+TS/Vite）, infra/（CDK 雛形）, docker-compose.yml。docs は org-ai-kb/ のまま。

### Q2: ローカル実行とテスト容易性
[Answer]: データ層は Repository 抽象。**InMemory 実装**（テスト/最小起動用）＋ **DynamoDB 実装**（boto3, DynamoDB Local）。テストは InMemory で外部依存なく pytest 実行。

### Q3: 認証（MVP）
[Answer]: 開発用スタブ認証（X-User-Id ヘッダ/dev トークン）で本人スコープを強制。OIDC 実接続は環境変数で後付け。

### Q4: 外部ポート（OCR/LLM・カタログ）
[Answer]: モック実装（決定論的ダミー抽出・定型礼状・固定候補）。実プロバイダは環境変数で差し替え。

### Q5: カバー範囲（中核ループ）
[Answer]: 認証スタブ → 記録（手入力＋抽出モック）→ 台帳/集計 → 半返し計算 → お返し提案 → 礼状生成 → イベント状態。半返しルール/業務ルール/本人スコープ/監査を実装。
