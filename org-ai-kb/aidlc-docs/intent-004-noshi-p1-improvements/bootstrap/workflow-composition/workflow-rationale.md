# Workflow Rationale — noshi-p1-improvements (lean brownfield)
- requirements-analysis（含む）— P1 要件を design-review から構造化。
- user-stories（含む）— トーン切替・信頼可視化・贈与税気づきのストーリー。
- functional-design --unit noshi-service（含む）— トーン分類・年間集計・110万枠判定の業務ロジック差分。
- code-generation --unit noshi-service（含む）— 既存 backend/frontend を TDD で改修。
スキップ: reverse-engineering（設計docs+コードあり）/ wireframes（既存画面改修、design-reviewがUX仕様）/ nfr-assessment・nfr-design・infrastructure-design（stack・インフラ不変）。build-and-test（v2未実装、実機build/test）。
Lens: owasp 有効（PII継続）。
