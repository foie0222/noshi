# Intent Prompt (verbatim)

UX/プロダクト設計レビュー（org-ai-kb/design-reviews/ux-product-review-001.md）の P1 一式を AI-DLC で改善実装したい。
- P1-1: 弔事と慶事でトーンを変える（香典等の弔事文脈で配色・コピーを静かに切替）
- P1-2: 信頼を“見える化”（氏名入力時に「あなただけが見られます」＋鍵モチーフ）
- P1-3: 贈与税110万円枠の不安をすくう（暦年でもらった合計を集計し、枠への接近を知らせる・税アドバイスではなく気づき）
既存 noshi 実装（backend FastAPI + frontend React/TS）を入力とする brownfield 改善。TDD（pytest/vitest、日本語の検証説明）。
