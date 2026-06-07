# Business Rules — noshi record given（intent-008）
intent-002..007 の BR を保持。

## BR-8-GIVEN-RECORD あげたの記録（修正・新規）
- **Stories:** S8-1, S8-2
- **BR-8-GIVEN-RECORD-1 (hard):** direction=given の記録作成はイベントを作らず正常応答（event=null）。received はイベント作成（既存）。
- **BR-8-GIVEN-RECORD-2 (hard):** given は pending お返しに出さない（BR-3-GIVEN 維持）。台帳には表示。
- **BR-8-GIVEN-RECORD-3 (hard):** 入力検証（BR-VAL）・本人スコープ（A01）は received/given 共通。
