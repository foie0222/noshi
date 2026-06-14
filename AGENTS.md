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
- lint / format / 型: **ruff**（backend）/ **biome**（frontend）/ **mypy strict**（backend `app/`）。
- **デザインシステム準拠（frontend）**: ネイティブ UI のドロップダウン（`<select>` 等、OS 依存の見た目になるもの）は使わず、自前コンポーネント（`Select` / `MasterSelect` / `PartySelect` の `rel-panel` パターン）で統一する。biome の a11y ルールは **error**（`<button>` / `fieldset` / `aria-*` を適切に使う）。

## lint / format / pre-commit
コミット前に自動チェックされる（厳格: format 自動修正・lint/型エラーはブロック）。
```bash
pip install pre-commit && pre-commit install   # 初回のみ
backend/.venv/bin/ruff check backend && backend/.venv/bin/ruff format --check backend
backend/.venv/bin/mypy --config-file backend/pyproject.toml   # ※ cd backend で実行
# フロントの完全ゲート（コミット前に通すこと）
( cd frontend && npx biome ci src && npx tsc --noEmit && npx vitest run && npm run build )
```

## 開発フロー
- **PR は必ず Issue に紐付ける**（本文に `Closes #<番号>`）。**Issue のない PR は原則作成しない** —
  軽微な変更でも、先に Issue を立ててから着手する。
- ブランチは **最新の `main` から** 切る（並行作業の隔離＝`git worktree` 運用はユーザー設定に従う）。
- Issue 単位で `issue-<番号>` ブランチ。1 論点ごとにコミット、メッセージは要点を簡潔に。
- 変更前にテスト緑（pytest / vitest、必要に応じ `cdk synth`）と pre-commit 通過を確認。
- PR で `main` へ。**CI（backend / frontend / infra）が緑** であること。
- **Claude 自動レビューの指摘（インラインコメント）への対応**: PR 作成時に Claude がレビューし、指摘を
  解決可能スレッドで残す（未解決スレッドがあるとマージ不可）。各スレッドは、
  **対応コミットの有効なリンク（コミット ID）を添えて返信してから Resolve する**。黙って Resolve しない。
  誤検知の場合も、なぜ対応不要かを返信してから Resolve する。
- マージは **squash merge**。`main` へのマージで **GitHub Actions が本番へ自動デプロイ** される
  （`--context enforceAuth=true`）。`deploy to AWS` ジョブの完了まで見届ける。

## AWS 運用
- 認証は SSO。セッション切れ時はセッション内で `aws login` で再認証（プロファイル: AdministratorAccess）。
- CDK スタック: Data / Auth / Messaging / Api / Worker / Frontend。
- DNS: Route 53 ホストゾーン `noshi.me`（Zone ID `Z05828342UROTXZ54NZBT`）。レジストラはお名前.com で
  NS を Route 53 に委任。ゾーンは手動管理し、CDK からは `fromLookup` で参照（独自ドメイン移行は #72）。
- 現行の本番 URL は CloudFront ドメイン（`*.cloudfront.net`）。

## セキュリティ
- 秘密情報（鍵・トークン・パスワード）はコミットしない。
- 生成物（`cdk.out*` / `dist/` / `.venv/` / `node_modules/`）はコミットしない（`.gitignore` 済み）。
