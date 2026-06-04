# Data Models — noshi（ドメインエンティティ）

論理型（DB非依存）。各フィールドにデータ分類（restricted/confidential/internal/public）を付与（OWASP）。

## User（owner: Identity）
- **Fields:** id(internal), authIdentifier(restricted: メール/IdP subject), secretHash(restricted), createdAt(internal)
- **Relationships:** 1—1 ConsentRecord, 1—* GiftRecord/Party/GiftEvent
- **Constraints:** authIdentifier は一意。
- **Lifecycle:** signUp で作成。削除要求で本人の全関連データと共に削除。

## ConsentRecord（owner: ConsentPrivacy）
- **Fields:** id(internal), userId(internal), purposeVersion(internal), consentedAt(internal)
- **Relationships:** *—1 User
- **Constraints:** 最新の同意バージョンを保持。
- **Lifecycle:** 同意時に作成・更新。

## Party（贈答相手）（owner: GiftLedger）
- **Fields:** id(internal), userId(internal), name(confidential), relationship(confidential), address(confidential, optional), note(confidential, optional)
- **Relationships:** *—1 User, 1—* GiftRecord
- **Constraints:** userId スコープ内で名寄せ。第三者PIIのため confidential。
- **Lifecycle:** レコード作成時に必要なら作成。User 削除で削除。

## GiftRecord（贈答レコード）（owner: GiftLedger）
- **Fields:** id(internal), userId(internal), partyId(internal), direction(internal: received/given), amount(confidential), purpose(confidential), occurredAt(confidential), memo(confidential, optional), sourceImageRef(confidential, optional)
- **Relationships:** *—1 User, *—1 Party, 1—0..1 GiftEvent
- **Constraints:** amount>0、direction 必須、本人所有。
- **Lifecycle:** 確認確定で作成。編集/削除（削除は監査記録）。

## ExtractionJob（owner: Extraction）
- **Fields:** id(internal), userId(internal), imageRef[](confidential), status(internal: pending/completed/failed), candidates(confidential: 抽出項目), confidence(internal), createdAt(internal)
- **Relationships:** *—1 User
- **Constraints:** 本人所有。candidates は確定前の中間データ。
- **Lifecycle:** submit で pending、完了/失敗で更新。確定後は短期保持し破棄可。

## GiftEvent（owner: GiftEvent）
- **Fields:** id(internal), userId(internal), recordId(internal), status(internal: received/considering/done), overrideReturnAmount(confidential, optional), createdAt/updatedAt(internal)
- **Relationships:** *—1 User, 1—1 GiftRecord, 1—0..1 ReturnSuggestion, 1—0..1 Letter
- **Constraints:** status 遷移は received→considering→done。本人所有。
- **Lifecycle:** 受領レコードから作成。完了で確定。

## ReturnSuggestion（owner: GiftSuggestion）
- **Fields:** id(internal), eventId(internal), title(internal), summary(internal), externalRef(internal: 外部リンク), priceBand(internal)
- **Relationships:** *—1 GiftEvent
- **Constraints:** MVP は提案のみ（購入情報を持たない）。
- **Lifecycle:** 提案時に生成、選択で event に紐付け。

## Letter（owner: LetterGenerator）
- **Fields:** id(internal), eventId(internal), tone(internal), bodyText(confidential: 宛名等を含みうる), updatedAt(internal)
- **Relationships:** *—1 GiftEvent
- **Constraints:** 本人所有。
- **Lifecycle:** 生成・編集保存。

## AuditEntry（owner: AuditLog）
- **Fields:** id(internal), actorId(internal), action(internal), targetRef(internal: 識別子のみ), at(internal), metadata(internal: 平文restricted禁止)
- **Relationships:** *—1 User（actor）
- **Constraints:** 追記専用・改ざん不可前提。restricted を平文で持たない。
- **Lifecycle:** セキュリティイベント発生時に追記。保持期間ポリシーに従う。
