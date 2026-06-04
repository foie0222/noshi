# Component Dependencies — noshi

通信パターン: sync = 同期呼び出し / event = 非同期イベント / port = 外部ポート経由。
すべての外部入力は BFF（トラスト境界）で検証され、Identity が本人スコープを解決してから下流に渡る。

## 依存マトリクス

| From | To | パターン | 根拠 |
|---|---|---|---|
| BFF | Identity | sync | リクエストの本人スコープ解決・認可 |
| BFF | GiftLedger | sync | home/ledger の台帳データ集約 |
| BFF | GiftEvent | sync | 未完了お返し・イベント詳細の集約 |
| BFF | Extraction | sync | ジョブ投入・状態取得 |
| BFF | HalfReturnCalculator | sync | 半返し算出の提示 |
| BFF | GiftSuggestion | sync | お返し候補の取得 |
| BFF | LetterGenerator | sync | 礼状生成の取得 |
| BFF | ConsentPrivacy | sync | 同意状況・削除/エクスポート要求 |
| Extraction | OcrLlmPort | port | 画像→項目抽出（外部 OCR/LLM、内部ポート隔離） |
| Extraction | GiftLedger | event | ExtractionCompleted を受け、確認後にレコード化（確定はユーザー操作） |
| GiftSuggestion | GiftCatalogPort | port | 外部カタログ参照（提案のみ） |
| LetterGenerator | OcrLlmPort | port | 文面生成（LLM、送信最小化） |
| GiftEvent | GiftLedger | sync | レコードからイベント生成・参照 |
| HalfReturnCalculator | GiftEvent | sync | 上書き額をイベントに反映 |
| GiftSuggestion | GiftEvent | sync | 選択候補をイベントに紐付け |
| LetterGenerator | GiftEvent | sync | 礼状をイベントに紐付け |
| Identity | AuditLog | event | 認証試行・認可失敗の記録 |
| ConsentPrivacy | AuditLog | event | 削除・エクスポートの記録 |
| GiftLedger | AuditLog | event | レコード削除の記録 |

## イベント駆動部分
- Extraction の抽出処理のみ非同期（ExtractionRequested/Completed/Failed）。loading 画面と整合。
- AuditLog への記録はイベント（同期処理をブロックしない）。

## 循環依存
- なし。BFF→下流、下流→AuditLog（一方向）、Extraction↔GiftLedger はイベント（Extraction→event→確認→Ledger）と参照（GiftEvent→Ledger）で循環を回避。
- HalfReturn/Suggestion/Letter → GiftEvent は書き込み方向のみ。GiftEvent → これらへの逆依存は持たない。
