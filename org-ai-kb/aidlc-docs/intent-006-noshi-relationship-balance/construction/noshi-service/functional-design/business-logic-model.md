# Business Logic Model — noshi relationship balance（intent-006）
## Unit scope
- Unit: noshi-service。Stories: S6-1..4。Owning components: GiftLedger（集計）/ BFF・UI（おつきあいビュー）。
## 変更WF（差分）
- バランス集計（system, S6-4）: 相手別 received/given/差分/最終やりとり日 を集計し偏りを分類（BR-6-BALANCE）。
- おつきあいビュー: マイページに相手別バランス一覧、気になる関係を上位・控えめ（UI）。
## 不変
- 既存ドメインは intent-002..005 のまま。
