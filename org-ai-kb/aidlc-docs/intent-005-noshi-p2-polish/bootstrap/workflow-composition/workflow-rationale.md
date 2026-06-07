# Workflow Rationale — noshi-p2-polish (lean brownfield)
- requirements-analysis（含む）— P2 要件を design-review から構造化。
- user-stories（含む）— ナビ/モーション/オンボーディング/コピー/a11y のストーリー。
- functional-design --unit noshi-service（含む）— 季節ナッジ等の僅少ロジック差分（多くはUI）。
- code-generation --unit noshi-service（含む）— frontend 中心の磨き込み＋SummaryBar削除を TDD/ビルドで。
スキップ: reverse-engineering / wireframes / nfr-assessment / nfr-design / infrastructure-design（stack・設計不変、UIの磨き込み）。build-and-test（v2未実装、実機）。
Lens: owasp 有効。
