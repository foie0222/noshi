# Workflow Rationale — noshi-gift-service

Intent: greenfield / 新規ギフト・熨斗サービス / prototype。今回のスコープは **Inception まで**（人間判断 Q1）。
right-sizing 原則を適用。always-on の code-generation / build-and-test も含め、construction フェーズは今回 intent では実行せず、後続 intent に回す。

## Inception phase（実行する）

- **requirements-analysis（含む）** — always-on。noshi の提供価値・対象・スコープを確定する起点。
- **user-stories（含む）** — 消費者向けサービスで複数アクター・複数ユースケース（贈り主、受け取り手、用途別）が想定され、ストーリー化の価値が高い。OWASP により abuse case も併記。
- **wireframes（含む）** — UI あり（Q3）。ギフト購入・熨斗選択の画面とデータ対応を早期に可視化する。
- **application-design（含む）** — 論理コンポーネント構成・データモデル・トラスト境界を設計する。単一サービスでも構成の骨格として価値がある。

## スキップしたスキル

- **reverse-engineering（スキップ）** — greenfield、既存リポジトリ・統合対象なし。
- **units-generation（スキップ）** — 単一サービス前提（Q2）。1ユニットに collapse。複数サービス化が必要なら application-design 後に挿入可能（合成ルール §5）。
- **functional-design / nfr-assessment / nfr-design / infrastructure-design / code-generation / build-and-test（今回スキップ）** — スコープを Inception までとしたため（Q1）。構想・設計確定後、別 intent で construction を実行する。

## Lenses

- **owasp（有効化）** — 購入・PII を扱う消費者向け公開サービス。全 inception ステージにセキュリティ観点を注入。tailoring は暫定値を lens-owasp-answers.md に記録し requirements で確定。
