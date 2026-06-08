# noshi 🧧

家族・親族・友人との贈答（もらった／あげた）を AI が一元管理する生成 AI Web プロダクト。
ご祝儀袋を撮影 → 半返し計算 → お返し提案 → 礼状生成 → 期限管理 までを支援します。
「贈答を、損得ではなく **関係のメンテナンス** として、ちゃんと続けられる」。

本リポジトリは **AWS AI-DLC v2** の方法論（Claude Code をオーケストレーターとして駆動）で、
構想 → 設計 → 実装 → UX改善 → 機能拡張 → IaC まで進めたものです。設計・監査の全記録は `org-ai-kb/` 配下。

## 主な機能
- **ログイン**: Amazon Cognito によるメール＋パスワード認証（サインアップ／確認コード／ログイン）。本番APIは JWT 必須。
- **家族で共有**: 世帯（家族）単位で台帳・お返し・期限を共有。招待コードで家族が参加し、二人三脚で贈答を回す。
- **撮影 → 記録**: ご祝儀袋等を撮影し AI（Bedrock/Claude Vision）抽出（金額/氏名/関係/用途/日付）。要所だけ確認して保存。
- **記録の修正**: 抽出/入力の誤りを後から訂正（本人スコープ＋監査、日付は保持）。
- **お返し期限ダッシュボード**: ホームを「お返しの予定」（残日数の近い順）に。期限超過を強調。
- **半返し計算**: 用途別の推奨お返し額＋根拠（香典1/2、出産1/3〜1/2、お中元歳暮は返礼不要 等）。
- **お返し提案・礼状生成**: 候補提示（提案のみ）と礼状文面の生成。礼状はワンタップでコピー。
- **弔事/慶事トーン**: 香典等は静かな配色・コピーに切替。礼状文面も弔事（四十九日・供養）に出し分け。
- **年間振り返り**: その年の いただいた/贈った の件数・合計・お付き合いした人数。
- **信頼の可視化**: 「ご家族だけが見られます🔒」。世帯スコープ・暗号化・削除権。
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
.venv/bin/python -m pytest                 # 98 tests
.venv/bin/python -m uvicorn app.main:app --reload   # http://localhost:8000
.venv/bin/python seed_demo.py              # （任意）デモ用に7件投入（要: backend 起動中）
```
既定は InMemory リポジトリ＋モック抽出で外部依存なく起動（`X-User-Id` ヘッダでユーザー識別）。
**再起動を跨いでデータを残す**には DynamoDB Local を使う永続モードで起動:
```bash
docker compose up -d dynamodb                                   # DynamoDB Local (host:8001)
export DYNAMODB_ENDPOINT=http://localhost:8001 AWS_REGION=ap-northeast-1 \
       AWS_ACCESS_KEY_ID=local AWS_SECRET_ACCESS_KEY=local NOSHI_TABLE=noshi NOSHI_USE_DYNAMO=1
.venv/bin/python -c "from app.repository import create_table; create_table('noshi')"  # 初回のみ
.venv/bin/python -m uvicorn app.main:app                        # 以後データは DynamoDB に永続化
```
**実 AI で画像を読む**（モック→本物）には Amazon Bedrock(Claude) を有効化:
```bash
aws login                                  # AWS 認証（要 Bedrock の Claude モデル利用許可）
.venv/bin/pip install "botocore[crt]"      # aws login の資格情報を boto3 が読むために必要
export NOSHI_USE_BEDROCK=1                  # 既定モデル jp.anthropic.claude-sonnet-4-5（NOSHI_BEDROCK_MODEL で変更可）
.venv/bin/python -m uvicorn app.main:app   # /api/capture が実画像を Claude Vision で抽出
```

### 認証・家族共有
データは**本人ではなく「世帯」**に属し、同じ世帯の家族が台帳を共有する（初回アクセスで世帯が自動作成され、本人が管理者。マイページの招待コードを家族に伝えると参加できる）。認証は環境変数で切替:
- 既定: `X-User-Id` スタブ（ローカル開発。フロントの「開発用ユーザー切替」で共有を体験可能）
- ローカル検証: `NOSHI_JWT_SECRET=...` で HS256 の Bearer トークン検証
- 本番: `NOSHI_COGNITO_POOL_ID=<poolId>`（+AWS_REGION）で Amazon Cognito の JWT を RS256/JWKS 検証
User Pool は CDK の `AuthStack`（`cdk deploy NoshiAuthStack`）で作成。

### frontend
```bash
cd frontend
npm install
npm test            # vitest 30（日本語の検証説明つき）
npm run dev         # http://localhost:5173 （/api を backend にプロキシ）
```

### infra（CDK）
```bash
cd infra/cdk
npm install
npx cdk synth       # CloudFormation を生成（AWS 認証不要）
```

### AWS へデプロイ（フルスタック公開）
```bash
aws login                                   # 認証（Bedrock/Cognito 等の権限が必要）
.venv/bin/pip install "botocore[crt]"       # aws login 資格情報用
cd infra/cdk && npm install
# 1) バックエンド（DynamoDB/Cognito/SQS/Lambda+API GW/Worker）
npx cdk deploy NoshiDataStack NoshiAuthStack NoshiMessagingStack NoshiApiStack NoshiWorkerStack \
  --require-approval never --outputs-file ./cdk-outputs.json
# 2) 取得した ApiUrl でフロントをビルド → 配信（S3+CloudFront）
API=$(python3 -c "import json;print(json.load(open('cdk-outputs.json'))['NoshiApiStack']['ApiUrl'])")
( cd ../../frontend && VITE_API_BASE="$API" npx vite build )
npx cdk deploy NoshiFrontendStack --require-approval never --outputs-file ./cdk-outputs-frontend.json
# 出力された SiteUrl(CloudFront) が公開URL。撤去は: npx cdk destroy --all
```
- Lambda は依存ライブラリ込みでバンドル（`lib/lambda-code.ts`、pip の manylinux wheel・Docker不要）。
- API は本番で **DynamoDB 永続化＋Bedrock 実OCR** が有効。
- 認証: `--context enforceAuth=true` で Cognito JWT を強制（X-User-Id スタブを無効化）。フロントは
  Cognito ログイン（サインアップ→メール確認コード→ログイン、`VITE_COGNITO_CLIENT_ID` を注入）。
  ローカル（env 未設定）はスタブ認証＋開発用ユーザー切替のまま。

## テスト方針（TDD）
backend=**pytest**（98）/ frontend=**vitest**（43）/ infra=**cdk synth**。各テストは「何を検証するか」を日本語一文で記載。
半返し・期限・贈与税・おつきあい・お年玉・本人スコープ（OWASP A01）・入力検証（A03）・監査（A09）をテストで担保。

## セキュリティ（OWASP）
本人スコープ強制（DynamoDB の PK に userId 内包＋API/サービス/リポジトリの多層検証）、入力検証、汎用エラー（内部情報秘匿）、監査ログ、外部送信の最小化、暗号化（KMS/TLS）。

## AI-DLC の歩み（intent）
001 inception → 002 construction（動くMVP）→ 003 P0（期限ダッシュボード等）→ 004 P1（トーン/信頼/贈与税）→ 005 P2（FAB/水引/a11y）→ 006 N1（おつきあい）→ 007 N2（お年玉）→ 008 あげた記録/バグ修正 → 009 CDK インフラ → 実OCR(Bedrock/Claude) → 家族共有(世帯スコープ+Cognito)。
各 intent は決定論的検証（process_checker）＋ TDD ＋ 独立バリデーターで品質を担保。
