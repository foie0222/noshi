# Business Rules — noshi relationship balance（intent-006, unit: noshi-service）

intent-002..005 の BR を保持。N1 の新規ルール。

## BR-6-BALANCE 相手別バランス（新規・N1）
- **Stories:** S6-1, S6-2, S6-4
- **BR-6-BALANCE-1 (hard):** 相手（party_name）別に、本人の received合計 / given合計 / 差分（received-given）/ 最終やりとり日（max occurred_at）を集計する。本人データのみ（A01）。
- **BR-6-BALANCE-2 (soft):** 偏り分類: |差分| が一定割合以下なら balanced、received優位なら owe（もらい超過）、given優位なら ahead（あげ超過）。
- **BR-6-BALANCE-3 (soft):** 「気になる関係」= owe かつ 最終やりとりから ATTENTION_DAYS（既定180日）経過。
- **BR-6-BALANCE-4 (hard):** 表現は損得・収支ではなく「関係のメンテナンス」のやさしい言い回し（責めない）。
- **BR-6-BALANCE-5 (hard):** 集計・分類は確定的（日付・しきい値）。

## 不変（intent-002..005）
- 本人スコープ・入力検証・監査・分類・お返し期限・given除外・トーン・贈与税・P2 体験。
