# Screen Structure — noshi（MVP）

モバイルファースト（基準 375×812）。ナビ=ウィザード中心＋最小ナビ。日本語 UI / WCAG AA。

## Screen inventory（階層）

- 認証/オンボーディング群
  - `login` ログイン/サインアップ
  - `consent` 利用目的明示・同意（初回のみ）
- ホーム群
  - `home` ダッシュボード（既定の起点）
    - `home-empty` 空状態（記録ゼロ）
- 撮影→記録ウィザード（一本道）
  - `capture` 撮影/画像アップロード
    - `capture-loading` AI抽出中
    - `extract-review` 抽出結果の確認・修正
    - `extract-error` 抽出失敗→手入力 fallback
    - `record-saved` 保存完了
- お返しジャーニー
  - `half-return` 半返し計算
  - `gift-suggest` お返し品提案
  - `letter` 礼状文面生成・編集
- 台帳/イベント群
  - `ledger` Give履歴一覧
  - `event-detail` 贈答イベント詳細・ステータス
- 設定群
  - `settings` 設定・アカウント/データ削除

## Navigation map

- アプリ起動 → 未ログインなら `login`。初回ログイン直後は `consent` を1度だけ挟み `home` へ。
- `home` から:
  - 主導線「＋撮影」→ ウィザード `capture` を開始。
  - 「台帳」→ `ledger`。「設定」→ `settings`。未完了お返しカード → `event-detail`。
- 撮影ウィザード（戻る可・離脱可の一本道）:
  - `capture` →（送信）→ `capture-loading` →（成功）→ `extract-review` /（失敗）→ `extract-error`
  - `extract-error` →（手入力）→ `extract-review`
  - `extract-review` →（保存）→ `record-saved`
  - `record-saved` →「お返しを検討」→ `half-return` → `gift-suggest` → `letter` → `event-detail`（完了化）
  - `record-saved` →「ホームに戻る」→ `home`
- `ledger` ⇄ `event-detail`（項目タップで詳細、戻るで一覧）。
- `event-detail` から `half-return`/`gift-suggest`/`letter` に再入可（お返し未完了の続き）。
- 最小ナビ: 上部に戻る、ウィザード中はステッパー。常時タブバーは持たない（ウィザード中心方針）。`home`/`ledger`/`settings` 間は home のメニューから遷移。

## Component tree per screen（主要画面）

- 共通フレーム: `StatusBar` → `AppHeader`(戻る/タイトル/任意アクション) → `Main` → （ウィザード時）`StepProgress`。
- `home`: AppHeader → Main[ SummaryCards(収支/今月) , PendingReturnsList(未完了お返し) , PrimaryCaptureButton ] 。
- `capture`: AppHeader → Main[ CameraPreview/Dropzone , CaptureHint , SubmitButton ] → StepProgress(1/4)。
- `extract-review`: AppHeader → Main[ ExtractedFieldsForm(金額/氏名/関係/用途/日付・各 編集可・低信頼バッジ) , ImageThumb , SaveButton ] → StepProgress(2/4)。
- `extract-error`: AppHeader → Main[ GenericErrorBanner(汎用文言) , ManualEntryForm , RetryButton ] → StepProgress(2/4)。
- `half-return`: AppHeader → Main[ ReceivedAmountCard , SuggestedReturnRange , RuleRationale , OverrideInput ] 。
- `gift-suggest`: AppHeader → Main[ BudgetBadge , SuggestionList(候補カード=概要+外部リンク+選択) ] 。
- `letter`: AppHeader → Main[ ToneSelector , GeneratedLetterText(編集可) , Copy/Exportボタン ] 。
- `ledger`: AppHeader → Main[ SearchBar , FilterChips(相手/用途/期間) , GiveList(方向アイコン+相手+金額+用途+日付) , PerPartySummary ] 。
- `event-detail`: AppHeader → Main[ EventSummary , StatusStepper(受領→検討中→完了) , LinkedReturn , Actions ] 。
- `settings`: AppHeader → Main[ AccountSection , PrivacySection , DangerZone(アカウント/データ削除) ] 。
- `login`/`consent`: AppHeader(最小) → Main[ フォーム / 同意本文+同意ボタン ]。

## Shared components

- `AppHeader`（戻る・タイトル・任意アクション）
- `StepProgress`（撮影ウィザードのステッパー）
- `PrimaryCaptureButton`（＋撮影の主導線）
- `GenericErrorBanner`（汎用エラー。内部情報を出さない＝OWASP）
- `EmptyState`（イラスト＋説明＋CTA）
- `LoadingIndicator`（抽出中・送信中）
- `ConfirmDialog`（削除など破壊的操作の確認）

## Screen groups

- onboarding-flow: `login`, `consent`
- capture-wizard: `capture`, `capture-loading`, `extract-review`, `extract-error`, `record-saved`
- return-journey: `half-return`, `gift-suggest`, `letter`
- ledger-views: `home`, `home-empty`, `ledger`, `event-detail`
- settings: `settings`

## 状態の扱い（全状態網羅・画面増殖を抑える方針）

- loading: `capture-loading`（代表）。他画面の送信中は `LoadingIndicator` をオーバーレイ表示として guidance に記述。
- empty: `home-empty`（代表）。`ledger` の空は EmptyState コンポーネントで表現（guidance 記述）。
- error: `extract-error`（代表・汎用文言）。他のエラーは `GenericErrorBanner` を共有。
- 権限/未ログイン: `login` にガード。保護リソースへの未認証アクセスは login へリダイレクト（S-10/S-11 と整合）。
