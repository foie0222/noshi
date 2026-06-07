# Requirements — noshi relationship balance（intent-006, N1）

## Intent summary
- Type: feature（brownfield）/ Scope: 単一サービス noshi-service / Classification: brownfield / Affected repos: noshi
- 源泉: design-review-002 の N1。intent-001..005 を保持。

## Functional requirements

- **FR-6-1 相手別バランス集計**
  - FR-6-1.1 相手（party_name）ごとに「もらった合計 / あげた合計 / 差分 / 最終やりとり日」を集計する。
  - FR-6-1.2 集計は本人データのみ（A01）。確定的（日付ベース）。

- **FR-6-2 偏りの気づき**
  - FR-6-2.1 相手別に偏り状態を分類する: balanced（均衡）/ owe（もらい超過）/ ahead（あげ超過）。
  - FR-6-2.2 「もらい超過 かつ 最後のやりとりから一定期間（既定180日）経過」の関係を「気になる関係」として示す。
  - FR-6-2.3 損得・収支ではなく「関係のメンテナンス」のやさしい言い回しにする（責めない）。

- **FR-6-3 おつきあいビュー**
  - FR-6-3.1 マイページに「おつきあい」一覧（相手別のバランス）を追加する。
  - FR-6-3.2 「気になる関係」を上位に、控えめに表示する。各行から相手の記録に辿れる。

## Non-functional requirements
- NFR は intent-001..005 を維持。本人スコープ（A01）・入力検証・監査・分類不変。
- 集計・偏り判定は確定的（日付・しきい値）。WCAG AA。

## Assumptions
- 技術スタック不変。相手の同定は party_name ベース（将来 Party ID 統合は別途）。
- 通知/相手への連絡はスコープ外（画面表示のみ）。「気になる」しきい値は既定180日（調整可）。

## Out of scope
- お年玉の年齢別相場（N2・次 intent）
- 自動リマインド/相手への通知
- 相手の名寄せ高度化・世帯共有
