# Business Logic Model — noshi record given（intent-008）
## Unit scope
- Unit: noshi-service。Stories: S8-1/2。Owning: GiftLedger/GiftEvent（作成分岐）/ BFF・UI（方向選択）。
## 変更WF
- 記録作成: received→イベント作成、given→イベント無し（既存 create_record の None 応答を API で安全に扱う）。
- 確認画面: 受領/贈与 トグル（UI）。
## 不変
- given除外・本人スコープ・お返しフローは不変。
