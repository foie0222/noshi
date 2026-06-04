# Screen Data Map — noshi（MVP）

各画面の 目的 / 表示データ / 入力データ / アクション / Source stories / Source components(推定)。
Source components は推定であり、最終決定は application-design が行う。

## login
- **Purpose:** 本人がサインアップ/ログインする
- **Data displayed:** ロゴ, ログイン手段（外部IdPボタン, メール欄）
- **Data submitted:** メールアドレス, パスワード or IdP トークン
- **Actions:** ログイン → 成功で `home`（初回は `consent`）/ 失敗で汎用エラー＋レート制限
- **Source stories:** S-1, S-12
- **Source components(推定):** AuthService

## consent
- **Purpose:** 利用目的の明示と同意取得（第三者PII含む）
- **Data displayed:** 利用目的, データ機微度の説明, 第三者PIIの扱い・削除手段
- **Data submitted:** 同意チェック
- **Actions:** 同意 → `home` / 拒否 → 利用不可案内
- **Source stories:** S-14
- **Source components(推定):** ConsentService / UserProfile

## home
- **Purpose:** 台帳サマリと未完了お返しを俯瞰し、撮影を起点化
- **Data displayed:** 収支サマリ(もらった/あげた/差分), 未完了お返し一覧, 直近記録
- **Data submitted:** なし（ナビのみ）
- **Actions:** ＋撮影 → `capture` / 未完了カード → `event-detail` / 台帳 → `ledger` / 設定 → `settings`
- **Source stories:** S-4, S-8
- **Source components(推定):** LedgerService, EventService

## home-empty
- **Purpose:** 記録ゼロ時のオンボーディング誘導
- **Data displayed:** 空状態イラスト, 「最初の贈答を記録しよう」説明
- **Data submitted:** なし
- **Actions:** ＋撮影 → `capture`
- **Source stories:** S-4
- **Source components(推定):** LedgerService

## capture
- **Purpose:** ご祝儀袋/贈答品の画像を取り込む
- **Data displayed:** カメラプレビュー/アップロード領域, 撮影ヒント
- **Data submitted:** 画像ファイル（1枚以上）
- **Actions:** 送信 → `capture-loading`（抽出開始）
- **Source stories:** S-3
- **Source components(推定):** ExtractionService, MediaStorage

## capture-loading
- **Purpose:** AI抽出中の進捗提示（p95<10s）
- **Data displayed:** ローディング, 進捗/推定時間, キャンセル
- **Data submitted:** なし
- **Actions:** 成功 → `extract-review` / 失敗 → `extract-error` / キャンセル → `capture`
- **Source stories:** S-9
- **Source components(推定):** ExtractionService

## extract-review
- **Purpose:** 抽出結果を確認・修正して確定保存
- **Data displayed:** 抽出項目(金額/氏名/関係/用途/日付), 低信頼バッジ, 画像サムネ
- **Data submitted:** 各項目の修正値, 方向(受領/贈与)
- **Actions:** 保存 → `record-saved` / 各項目編集
- **Source stories:** S-3, S-9
- **Source components(推定):** ExtractionService, LedgerService

## extract-error
- **Purpose:** 抽出失敗時の手入力 fallback（汎用エラー）
- **Data displayed:** 汎用エラーメッセージ（内部情報を出さない＝OWASP）
- **Data submitted:** 手入力の各項目（金額/氏名/関係/用途/日付）
- **Actions:** 再試行 → `capture` / 手入力で続行 → `extract-review`
- **Source stories:** S-3, S-9
- **Source components(推定):** LedgerService

## record-saved
- **Purpose:** 保存完了と次アクション導線
- **Data displayed:** 保存サマリ, 次の選択肢
- **Data submitted:** なし
- **Actions:** お返しを検討 → `half-return` / ホーム → `home`
- **Source stories:** S-3, S-7(イベント)
- **Source components(推定):** LedgerService, EventService

## half-return
- **Purpose:** 推奨お返し額の算出・根拠提示・上書き
- **Data displayed:** もらった額, 推奨レンジ, 適用ルールの根拠
- **Data submitted:** 上書き額（任意）
- **Actions:** 次へ → `gift-suggest`
- **Source stories:** S-5
- **Source components(推定):** HalfReturnCalculator

## gift-suggest
- **Purpose:** 予算・関係・用途に合うお返し品候補の提示（提案のみ）
- **Data displayed:** 予算バッジ, 候補カード（概要＋外部リンク）
- **Data submitted:** 選択した候補
- **Actions:** 選択 → イベントに紐付け → `event-detail` / 外部リンク → 別タブ
- **Source stories:** S-6
- **Source components(推定):** SuggestionService, EventService

## letter
- **Purpose:** 礼状文面の生成と編集
- **Data displayed:** トーン選択, 生成文面（編集可）
- **Data submitted:** トーン/相手/用途, 編集後本文
- **Actions:** 生成 / コピー / 書き出し → `event-detail`
- **Source stories:** S-7
- **Source components(推定):** LetterGenerator(LLM, 送信最小化)

## ledger
- **Purpose:** もらった/あげたの一覧・検索・集計
- **Data displayed:** 検索結果リスト(方向/相手/金額/用途/日付), 相手別サマリ(合計/差分)
- **Data submitted:** 検索語, フィルタ(相手/用途/期間)
- **Actions:** 項目タップ → `event-detail` / フィルタ適用
- **Source stories:** S-4
- **Source components(推定):** LedgerService

## event-detail
- **Purpose:** 1件の贈答イベントの詳細とステータス管理
- **Data displayed:** イベント詳細, ステータス(受領→検討中→完了), 紐付くお返し/礼状
- **Data submitted:** ステータス変更
- **Actions:** ステータス更新 / お返し続き → `half-return`等 / 編集・削除
- **Source stories:** S-6, S-8
- **Source components(推定):** EventService, LedgerService

## settings
- **Purpose:** アカウント設定とデータ削除
- **Data displayed:** プロフィール, プライバシー設定, Danger Zone
- **Data submitted:** 設定変更, 削除要求（確認ダイアログ）
- **Actions:** アカウント/データ削除（監査記録）/ ログアウト
- **Source stories:** S-2
- **Source components(推定):** UserProfile, AuthService, AuditLog
