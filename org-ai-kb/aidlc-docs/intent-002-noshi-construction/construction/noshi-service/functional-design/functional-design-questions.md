# Functional Design — Clarification Questions（unit: noshi-service）

入力: intent-001 の stories/components/component-methods/data-models/cross-cutting。Lens: OWASP。
単一ユニット（noshi-service 全体）。units-of-work は collapse 済み（= MVP 全機能が1ユニット）。
技術非依存。core の業務ロジックのうち、人間判断が効く点を確認する。

### Q1: 半返しの返礼率ルール（HalfReturnCalculator のアルゴリズム）

用途別の推奨返礼率の初期値（上書き可）。

| 用途 | 初期の推奨率 |
|---|---|
| 香典（弔事） | もらった額の 1/2（半返し） |
| 出産祝い | 1/3 〜 1/2 |
| 結婚祝い | 1/2（引出物がある場合は調整） |
| 快気祝い | 1/3 〜 1/2 |
| 入学・新築など一般慶事 | 1/3 〜 1/2 |
| お中元・お歳暮 | 返礼不要（礼状で対応）が基本 |

a) この初期ルールで実装（端数は1,000円単位で丸め・上書き可）
b) 調整したい（具体値を指定）

**Recommendation:** a) 上記を初期値として実装し、ユーザー上書きを許可。

[Answer]: a) 推奨初期値で実装（1,000円丸め・上書き可）

### Q2: AI抽出の確定方針（Extraction → 確認）

a) 信頼度がしきい値未満の項目は「要確認」フラグ。全項目をユーザーが確認・確定してから保存（誤記録を防ぐ）
b) 高信頼なら自動確定し、低信頼のみ確認

**Recommendation:** a) 確認を挟む（wireframes の extract-review と整合・OWASP の入力検証）。

[Answer]: a) 全項目確認して保存

### Q3: 贈答イベントのステータス遷移ルール

received（受領）→ considering（検討中）→ done（完了）。

a) 前方遷移のみ（done から戻すには明示の「再開」操作）。スキップ不可（received→done は不可、considering を経由）
b) 自由に行き来できる

**Recommendation:** a) 前方基本＋明示再開。不変条件: done のイベントは未完了一覧に出ない。

[Answer]: b) 自由に行き来できる（ただし done は未完了一覧に出さない）

### Q4: お返し未完了の判定とリマインド範囲（MVP）

a) 「received/considering かつお返し未完了」を未完了として一覧表示（リマインド通知は MVP 対象外）
b) 通知/リマインドも MVP に含める

**Recommendation:** a) 一覧表示のみ（通知は将来）。

[Answer]: a) 一覧表示のみ（通知は将来）
