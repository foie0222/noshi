# Business Logic Model — noshi P0 improvements（intent-003, unit: noshi-service）

## Unit scope
- Unit: noshi-service（intent-002 を改修）。
- Stories owned (本 intent): S3-1, S3-2, S3-3, S3-4, S3-5（既存 S-1..14 は維持）。
- Owning components: GiftLedger / GiftEvent / Extraction / BFF（期限・表示・除外の差分）。AuditLog/Identity 等は不変。

## 変更ワークフロー（差分）
- WF-2'（撮影→記録）: 抽出結果は高信頼=確定済み・低信頼のみ要確認で提示（BR-3-CONF）。要確認ゼロなら即保存可。
- WF-記録→イベント: **received のみ**受領イベントを生成（given はイベントを作らない・BR-3-GIVEN）。
- WF-ホーム: 未完了お返し（received・期限あり）を**残日数つき・期限昇順**で提示。収支/差分は表示しない（BR-3-DUE / FR-3-2）。
- WF-期限算出（system, S3-5）: 受領レコードの用途から標準期限を occurred_at 起点で算出、残日数を返す。お返し不要用途は期限なし。

## 不変
- 本人スコープ前提（A01）・監査（A09）・半返し以降のお返しフローは intent-002 のまま。
