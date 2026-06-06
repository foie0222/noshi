# Intent Prompt (verbatim)

UX/プロダクト設計レビュー（org-ai-kb/design-reviews/ux-product-review-001.md）の P0 一式を AI-DLC で改善実装したい。内訳:
- P0-1: お返し期限ダッシュボード（ホームを「のこり◯日」順に、用途別の標準期限・残日数・緊急度表示）
- P0-2: 撮影レビューの「要所だけ確認」体験（高信頼は確定済み表示、低信頼のみ強調）
- P0-3: 収支フレーミング見直し（差分を前面から外し「お返しが必要/完了」へ）
- 負債#1: 「あげた(given)」を未完了お返し一覧から除外

既存の noshi 実装（backend FastAPI + frontend React/TS、intent-001/002 の成果物）を入力とする brownfield 改善。TDD（pytest/vitest、日本語の検証説明）。
