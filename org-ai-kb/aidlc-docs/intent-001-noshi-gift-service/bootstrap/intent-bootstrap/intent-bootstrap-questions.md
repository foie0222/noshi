# Intent Bootstrap — Clarification Questions (auto-answered)

`human-clarification: false` のため、builder が推奨回答を自動記入し、人間には提示していない。トレーサビリティ用に記録する。

### Q1: org-ai-kb の配置場所は？

a) `<workspace-root>/org-ai-kb/`（= `/home/inoue-d/dev/noshi/org-ai-kb/`）
b) その他のパス

**Recommendation:** a) デフォルトの workspace 直下。

[Answer]: a) `/home/inoue-d/dev/noshi/org-ai-kb/`

### Q2: intent slug は？

a) `noshi-gift-service`
b) `noshi`
c) その他

**Trade Offs:** `noshi` は短いが汎用的すぎて intent 名として識別性が低い。`noshi-gift-service` はギフト/熨斗サービスであることが明確。

**Recommendation:** a) `noshi-gift-service`

[Answer]: a) noshi-gift-service

### Q3: 分類は greenfield / brownfield / mixed のどれか？

a) greenfield
b) brownfield
c) mixed

**Recommendation:** a) 対象リポジトリは空で既存コードが無いため greenfield。

[Answer]: a) greenfield

### Q4: intent type は？

a) prototype（新規プロダクトの構想〜構築）
b) feature
c) migration / refactor

**Recommendation:** a) ゼロからの新サービスのため prototype。

[Answer]: a) prototype
