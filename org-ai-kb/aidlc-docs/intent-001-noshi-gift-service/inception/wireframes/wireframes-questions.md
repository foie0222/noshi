# Wireframes — Clarification Questions

Input: stories.md（S-1..14）, personas.md, requirements.md。
要件から確定済み（質問しない）: モバイルファースト・レスポンシブ Web（NFR-4.1）、日本語 UI（単一言語）、WCAG 2.1 AA（NFR-4.2）。

### Q1: ワイヤーフレームの出力形式

a) SVG（静的レイアウト確認・最速）
b) HTML プロトタイプ（インタラクション・実機の手触り確認可、作成は重い）

**Trade Offs:** 構想段階のレイアウト合意なら SVG が速い。HTML は触れる代わりに工数大。code-generation は3つの markdown を主入力にするため、視覚物は「レイアウト参照」目的。

**Recommendation:** a) SVG。

[Answer]: a) SVG

### Q2: ナビゲーションモデル

a) 下部タブバー（モバイル定番: ホーム / 台帳 / ＋撮影 / お返し / 設定）
b) サイドバー/ハンバーガー
c) ウィザード中心（撮影→記録の一本道）＋最小ナビ

**Recommendation:** a) 下部タブバー。中央に「＋撮影」を強調する FAB 風。

[Answer]: c) ウィザード中心（撮影→記録の一本道）＋最小ナビ

### Q3: カバーする画面状態

a) ハッピーパス＋主要な空状態/エラー（空の台帳、抽出失敗、未完了お返し）
b) ハッピーパスのみ
c) 全状態（loading/empty/error/権限）網羅

**Recommendation:** a) ハッピーパス＋要の空/エラー（noshi は抽出失敗・空台帳の体験が重要）。

[Answer]: c) 全状態（loading/empty/error/権限）網羅

### Q4: ブランド/デザインシステムの扱い

a) 中立スタイルで進め、ブランド（色・タイポ・ロゴ）は後日 org-ai-kb/design-system に定義（deferred を明記）
b) 既存のデザインシステム/CSSフレームワークがある（指定する）
c) 今ここで簡易ブランド方針を決める（和の落ち着いた配色など）

**Recommendation:** a) 中立で進め、ブランドは deferred。

[Answer]: a) 中立スタイルで進め、ブランドは deferred（org-ai-kb/design-system に後日）
