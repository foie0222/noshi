# Business Logic Model — noshi P1 improvements（intent-004, unit: noshi-service）

## Unit scope
- Unit: noshi-service（継続改修）。Stories owned: S4-1..4（既存維持）。
- Owning components: GiftLedger（年間集計）/ BFF・UI（トーン・信頼表示・税サマリ）。

## 変更ワークフロー（差分）
- WF-トーン: 画面は用途の弔事/慶事分類に応じて配色・コピーを切替（BR-4-TONE）。
- WF-税サマリ（S4-3）: 専用サマリで「今年の対象もらった合計 / 110万まであと◯円 / 超過注意」＋免責（BR-4-TAX）。
- WF-信頼表示: 氏名入力/consent/設定に安心表示（BR-4-TRUST、表示のみ）。
- WF-集計（system, S4-4）: 暦年・対象除外で受領合計を算出（本人データのみ）。

## 不変
- お返し期限・given除外・本人スコープ・監査は intent-002/003 のまま。
