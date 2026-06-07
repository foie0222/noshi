# Intent — noshi P1 improvements

## Prompt

UX/プロダクト設計レビュー（org-ai-kb/design-reviews/ux-product-review-001.md）の P1 一式を AI-DLC で改善実装したい。P1-1 弔事/慶事トーン / P1-2 信頼の可視化 / P1-3 贈与税110万枠の気づき。既存 noshi 実装（backend FastAPI + frontend React/TS）を入力とする brownfield 改善。TDD。

## Summary

intent-001/002/003 で構築・改善した noshi に、UX レビュー 001 の P1 提案を実装する。
- P1-1: 香典等の弔事文脈で配色・コピーを静かなトーンに切替（慶事は現状）。
- P1-2: 機微な第三者PIIを扱う安心を felt trust として可視化（氏名入力時の「あなただけが見られます」＋鍵）。
- P1-3: 暦年で「もらった」合計を集計し、贈与税の基礎控除110万円枠への接近を知らせる（税アドバイスではなく気づき・注意喚起）。
技術スタック不変（Python/FastAPI + React/TS、InMemory+モックでローカル動作）。TDD（pytest/vitest、日本語の検証説明）。

## Slug

noshi-p1-improvements

## Type

feature（brownfield 改善）

## Upstream（入力）

- org-ai-kb/design-reviews/ux-product-review-001.md（P1-1〜3）
- intent-001/002/003 の成果物と実コード（backend/ frontend/）
