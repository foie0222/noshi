# Workflow Composition — Clarification（intent-003 brownfield 改善）

P0 一式の改善。既存設計・コード・stack を再利用するため lean に構成。単一ユニット noshi-service。

### Q1: 実行ステージ
a) requirements-analysis → user-stories → functional-design(--unit) → code-generation(--unit)
b) フルパイプライン（reverse-engineering/wireframes/nfr/infra も）

**注記:** build-and-test は v2 未実装のため除外（code-generation 後に実機 build/test）。

**Recommendation:** a) lean。reverse-engineering は不要（設計docs+コードあり）、wireframes は既存画面の改修（design-review がUX仕様）、nfr/infra は stack 不変のため再利用。

[Answer]: a) lean（requirements → user-stories → functional-design → code-generation）

### Q2: ユニット
[Answer]: 単一ユニット noshi-service（intent-002 と同一を改修）

### Q3: OWASP lens
[Answer]: 有効化（引き続き PII を扱うため）
