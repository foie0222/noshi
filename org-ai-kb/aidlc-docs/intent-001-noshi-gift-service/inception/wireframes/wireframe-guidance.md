# Wireframe Guidance — noshi（MVP）

code-generation 向けの再現指示。基準ビューポート 375×812（モバイル）。中立スタイル（ブランド deferred）。
共通: 上部 AppHeader 56px、本文 16px パディング、主要タップ領域 44px 以上（WCAG AA）、コントラスト AA。

## 共通レイアウト
- 縦積み（top→bottom）。AppHeader → Main（スクロール） → （ウィザード時のみ）下部 StepProgress 固定。
- フォントスケール: 見出し 20、本文 15、補助 13。余白は 8 の倍数。
- 破壊的操作（削除）は ConfirmDialog を必須。

## login
- 上から: ロゴ（中央, 上 1/4）, IdP ボタン（全幅, 縦並び）, 区切り「または」, メール/パスワード, ログインボタン（全幅・主色）。
- 状態遷移: 送信中はボタンを LoadingIndicator 化。失敗は GenericErrorBanner（汎用文言）＋連続失敗でレート制限の注記。
- レスポンシブ: タブレット以上は中央 360px 固定幅カード。

## consent
- 上から: タイトル「ご利用にあたって」, 本文（利用目的・データ機微度・第三者PIIの扱いと削除手段）, 同意チェック, 同意して始めるボタン。
- 条件表示: 初回ログイン後のみ表示。同意済みフラグがあればスキップ。

## home / home-empty
- home: AppHeader（タイトル「noshi」, 設定アイコン右）。Main: SummaryCards（横3: もらった/あげた/差分）→ 「未完了のお返し」セクション（カードリスト, タップで event-detail）→ 直近記録。最下部に PrimaryCaptureButton（全幅・主色・「＋ 贈答を撮影」）。
- home-empty: SummaryCards の代わりに EmptyState（イラスト＋「最初の贈答を記録しよう」＋ PrimaryCaptureButton）。
- 条件: 記録件数 0 → home-empty、>0 → home。

## capture（ウィザード 1/4）
- Main: 上に CameraPreview/Dropzone（正方形, 画面幅）, 下に撮影ヒント（「ご祝儀袋・のし・送り状を撮影」）, SubmitButton（全幅）。
- StepProgress 下部固定（1/4 ハイライト）。
- 遷移: 送信 → capture-loading。

## capture-loading（loading 代表 2/4）
- Main 中央: LoadingIndicator（円形）＋「読み取り中…」＋推定時間, キャンセルリンク。
- 性能注記: 10s 超過で「もう少しかかります」を表示、タイムアウトで extract-error。

## extract-review（2/4）
- Main: 上に ImageThumb（小, 右上）, ExtractedFieldsForm（金額/氏名/関係/用途/日付を縦フォーム, 各フィールド編集可）。低信頼項目は黄色「要確認」バッジ＋フォーカス誘導。方向トグル（受領/贈与）。下部 SaveButton（全幅）。
- 条件表示: confidence<閾値 の項目に要確認バッジ。全要確認解消まで保存は警告。
- 遷移: 保存 → record-saved。

## extract-error（error 代表 2/4）
- Main: 上部 GenericErrorBanner（「うまく読み取れませんでした」＝内部情報・スタックトレースを出さない / OWASP）。下に ManualEntryForm（extract-review と同じ項目を空で）, RetryButton（撮影し直す）。
- 遷移: 手入力続行 → extract-review（手入力値を保持）/ 再試行 → capture。

## record-saved
- Main 中央: チェックアイコン＋「記録しました」＋保存サマリ（相手/金額/用途）。下に 2 ボタン: 「お返しを検討」（主色→half-return）/「ホームに戻る」（淡色→home）。

## half-return
- Main: ReceivedAmountCard（もらった額）→ SuggestedReturnRange（大きく レンジ表示）→ RuleRationale（適用ルールの根拠を箇条書き）→ OverrideInput（上書き額）。下部「次へ」→ gift-suggest。

## gift-suggest
- Main: 上に BudgetBadge（半返し額）, SuggestionList（カード: 画像プレースホルダ＋品名＋概要＋外部リンク＋「これにする」）。
- 注記: MVP は提案のみ。外部リンクは新規タブ。選択 → event-detail に紐付け。

## letter
- Main: ToneSelector（丁寧/カジュアル等のチップ）→ GeneratedLetterText（複数行・編集可）→ 下部 Copy / Export。
- 注記: 生成時に LLM へ送るデータは最小化（氏名等は不要なら送らない / S-7 AC3）。

## ledger
- Main: SearchBar（上固定）→ FilterChips（相手/用途/期間）→ GiveList（行: 方向アイコン＋相手＋金額＋用途＋日付）→ 末尾 PerPartySummary。
- 空状態: 結果 0 件は EmptyState（「記録がありません」）。
- 遷移: 行タップ → event-detail。

## event-detail
- Main: EventSummary（相手/金額/用途/日付）→ StatusStepper（受領→検討中→完了, タップで進める）→ LinkedReturn（紐付くお返し品/礼状, なければ「お返しを検討」CTA）→ Actions（編集/削除=ConfirmDialog）。

## settings
- Main: AccountSection（プロフィール/ログアウト）→ PrivacySection（同意状況/エクスポート）→ DangerZone（アカウント削除・全データ削除, 赤系, ConfirmDialog 必須, 実行は監査ログ記録 / S-2,S-13）。

## レスポンシブ全般
- 375 基準。≥768 は中央 480px のカラム＋左右余白。タッチ領域・フォントは据え置き。

## アクセシビリティ（WCAG AA）
- すべての画像/アイコンに代替テキスト。フォーム項目にラベル。フォーカス可視。コントラスト 4.5:1 以上。エラーは色だけに依存せずテキスト併記。
