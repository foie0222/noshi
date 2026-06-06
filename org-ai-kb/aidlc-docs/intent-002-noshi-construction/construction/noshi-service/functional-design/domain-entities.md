# Domain Entities — noshi-service（技術非依存・精緻化）

application-design/data-models.md を実装可能な粒度に精緻化。**全フィールドに分類**を付与（OWASP: restricted/confidential/internal/public）。

## User
- 属性:
  - id (internal)
  - authIdentifier (restricted) — メール/IdP subject
  - secretHash (restricted) — IdP 利用時は無し
  - createdAt (internal)
- 関係: 1—1 ConsentRecord, 1—* Party/GiftRecord/GiftEvent
- 不変条件: authIdentifier 一意。
- ライフサイクル: signUp で作成 → 利用中 → 削除要求で本人の全関連と共に削除（terminal）。

## ConsentRecord
- 属性:
  - id (internal)
  - userId (internal)
  - purposeVersion (internal)
  - consentedAt (internal)
- 関係: *—1 User
- 不変条件: 最新同意バージョンを保持。未同意では主要機能を使えない。
- ライフサイクル: 初回同意で作成 → 目的バージョン更新時に更新 → User 削除で削除（terminal）。

## Party（贈答相手）
- 属性:
  - id (internal)
  - userId (internal)
  - name (confidential)
  - relationship (confidential)
  - address (confidential, optional)
  - note (confidential, optional)
- 関係: *—1 User, 1—* GiftRecord
- 不変条件: userId スコープ内。第三者PII。
- ライフサイクル: レコード作成時に必要なら作成 → 参照/更新 → 参照ゼロ or User 削除で削除（terminal）。

## GiftRecord（贈答レコード）
- 属性:
  - id (internal)
  - userId (internal)
  - partyId (internal)
  - direction (internal) — received/given
  - amount (confidential, >0)
  - purpose (confidential)
  - occurredAt (confidential)
  - memo (confidential, optional)
  - sourceImageRef (confidential, optional)
- 関係: *—1 User, *—1 Party, 1—0..1 GiftEvent
- 不変条件: amount>0, direction 必須, 本人所有。
- ライフサイクル: 確認確定で作成 → 編集 → 削除（監査記録, terminal）。

## ExtractionJob
- 属性:
  - id (internal)
  - userId (internal)
  - imageRef[] (confidential)
  - status (internal) — pending/completed/failed
  - candidates (confidential) — 確定前の抽出項目
  - confidence (internal) — 0–1
  - needsReview[] (internal) — 低信頼項目フラグ
  - createdAt (internal)
- 関係: *—1 User
- 不変条件: 本人所有。candidates は確定前の中間データ。
- ライフサイクル: submit→pending → completed/failed → 確定後は短期保持し破棄（terminal）。

## GiftEvent（状態モデル）
- 属性:
  - id (internal)
  - userId (internal)
  - recordId (internal)
  - status (internal) — received/considering/done
  - overrideReturnAmount (confidential, optional)
  - createdAt (internal)
  - updatedAt (internal)
- **状態:** received / considering / done（**自由遷移**: owner は任意の状態へ遷移可）
- 不変条件: status==done のイベントは未完了一覧に含めない。recordId は本人所有。
- 関係: 1—1 GiftRecord, 1—0..1 ReturnSuggestion, 1—0..1 Letter
- ライフサイクル: 受領レコードから作成 → 状態遷移 → User/レコード削除で削除（terminal）。

## ReturnSuggestion
- 属性:
  - id (internal)
  - eventId (internal)
  - title (internal)
  - summary (internal)
  - externalRef (internal) — 外部リンク
  - priceBand (internal)
- 関係: *—1 GiftEvent
- 不変条件: 購入/決済情報は持たない（提案のみ）。
- ライフサイクル: 提案時に生成 → 選択で event に紐付け → 再提案で置換 or event 削除で削除（terminal）。

## Letter
- 属性:
  - id (internal)
  - eventId (internal)
  - tone (internal)
  - bodyText (confidential) — 宛名等を含みうる
  - updatedAt (internal)
- 関係: *—1 GiftEvent
- 不変条件: 本人所有。生成時の外部送信は最小化。
- ライフサイクル: 生成で作成 → 編集保存 → event 削除で削除（terminal）。

## AuditEntry
- 属性:
  - id (internal)
  - actorId (internal)
  - action (internal)
  - targetRef (internal) — 識別子のみ
  - at (internal)
  - metadata (internal) — 平文 restricted 禁止
- 関係: *—1 User（actor）
- 不変条件: 追記専用・改ざん不可前提。restricted を平文で持たない。
- ライフサイクル: セキュリティイベント発生時に追記 → 保持期間ポリシーに従い失効/削除（terminal、追記後は不変）。
