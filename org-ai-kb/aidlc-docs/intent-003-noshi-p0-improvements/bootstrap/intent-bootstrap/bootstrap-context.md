# Bootstrap Context — noshi-p0-improvements

## Classification

**brownfield**

Rationale: 既存の noshi 実装（backend/ frontend/）が存在し、それを改修する。intent-001/002 の設計ドキュメントと実コードが揃っている。

## Repos in scope

noshi（本リポジトリ）— 既存の backend/ frontend/ を改修。

## RE-kb status

無し。ただし intent-001/002 の設計ドキュメント（requirements/application-design/functional-design 等）と実コードが存在するため、brownfield context はそこから直接取得できる。

## Reverse-engineering

not needed（自分たちで設計・実装した最新コードと設計docsが入力として使えるため、reverse-engineering ステージは不要）。

## Construction unit

単一サービス `noshi-service`（intent-002 と同一ユニットを改修）。
