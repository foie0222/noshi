# Domain Entities — noshi P1 improvements（intent-004, unit: noshi-service）

intent-002/003 のエンティティを保持。本 intent は新規エンティティなし（差分のみ）。

## GiftRecord（不変）
- 既存の amount/purpose/occurred_at/direction を集計・分類に利用（分類は派生・保存しない）。

## 派生（保存しない計算値）
- tone(purpose): mourning / celebration（BR-4-TONE）— internal。
- yearly_target_total(user, year): 対象received合計（香典/中元/歳暮除外）— internal。
- gift_tax_view: { total, remaining, over } — internal。

## 分類
- 追加は派生のみ。restricted/confidential のデータ分類は不変。集計は本人スコープ内（A01）。
