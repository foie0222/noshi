# Requirements — noshi record given（intent-008, bugfix+feature）

## Intent summary
- Type: bug fix（＋小機能）/ Scope: 単一サービス noshi-service / Classification: brownfield / Affected repos: noshi
- intent-001..007 を保持。

## Functional requirements
- **FR-8-1 given レコード作成の修正（bug）**
  - FR-8-1.1 direction=given の記録作成は 200 を返し、お返しイベントを作らない（event=null）。500 にならない。
  - FR-8-1.2 received は従来どおりイベントを作る。given は pending に出ない（既存 BR-3-GIVEN 維持）。
- **FR-8-2 あげたの記録 UI**
  - FR-8-2.1 記録確認画面に 受領/贈与（received/given）の選択を追加する。
  - FR-8-2.2 贈与で保存すると given レコードが作成され、台帳に「贈与」として表示される。

## Non-functional requirements
- NFR は intent-001..007 を維持。本人スコープ（A01）・入力検証・監査・分類不変。given でも本人スコープ・検証は同じ。

## Assumptions
- 技術スタック不変。given は受領イベント（お返し対象）を持たない。

## Out of scope
- given に対するお返し/期限（given はお返し対象外のまま）
