# Workflow Rationale — noshi-construction

Intent: construction フェーズ（intent-001 inception を入力に実装）。単一サービス＝1ユニット `noshi-service`。

## 実行する construction ステージ（per-unit: noshi-service）

- **functional-design（含む）** — 技術非依存のドメイン/業務ロジック詳細（business-logic-model / domain-entities / business-rules）。
- **nfr-assessment（含む）** — 非機能要件の評価と **技術スタックの決定**（tech-stack-decisions）。construction の要の意思決定点。
- **nfr-design（含む）** — 性能/セキュリティ/可用性などの設計パターンと論理コンポーネントへの落とし込み。
- **infrastructure-design（含む）** — デプロイ構成・インフラ設計。
- **code-generation（含む）** — 実コードの生成。OWASP を作り込む。

## スキップ/対象外

- **reverse-engineering / requirements-analysis / user-stories / wireframes / application-design / units-generation** — intent-001（inception）で完了済み。本 intent では再実行しない（入力として参照）。
- **build-and-test（対象外）** — この AI-DLC v2 スナップショットに SKILL.md が無く未実装。ワークフローには含めず、code-generation 後に **実機でビルド＋テスト**を実施して動作検証する（人間判断 Q4）。

## Lenses

- **owasp（有効化）** — 実装段階のセキュリティ作り込み（本人スコープ強制 A01・入力検証 A03・認証 A07・監査 A09）。全 construction ステージに注入。
