# Intent — noshi P2 polish

## Prompt

UX/プロダクト設計レビュー001 の P2 一式を AI-DLC で改善実装したい。P2-1 ナビ再設計（撮影を中央FAB）/ P2-2 水引モーション＋季節ナッジ / P2-3 オンボーディング・空状態 / P2-4 アクセシビリティ / P2-5 マイクロコピー。＋未使用 SummaryBar 削除。既存 noshi の brownfield 改善。TDD。

## Summary

noshi の体験を磨き込む。ナビは撮影を中央のFABに格上げ。お返し完了時に水引が結ばれる情緒的クロージャ＋季節（お中元/お歳暮/年末年始）のやさしいナッジ。実初回の空状態とオンボーディングを整える。アクセシビリティ（文字サイズ・コントラスト・代替テキスト）とマイクロコピー（「はじめる(デモ)」等の開発者語を排除）を改善。未使用化した SummaryBar を削除。技術スタック不変。ロジックは TDD（pytest/vitest）、視覚はビルド＋スクリーンショットで検証。

## Slug

noshi-p2-polish

## Type

feature（brownfield 磨き込み）

## Upstream（入力）

- org-ai-kb/design-reviews/ux-product-review-001.md（P2-1〜5）
- intent-001..004 の成果物と実コード（backend/ frontend/）
