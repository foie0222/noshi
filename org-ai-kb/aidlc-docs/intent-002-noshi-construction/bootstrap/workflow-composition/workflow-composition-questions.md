# Workflow Composition — Clarification Questions (construction)

Intent: noshi-construction（intent-001 inception を入力に実装）。単一サービス＝1ユニット `noshi-service`。

### Q1: 実行する construction ステージ

a) functional-design → nfr-assessment → nfr-design → infrastructure-design → code-generation（全5ステージ・per-unit）
b) 一部のみ（例: 設計を飛ばして code-generation 中心）

**注記:** build-and-test はこの AI-DLC v2 スナップショットに **未実装（SKILL.md 無し）**。ワークフローには含めず、code-generation 後に実ビルド/テストを実機で実施する（後述）。

**Recommendation:** a) 全5ステージ。nfr-assessment で技術選定 → 設計 → 実装の順で品質を担保。

[Answer]: a) 全5ステージ（per-unit）

### Q2: ユニット構成

a) 単一ユニット `noshi-service`（intent-001 で units-generation スキップ＝単一サービス）
b) 複数ユニットに分割

**Recommendation:** a) 単一ユニット。per-unit スキルは `--unit noshi-service` で1回ずつ実行。

[Answer]: a) 単一ユニット noshi-service

### Q3: OWASP セキュリティ lens

a) 有効化（code-generation まで全ステージにセキュリティ観点）
b) 無効化

**Recommendation:** a) 有効化。実装段階こそ A01/A03/A07 等の作り込みが重要。

[Answer]: a) 有効化

### Q4: build-and-test の扱い（未実装スキル）

a) ワークフローから除外し、code-generation 後に「実ビルド＋テスト実行」を手動ステージとして実施
b) 何もしない

**Recommendation:** a) 除外＋実機で build/test（生成コードが実際に動くか検証）。

[Answer]: a) build-and-test は除外し、code-generation 後に実機で build/test を実施
