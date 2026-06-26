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
