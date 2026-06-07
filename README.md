# noshi 🧧

家族・親族・友人との贈答（もらった／あげた）を AI が一元管理する生成 AI Web プロダクト。
ご祝儀袋を撮影 → 半返し計算 → お返し提案 → 礼状生成 → 期限管理 までを支援します。
「贈答を、損得ではなく **関係のメンテナンス** として、ちゃんと続けられる」。

本リポジトリは **AWS AI-DLC v2** の方法論（Claude Code をオーケストレーターとして駆動）で、
構想 → 設計 → 実装 → UX改善 → 機能拡張 → IaC まで進めたものです。設計・監査の全記録は `org-ai-kb/` 配下。

## 主な機能
- **撮影 → 記録**: ご祝儀袋等を撮影し AI 抽出（金額/氏名/関係/用途/日付）。要所だけ確認して保存。
- **お返し期限ダッシュボード**: ホームを「お返しの予定」（残日数の近い順）に。期限超過を強調。
- **半返し計算**: 用途別の推奨お返し額＋根拠（香典1/2、出産1/3〜1/2、お中元歳暮は返礼不要 等）。
- **お返し提案・礼状生成**: 候補提示（提案のみ）と礼状文面の生成。
- **弔事/慶事トーン**: 香典等は静かな配色・コピーに切替。
- **信頼の可視化**: 「あなただけが見られます🔒」。本人スコープ・暗号化・削除権。
- **贈与税110万枠の気づき**: 暦年の対象もらった合計（社会通念上の贈答は除外）と枠への接近（※税アドバイスではない）。
- **おつきあいバランス**: 相手別の もらった/あげた/差分・最終やりとり、「気になる関係」をやさしく可視化。
- **お年玉の目安**: 年齢別の相場レンジ。
- **体験**: 中央＋FABナビ／お返し完了の水引アニメ（reduced-motion尊重）／季節ナッジ／文字サイズ拡大／オンボーディング。

## 構成
```
backend/   FastAPI + ドメインロジック（半返し/期限/トーン/贈与税/おつきあい/お年玉判定）
           + Repository(InMemory/DynamoDB) + モックポート（OCR/LLM/カタログ）
frontend/  React + TypeScript (Vite) — 和の意匠（生成り/水引/明朝）
infra/cdk/ AWS CDK(TypeScript) — Data/Messaging/Api/Worker/Frontend スタック（cdk synth 検証済み）
docker-compose.yml  ローカル開発（DynamoDB Local + LocalStack + backend + frontend）
org-ai-kb/ AI-DLC の設計ドキュメント（intent-001〜009）と design-reviews、監査ログ
```

## 技術スタック
Python(FastAPI) + React(TS) + DynamoDB + SQS + S3 / デプロイ AWS（CDK）・ローカル Docker / AI・OCR はポート抽象（MVP はモック）。

## ローカルで動かす
### backend
```bash
cd backend
python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/python -m pytest                 # 54 tests
.venv/bin/python -m uvicorn app.main:app --reload   # http://localhost:8000
```
MVP は InMemory リポジトリ＋モック抽出で外部依存なく起動（`X-User-Id` ヘッダでユーザー識別）。

### frontend
```bash
cd frontend
npm install
npm test            # vitest 23（日本語の検証説明つき）
npm run dev         # http://localhost:5173 （/api を backend にプロキシ）
```

### infra（CDK / 検証のみ）
```bash
cd infra/cdk
npm install
npx cdk synth       # CloudFormation を生成（AWS 認証不要・未デプロイ）
```

## テスト方針（TDD）
backend=**pytest**（54）/ frontend=**vitest**（23）/ infra=**cdk synth**。各テストは「何を検証するか」を日本語一文で記載。
半返し・期限・贈与税・おつきあい・お年玉・本人スコープ（OWASP A01）・入力検証（A03）・監査（A09）をテストで担保。

## セキュリティ（OWASP）
本人スコープ強制（DynamoDB の PK に userId 内包＋API/サービス/リポジトリの多層検証）、入力検証、汎用エラー（内部情報秘匿）、監査ログ、外部送信の最小化、暗号化（KMS/TLS）。

## AI-DLC の歩み（intent）
001 inception → 002 construction（動くMVP）→ 003 P0（期限ダッシュボード等）→ 004 P1（トーン/信頼/贈与税）→ 005 P2（FAB/水引/a11y）→ 006 N1（おつきあい）→ 007 N2（お年玉）→ 008 あげた記録/バグ修正 → 009 CDK インフラ。
各 intent は決定論的検証（process_checker）＋ TDD ＋ 独立バリデーターで品質を担保。
