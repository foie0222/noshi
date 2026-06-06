# Functional Design — Clarification（intent-003, auto）
P0 のドメイン差分。genuine ambiguity なし、要件で確定済み。
### Q1 期限ルール
[Answer]: requirements/BR-3-DUE のとおり（香典+49日、他+1ヶ月、中元歳暮なし、受領日起点、残日数、超過、昇順）。
### Q2 given
[Answer]: received のみ受領イベント生成（BR-3-GIVEN）。
### Q3 撮影確認
[Answer]: 高信頼=確定、低信頼のみ要確認、要確認ゼロで即保存（BR-3-CONF）。
