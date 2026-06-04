# Component Methods — noshi（論理メソッド）

入出力は論理型（言語非依存）。事前/事後条件付き。すべてのメソッドは Identity が解決した本人スコープ下で実行される（特記なき限り）。

## Identity
- **signUp(idpToken | email+secret) → Session**
  - Pre: 入力が検証済み。Post: User と Session が作成され、初回は ConsentPrivacy へ同意要求。
- **logIn(credentials) → Session**
  - Pre: レート制限内。Post: 有効な Session、または汎用認証エラー（内部情報なし）。
- **resolveScope(session) → UserId**
  - Pre: Session が有効・未失効。Post: 本人 UserId を返す。無効なら拒否。
- **logOut(session) → void** / **revokeExpired() → void**

## ConsentPrivacy
- **recordConsent(userId, purposeVersion) → ConsentRecord**
  - Pre: 本人。Post: 同意が記録される。
- **requestDeletion(userId) → DeletionTicket**
  - Pre: 本人。Post: 全データ削除が起動し、完了で参照不能。AuditLog に記録。
- **exportData(userId) → ExportBundle**
  - Pre: 本人。Post: 本人データのエクスポートを生成。AuditLog に記録。

## GiftLedger
- **createRecord(userId, GiftRecordDraft) → GiftRecord**
  - Pre: 入力検証済み・本人。Post: レコード作成。
- **updateRecord / deleteRecord(userId, recordId, ...) → GiftRecord | void**
  - Pre: recordId が本人所有。Post: 変更/削除（削除は AuditLog 記録）。
- **search(userId, filter) → GiftRecord[]**
  - Pre: 本人。Post: 本人所有レコードのみ返す（他者データは不可）。
- **summarizeByParty(userId) → PartySummary[]**
  - Post: 相手別の もらった/あげた/差分。

## Extraction
- **submitJob(userId, imageRef[]) → ExtractionJob**
  - Pre: 画像が検証済み（形式/サイズ）・本人。Post: ジョブが pending で作成、ExtractionRequested イベント発行。
- **getJob(userId, jobId) → ExtractionJob**
  - Pre: jobId が本人所有。Post: 状態（pending/completed/failed）と抽出候補＋信頼度。
- **（内部）runExtraction(jobId) → void**
  - Post: OcrLlmPort 経由で抽出、ExtractionCompleted か ExtractionFailed を発行。

## HalfReturnCalculator
- **calculate(amount, purpose) → ReturnRange**
  - Pre: amount>0, purpose 既知。Post: 推奨レンジ＋適用ルール根拠。
- **override(eventId, amount) → void**
  - Pre: 本人所有 event。Post: 上書き額を保持し以後の提案に反映。

## GiftSuggestion
- **suggest(budgetRange, relationship, purpose) → ReturnSuggestion[]**
  - Post: 候補（概要＋外部参照）。GiftCatalogPort 経由。
- **select(userId, eventId, suggestionId) → void**
  - Pre: 本人所有 event。Post: 選択を event に紐付け。

## LetterGenerator
- **generate(purpose, relationship, tone, minimalContext) → LetterDraft**
  - Pre: minimalContext は送信最小化（restricted を不要に含めない）。Post: 文面ドラフト。
- **saveEdited(userId, eventId, text) → Letter**
  - Pre: 本人所有 event。Post: 編集後文面を保持。

## GiftEvent
- **createFromRecord(userId, recordId) → GiftEvent**
  - Post: 受領イベントを作成。
- **setStatus(userId, eventId, status) → GiftEvent**
  - Pre: 本人所有・遷移が妥当（受領→検討中→完了）。Post: ステータス更新。
- **listPending(userId) → GiftEvent[]**
  - Post: お返し未完了の一覧。

## AuditLog
- **append(actorId, action, target, metadata) → void**
  - Pre: metadata に restricted 平文を含めない。Post: 追記専用で記録（改ざん不可前提）。

## BFF
- **getHome(session) → HomeView** / **getEventDetail(session, eventId) → EventView** / **getLedger(session, filter) → LedgerView**
  - Pre: resolveScope で本人確定・入力検証。Post: 複数コンポーネントを集約し、本人スコープのデータのみ返す。
