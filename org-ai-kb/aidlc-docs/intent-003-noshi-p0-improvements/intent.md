# Intent — noshi P0 improvements

## Prompt

UX/プロダクト設計レビュー（org-ai-kb/design-reviews/ux-product-review-001.md）の P0 一式を AI-DLC で改善実装したい。P0-1 お返し期限ダッシュボード / P0-2 撮影レビューの要所だけ確認 / P0-3 収支フレーミング見直し / 負債#1 given 除外。既存 noshi 実装（backend FastAPI + frontend React/TS）を入力とする brownfield 改善。TDD。

## Summary

intent-001/002 で構築した動く noshi MVP を、UX レビュー 001 の P0 提案に沿って改善する。中核は「お返し期限」を製品の心臓に据えること（ホームを残日数順ダッシュボードへ）、撮影体験の魔法を保つこと、贈答にふさわしいフレーミングへ寄せること、given を未完了から外すこと。技術スタックは現状維持（Python/FastAPI + React/TS + DynamoDB、InMemory+モックでローカル動作）。TDD（pytest/vitest、日本語の検証説明）で既存コードを改修する。

## Slug

noshi-p0-improvements

## Type

feature（brownfield 改善）

## Upstream（入力）

- org-ai-kb/design-reviews/ux-product-review-001.md（改善の源泉）
- intent-001 inception 成果物（requirements/stories/wireframes/application-design）
- intent-002 construction 成果物（functional-design/nfr/infra）と実コード（backend/ frontend/）
