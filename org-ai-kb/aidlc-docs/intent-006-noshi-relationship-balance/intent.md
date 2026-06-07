# Intent — noshi relationship balance (N1)

## Prompt
design-review-002 の N1「親族間バランスの気づき」を AI-DLC で実装したい。相手別の もらった/あげた/差分・最終やりとり時期を可視化し、偏りをやさしく気づかせる。既存台帳データのみ。brownfield・TDD。

## Summary
相手（Party）ごとに、もらった/あげた合計・差分・最後のやりとり時期を集計し、「関係のメンテナンス」の観点で偏りを気づかせる「おつきあい」ビューを追加する。損得ではなく、長くお贈りしていない/もらってばかりの関係にそっと気づける形。本人データのみ（A01）。技術スタック不変、TDD。

## Slug
noshi-relationship-balance

## Type
feature（brownfield・関係バランス）

## Upstream（入力）
- org-ai-kb/design-reviews/ux-product-review-002.md（N1）
- intent-001..005 の成果物と実コード
