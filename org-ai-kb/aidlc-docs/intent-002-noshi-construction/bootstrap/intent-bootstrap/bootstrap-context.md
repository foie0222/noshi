# Bootstrap Context — noshi-construction

## Classification

**greenfield**

Rationale: 実装コードはまだ存在しない（intent-001 は inception ドキュメントのみを生成）。新規にコードをゼロから構築するため greenfield。inception 成果物が設計入力として存在する。

## Repos in scope

none（新規コードを本リポジトリ `noshi` に構築する。取り込み対象の既存リポジトリはなし）

## RE-kb status

n/a（既存システムが無いため reverse-engineering 知識ベースは不要。設計は intent-001 の application-design を直接参照）

## Reverse-engineering

not needed（既存コードが無いため reverse-engineering ステージはスキップ）

## Construction unit

単一サービスのため、construction は 1 ユニット `noshi-service` に collapse する（intent-001 で units-generation はスキップ済み）。
