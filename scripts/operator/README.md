# 自律オペレーター

承認済み Issue を Claude が実装→PR 化し、リスク別ハイブリッドで本番マージまで運ぶ仕組み。
設計: `docs/superpowers/specs/2026-06-27-autonomous-operator-design.md`

## PO（あなた）の操作だけ
- バックログを承認する: 対象 Issue に `po:approved` を付ける（`po:proposal` は提案、まだ着手されない）
- 早く着手させたい: `prio:high` を足す or operator ワークフローを手動 dispatch
- センシティブ PR を出荷する: `merge:human` の付いた PR を自分でマージ
- 方向性の質問に答える: `needs:po` の Issue に回答して `po:approved` を付け直す

## ラベル状態機械
`po:proposal` → (PO) `po:approved` → `agent:in-progress` → `agent:pr-open` → merge

## ワークフロー
- `operator.yml`: cron で 1 日 1 回。承認済みを 1 件拾って implement を起動。枯れていたら提案を生成。ブリーフィングを追記
- `implement.yml`: 指定 Issue を実装し PR を開く（operator から dispatch）
- `classify-and-merge.yml`: PR を merge:auto/human に分類。auto のみ自動マージ

## ローカルでロジックを試す
python -m pytest scripts/operator

## GitHub App セットアップ（オペレーターの PR 作成に必須）
implement が作る PR に CI/レビューを発火させるため、PR は GitHub App の installation
トークンで作成する（GITHUB_TOKEN だと下流ワークフローが起動しない GitHub 仕様の回避）。

1. GitHub App を作成（Settings → Developer settings → GitHub Apps → New）。
   Repository permissions: Contents=Read and write、Pull requests=Read and write、Issues=Read and write。
2. この App をリポジトリに Install。
3. App の秘密鍵(.pem)を生成し、リポジトリ secret に登録:
   - `OPERATOR_APP_ID`（App ID）
   - `OPERATOR_APP_PRIVATE_KEY`（.pem の中身）

## ブランチ保護の前提（auto-merge が成立する条件）
`main` のルールセットで、必須チェック（CI / Claude review）とレビュースレッド解決を
required にする。ただし「人間の PR 承認」を必須にしないこと（必須にすると merge:auto でも
人間承認待ちで止まる）。センシティブ変更の人間ゲートは merge:human を auto-merge しないことで担保する。
既存ルールセットの確認: `gh api repos/:owner/:repo/rulesets`。
- implement の PR は App 名義のため CI/Claude review が発火する。merge:auto の自動マージは、
  指摘ゼロ（未解決スレッド無し）かつ必須チェック緑のときだけ成立する＝レビューが安全弁になる。
