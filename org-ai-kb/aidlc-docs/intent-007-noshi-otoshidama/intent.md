# Intent — noshi otoshidama (N2)

## Prompt
design-review-002 の N2「お年玉の年齢別相場」を AI-DLC で実装したい。年齢（学齢）から一般的な相場レンジを提示し、金額の不安を解消する。brownfield・TDD。

## Summary
お年玉をあげる際の金額の不安を、年齢（学齢）に応じた一般的な相場レンジの提示で解消する小さなツールを追加する。マイページに「お年玉の目安」として、年齢入力→相場レンジ＋一言。あくまで一般的な目安（家庭・地域で異なる旨を明記）。本人操作のみ・データ非依存。stack 不変・TDD。

## Slug
noshi-otoshidama

## Type
feature（brownfield・お年玉相場）

## Upstream（入力）
- org-ai-kb/design-reviews/ux-product-review-002.md（N2）
- intent-001..006 の成果物と実コード
