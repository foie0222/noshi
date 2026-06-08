# AGENTS.md

noshi — 家族・親族・友人との贈答（もらった／あげた）を AI で一元管理する Web プロダクト。

## 構成
- `backend/` — FastAPI（domain / services / repository / ports）。DynamoDB・Amazon Bedrock。
- `frontend/` — React + TypeScript (Vite)。
- `infra/cdk/` — AWS CDK（Data / Auth / Messaging / Api / Worker / Frontend）。
- `org-ai-kb/` — AI-DLC の設計ドキュメント・監査ログ。

## セットアップ & 主要コマンド
### backend
```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest                          # テスト
.venv/bin/python -m uvicorn app.main:app --reload   # 起動（http://localhost:8000）
```
### frontend
```bash
cd frontend
npm install
npm test            # vitest
npm run dev         # http://localhost:5173（/api を backend にプロキシ）
```
### infra
```bash
cd infra/cdk && npm install && npx cdk synth
```
本番デプロイ・永続化・実OCR・認証の詳細手順は [README.md](./README.md) を参照。

## コーディング方針
- **TDD 必須**: 失敗するテストを先に書き、最小実装で通す（Red → Green → Refactor）。
- テストは **「何を検証するか」を日本語の一文**で記述する（例: `def test_半返しは香典で半額になる():`）。
- 本人／世帯スコープ（OWASP A01）を必ず守る。エラーは汎用文言で返し内部情報を漏らさない。
- lint / format / 型チェック（ruff・biome・mypy strict）は #10 で整備予定。

## コミット / PR
- 1 つの論点ごとにコミット。メッセージは要点を簡潔に。
- Issue 単位で `issue-<番号>` ブランチを切り、PR で `main` に入れる。
- 変更はテスト緑（pytest / vitest、必要に応じ `cdk synth`）を確認してから。

## セキュリティ
- 秘密情報（鍵・トークン・パスワード）はコミットしない。
- 生成物（`cdk.out*` / `dist/` / `.venv/` / `node_modules/`）はコミットしない（`.gitignore` 済み）。
