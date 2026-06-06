# Functional Design — Validation (intent-003, self)

STATUS: PASS
- Unit scope 明記（noshi-service / S3-1..5 / owning components）。
- ルール双方向トレース: BR-3-DUE→S3-1/2/5, BR-3-GIVEN→S3-4, BR-3-CONF→S3-3。全 S3 被覆、孤立ルールなし。
- エンティティ差分（GiftEvent.due_at/days_left=internal）に分類付与・不変条件（given除外）・ライフサイクル不変。
- hard/soft 区別、技術非依存（日数・昇順等は論理）、intent-002 ルールと矛盾なし（received限定は BR-EVT を明示的に上書き）。
owasp（stage=functional-design, 8）: due_at は internal の派生で新規機微フローなし。本人スコープ(A01)・入力検証(A03)・監査(A09)・分類は intent-002 を維持→1-8 満たす。

---PROCESS-CHECK-DATA---
STATUS: PASS
TOOLS: none
RULES: 1,2,3,4,5,6,7,8,9,10,11,12,13,14
LENS-RULES: owasp:1,2,3,4,5,6,7,8
---END-PROCESS-CHECK-DATA---
