# User Stories — noshi record given（intent-008）
## あげたの記録
### S8-1 あげた贈答を記録する
As a 個人の贈答管理者, I want 自分が「あげた」贈答も記録したい, so that もらった/あげた を双方向に管理できる。
- AC1: 記録確認画面で 受領/贈与 を選べる。
- AC2: 贈与で保存すると台帳に「贈与」として表示され、未完了お返し（pending）には出ない。
- AC3: 贈与の記録作成はエラー（500）にならず正常に完了する。
- Requirements: FR-8-1, FR-8-2
## system
### S8-2 given はイベントを作らない
As the noshi サービス, when direction=given の記録が作られたとき, it must お返しイベントを作らず正常に応答する。
- AC1: given は event=null で 200。received はイベント作成。
- Requirements: FR-8-1
## 補足
- security/プライバシー維持。本人スコープ・given除外は不変。
