# Domain Entities — noshi P0 improvements（intent-003, unit: noshi-service）

intent-002 のエンティティを保持。本 intent の差分のみ記述（全エンティティ定義は intent-002 を参照）。

## GiftEvent（差分）
- 追加属性: due_at (internal, optional) — お返し期限日（受領日＋用途別日数）。お返し不要用途は None。
- 派生（保存しない計算値）: days_left = due_at − today（internal）。負値=超過。
- ライフサイクル不変。status は received/considering/done（自由遷移）。done と given は pending から除外。
- 不変条件: given レコードに対する pending イベントを持たない（BR-3-GIVEN-1）。

## GiftRecord（不変）
- 既存のまま（amount/purpose/occurred_at/direction… 分類も不変）。occurred_at が期限の起点。

## ExtractionJob（不変）
- candidates/confidence は既存。表示時に項目別 needs_review を信頼度で判定（BR-3-CONF、UI差分）。

## 分類
- 追加 due_at / days_left は internal（機微度に影響しない派生・期限情報）。restricted/confidential は不変。
