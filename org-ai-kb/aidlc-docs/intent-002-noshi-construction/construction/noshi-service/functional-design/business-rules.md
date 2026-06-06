# Business Rules — noshi-service

hard = 違反不可の制約 / soft = 既定・上書き可。

## BR-HR 半返し（HalfReturnCalculator）
- **Stories:** S-5
- **BR-HR-1 (soft):** 用途別の推奨返礼率（初期値）:
  | 用途 | 返礼率 |
  |---|---|
  | 香典（弔事） | 1/2 |
  | 出産祝い | 1/3〜1/2（既定 1/2） |
  | 結婚祝い | 1/2 |
  | 快気祝い | 1/3〜1/2（既定 1/2） |
  | 一般慶事（入学・新築等） | 1/3〜1/2（既定 1/3） |
  | お中元・お歳暮 | 返礼不要（礼状で対応） |
- **BR-HR-2 (soft):** 推奨額は 1,000 円単位に丸める。
- **BR-HR-3 (soft):** ユーザーは推奨額を上書きでき、上書き値が以後の提案・記録に反映。
- **BR-HR-4 (hard):** もらった額 amount>0 でないと算出しない。

## BR-EX 抽出と確定
- **Stories:** S-3, S-9
- **BR-EX-1 (hard):** 抽出候補は確定前は GiftRecord にしない（中間データ）。
- **BR-EX-2 (hard):** 信頼度 < しきい値（既定 0.7）の項目は needsReview。**全項目をユーザーが確認/確定**してから保存。
- **BR-EX-3 (hard):** 抽出失敗時は手入力 fallback を提供。

## BR-VAL 入力検証（A03）
- **Stories:** S-3, S-9, S-10
- **BR-VAL-1 (hard):** 画像は許可形式・最大サイズ内のみ受理。
- **BR-VAL-2 (hard):** 金額>0、必須項目（相手・用途・日付・方向）を検証。
- **BR-VAL-3 (hard):** 外部アクター向けエラーは汎用文言（内部情報を出さない）。

## BR-AUTH 認可（A01）
- **Stories:** S-1, S-10, S-11, S-12, S-13
- **BR-AUTH-1 (hard):** すべてのリソース操作で `resource.ownerId == session.userId`。違反は FORBIDDEN。
- **BR-AUTH-2 (hard):** 認可失敗・認証試行・削除・エクスポートは AuditLog に記録（A09）。
- **BR-AUTH-3 (hard):** 認証は連続失敗でレート制限、セッション/トークンに有効期限・失効（A07）。

## BR-EVT イベント状態
- **Stories:** S-8
- **BR-EVT-1 (soft):** status は received/considering/done を**自由遷移**可。
- **BR-EVT-2 (hard):** status==done は未完了お返し一覧から除外。

## BR-RET お返し未完了
- **Stories:** S-4, S-8
- **BR-RET-1 (soft):** 「received/considering かつ お返し未完了」を未完了一覧に表示。MVP は通知なし。

## BR-SUG お返し品の提案（GiftSuggestion）
- **Stories:** S-6
- **BR-SUG-1 (soft):** 候補は 予算（半返し額）・関係・用途 から導出する。
- **BR-SUG-2 (hard):** MVP は **提案のみ**。各候補は概要＋外部参照リンクを持ち、noshi 内で購入・決済は行わない。
- **BR-SUG-3 (hard):** ユーザーが1候補を選択すると、対象の GiftEvent に紐付けて記録する。
- **BR-SUG-4 (soft):** 外部カタログ（GiftCatalogPort）が不可用なら「候補なし」を丁寧に提示し、お返しを後回し可能としてフローを継続する。
- **BR-SUG-5 (hard):** カタログへの送信は非PIIの条件（予算/用途/関係）に限定（restricted/氏名等を送らない）。

## BR-LTR 礼状生成
- **Stories:** S-7
- **BR-LTR-1 (hard):** 文面生成で外部 LLM に送るデータは最小化。restricted を不要に送らない（必要時マスキング）。

## BR-PRV プライバシー
- **Stories:** S-2, S-14
- **BR-PRV-1 (hard):** 未同意では主要機能を使えない。
- **BR-PRV-2 (hard):** 削除要求で本人の全データを削除し参照不能化（監査記録）。
