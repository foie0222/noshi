# User Stories — noshi P2 polish（intent-005）

intent-001..004 を保持し P2 を追加。各 AC（pass/fail）と Requirements トレース。横断 AC（維持）: 本人スコープ・WCAG AA。

## P2-1 ナビ
### S5-1 撮影をすぐ始められる
As a 個人の贈答管理者, I want 撮影を画面のどこからでもすぐ始めたい, so that 記録の手間を感じない。
- AC1: 撮影は中央の目立つ FAB から起動できる。
- AC2: タブは ホーム/台帳/マイページ＋中央撮影。
- Requirements: FR-5-1

## P2-2 水引モーション＋季節
### S5-2 お返し完了の達成感
As a 個人の贈答管理者, I want お返しを完了したとき気持ちよく締めくくりたい, so that 続ける励みになる。
- AC1: 完了時に水引が結ばれる短いアニメが出る（reduced-motion 尊重）。
- Requirements: FR-5-2
### S5-3 季節のやさしい後押し
As a 個人の贈答管理者, I want 季節の贈答時期にそっと気づかせてほしい, so that 出し時を逃さない。
- AC1: 季節（お中元/お歳暮/年始）に応じたナッジがホームに控えめに出る。
- Requirements: FR-5-2

## P2-3 オンボーディング/空状態
### S5-4 初めてでも迷わない
As a 個人の贈答管理者, I want 初めて開いたとき何をすればいいか分かりたい, so that すぐ価値を感じられる。
- AC1: 記録ゼロのホームは「まず1枚、撮ってみましょう」を中心に撮影導線を出す。
- AC2: ログインの第一ボタンはやさしい言い回し。
- Requirements: FR-5-3, FR-5-5

## P2-4 アクセシビリティ
### S5-5 文字を大きくできる
As a 個人の贈答管理者, I want 文字サイズを大きくできる, so that 年配でも読みやすい。
- AC1: 文字サイズ（標準/大）トグルが反映される。
- AC2: 主要要素に代替テキスト/aria、コントラスト AA。
- Requirements: FR-5-4

## system story
### S5-6 季節判定
As the noshi サービス, when 現在月を評価するとき, it must 季節（お中元6-8/お歳暮11-12/年始12-1、重なりは年始優先）を判定する。
- AC1: 判定は確定的（月ベース）。
- Requirements: FR-5-2

## カバレッジ補足
- FR-5-6（SummaryBar削除）は内部整理であり discrete ストーリーにしない（コード整理として code-generation で対応）。
- security/abuse・プライバシーは維持・再記述しない。
