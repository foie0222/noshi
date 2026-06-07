# User Stories — noshi otoshidama（intent-007）
## N2 お年玉の目安
### S7-1 年齢から相場を知る
As a 個人の贈答管理者, I want 相手の年齢からお年玉の相場を知りたい, so that 金額に迷わない。
- AC1: 年齢入力で相場レンジ（low〜high）と一言が表示される。
- AC2: 「家庭・地域で異なる一般的な目安」の注記がある。
- Requirements: FR-7-1, FR-7-2, FR-7-3
### S7-2 相場判定（system）
As the noshi サービス, when 年齢を評価するとき, it must 学齢区分に応じた相場レンジを確定的に返す。
- AC1: 区分・レンジは確定的。データ非依存。
- Requirements: FR-7-1
## 補足
- security/プライバシーは維持（本機能はデータ非依存）。
