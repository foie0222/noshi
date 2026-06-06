# noshi

家族・親族・友人との贈答（もらった／あげた）を AI が一元管理する生成 AI Web プロダクト。
ご祝儀袋を撮影 → 半返し計算 → お返し提案 → 礼状生成 → Give 履歴連携 までを支援します。

本リポジトリは **AWS AI-DLC v2** の方法論（Claude Code をオーケストレーターとして駆動）で、
構想→要件→設計→実装まで進めたものです。設計ドキュメントは `org-ai-kb/aidlc-docs/` 配下。

## 構成
```
backend/    FastAPI + ドメインロジック（半返し/業務ルール）+ Repository(InMemory/DynamoDB) + モックポート
frontend/   React + TypeScript (Vite) — 中核画面
infra/      AWS CDK スタック雛形（DynamoDB/SQS/S3/Lambda/CloudFront）
docker-compose.yml  ローカル開発（DynamoDB Local + LocalStack + backend + frontend）
org-ai-kb/  AI-DLC 設計ドキュメント（intent-001 inception / intent-002 construction）
```

## 技術スタック
Python(FastAPI) + React(TS) + DynamoDB + SQS + S3 / デプロイ AWS・ローカル Docker / AI・OCR はポート抽象（MVP はモック）。

## ローカルで動かす

### backend（テスト）
```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest          # 31 tests
.venv/bin/uvicorn app.main:app --reload   # http://localhost:8000  (/api/health)
```
MVP は InMemory リポジトリ＋モック抽出で外部依存なく起動します（`X-User-Id` ヘッダでユーザー識別）。

### frontend
```bash
cd frontend
npm install
npm test            # vitest（日本語の検証説明つき）
npm run dev         # http://localhost:5173 （/api を backend にプロキシ）
```

### まとめて（Docker）
```bash
docker compose up --build
```

## テスト方針（TDD）
- backend: **pytest**、frontend: **vitest**。各テストは「何を検証するか」を日本語一文で記載。
- 半返しルール・本人スコープ（OWASP A01）・入力検証（A03）・監査（A09）をテストで担保。

## セキュリティ（OWASP）
本人スコープ強制（PK に userId 内包＋API 検証）、入力検証、汎用エラー（内部情報秘匿）、監査ログ、外部送信の最小化。
