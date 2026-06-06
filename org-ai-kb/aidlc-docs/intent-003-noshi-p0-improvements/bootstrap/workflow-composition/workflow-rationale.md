# Workflow Rationale — noshi-p0-improvements (lean brownfield)

- requirements-analysis（含む）— P0 改善の要件を design-review から構造化。
- user-stories（含む）— UX 変更（期限ダッシュボード・撮影体験）をストーリー化。abuse/security は既存維持。
- functional-design --unit noshi-service（含む）— 期限ルール・given除外・確認体験の業務ロジック差分。
- code-generation --unit noshi-service（含む）— 既存 backend/frontend を TDD で改修。

スキップ:
- reverse-engineering — 自作の最新コード＋intent-001/002 設計docs があるため不要。
- wireframes — 既存画面の改修。design-review がUX仕様を提供。必要なら code-generation 内で対応。
- nfr-assessment / nfr-design / infrastructure-design — 技術スタック・インフラ不変（intent-002 を再利用）。
- build-and-test — v2 未実装。code-generation 後に実機 build/test。

Lens: owasp 有効（PII 継続）。
