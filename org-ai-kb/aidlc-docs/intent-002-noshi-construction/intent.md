# Intent — noshi construction

## Prompt

Using AI-DLC, noshi の construction を進めたい。functional-design → nfr-assessment → nfr-design → infrastructure-design → code-generation → build-and-test（技術選定＋実装）へ。intent-001 の inception 成果物（requirements / stories / wireframes / application-design）を入力とする。単一サービス（単一ユニット）として構築する。

## Summary

intent-001 で確定した noshi の inception 成果物（requirements.md / stories.md / personas.md / wireframes / application-design の論理設計）を入力に、construction フェーズを実行する。単一サービスのため 1 ユニット（`noshi-service`）に collapse し、functional-design → nfr-assessment（技術選定）→ nfr-design → infrastructure-design → code-generation を順に行い、実際に動く noshi の実装を生成する。build-and-test はビルド・テストの検証ステップ。

## Slug

noshi-construction

## Type

implementation（construction フェーズ。inception 成果物に基づく実装）

## Upstream（intent-001 inception 成果物）

- ../intent-001-noshi-gift-service/inception/requirements-analysis/requirements.md
- ../intent-001-noshi-gift-service/inception/user-stories/stories.md, personas.md
- ../intent-001-noshi-gift-service/inception/wireframes/{screen-data-map,screen-structure,wireframe-guidance}.md
- ../intent-001-noshi-gift-service/inception/application-design/{components,component-methods,component-dependencies,services,cross-cutting,data-models,api-contracts,event-catalog,external-dependencies}.md
