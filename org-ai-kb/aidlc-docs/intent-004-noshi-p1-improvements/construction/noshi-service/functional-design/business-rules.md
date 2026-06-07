# Business Rules — noshi P1 improvements（intent-004, unit: noshi-service）

intent-002/003 の BR を保持し、P1 の新規ルールを定義（差分）。hard=制約 / soft=既定。

## BR-4-TONE 弔事/慶事トーン（新規・P1-1）
- **Stories:** S4-1, S4-4
- **BR-4-TONE-1 (soft):** 用途を弔事/慶事に分類する。弔事キーワード: 香典 / 御霊前 / 御仏前 / 法事 / 法要 / 弔慰 / お悔やみ。該当しなければ慶事。
- **BR-4-TONE-2 (soft):** 弔事の画面は静かな配色（朱→墨/グレー系）、コピーを控えめに（祝意語を避ける）。
- **BR-4-TONE-3 (hard):** 弔事トーンでもコントラストは AA を満たす。

## BR-4-TAX 贈与税110万枠の気づき（新規・P1-3）
- **Stories:** S4-3, S4-4
- **BR-4-TAX-1 (hard):** 集計対象は direction=received のレコードのうち、**社会通念上の贈答（香典・お中元・お歳暮）を除外**したもの。
- **BR-4-TAX-2 (soft):** 集計期間は暦年（対象年の1/1〜12/31、occurred_at ベース、日本時間）。既定は今年。
- **BR-4-TAX-3 (soft):** 基礎控除 EXEMPTION=1,100,000円。remaining = max(0, EXEMPTION − total)。over = total > EXEMPTION。
- **BR-4-TAX-4 (hard):** これは概算の気づきであり税務助言ではない旨を必ず併記。集計は本人データのみ（A01）。

## BR-4-TRUST 信頼の可視化（新規・P1-2）
- **Stories:** S4-2
- **BR-4-TRUST-1 (soft):** 氏名/相手入力の近く・consent・設定に「本人だけが見られる」安心表示を出す。
- **BR-4-TRUST-2 (hard):** 表示のみ。実体の認可（本人スコープ A01）は変更しない。

## 不変（intent-002/003 から維持）
- 本人スコープ(A01)・入力検証(A03)・汎用エラー・監査(A09)・分類・お返し期限(BR-3-DUE)・given除外(BR-3-GIVEN)・半返し(BR-HR)。
