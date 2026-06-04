# Wireframes — Plan

形式=SVG / ナビ=ウィザード中心＋最小ナビ / 状態=全状態網羅 / スタイル=中立(ブランド deferred)。
モバイルファースト（375×812 想定）・日本語 UI・WCAG AA。OWASP lens（エラー画面で内部情報を出さない等）。

## 生成する3つの markdown

- [x] screen-data-map.md — 画面ごとに 目的 / 表示データ / 入力データ / アクション / Source stories(S-n) / Source components(推定)
- [x] screen-structure.md — 画面インベントリ・ナビゲーションマップ・画面別コンポーネントツリー・共有コンポーネント・画面グループ
- [x] wireframe-guidance.md — 画面別の要素配置・サイズ比・状態遷移・レスポンシブ・条件表示

## 画面インベントリ（SVG: screens/<name>.svg）

オンボーディング/認証グループ
- [x] login.svg — ログイン/サインアップ（S-1）
- [x] consent.svg — 利用目的明示・同意（S-14）

ホーム
- [x] home.svg — ダッシュボード（台帳サマリ・未完了お返し・＋撮影起点）（S-4,S-8）
- [x] home-empty.svg — 空状態（初回・記録ゼロ）（empty）

撮影→記録 ウィザード（中核一本道）
- [x] capture.svg — 撮影/画像アップロード（S-3）
- [x] capture-loading.svg — AI抽出中（loading）（S-9）
- [x] extract-review.svg — 抽出結果の確認・修正（S-3）
- [x] extract-error.svg — 抽出失敗→手入力 fallback（error, 内部情報を出さない）（S-3,S-9）
- [x] record-saved.svg — 保存完了（次アクション導線）（S-3）

お返しジャーニー
- [x] half-return.svg — 半返し計算（根拠・上書き）（S-5）
- [x] gift-suggest.svg — お返し品提案（提案のみ・外部リンク）（S-6）
- [x] letter.svg — 礼状文面生成・編集（S-7）

台帳/イベント
- [x] ledger.svg — Give履歴一覧・検索・相手別/用途別（S-4）
- [x] event-detail.svg — 贈答イベント詳細・ステータス管理（S-6,S-8）

設定
- [x] settings.svg — 設定・アカウント/データ削除（S-2）

横断状態の表現
- [x] error 系は extract-error.svg で代表（汎用エラー文言・内部情報なし）
- [x] 権限/未ログイン状態は login.svg＋ガード注記で表現（過剰な画面増殖を避ける）

## 留意（scope-by-phase / lens）
- バックエンド/API設計には踏み込まない（application-design の領域）。Source components は「推定」に留める。
- OWASP: エラー画面はスタックトレース等を出さず汎用メッセージ。撮影画像の取り扱い注意を consent に明記。
