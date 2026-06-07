# CODE_SUMMARY — noshi relationship balance（intent-006 N1）

既存 noshi を TDD で拡張。stack 不変。

## backend
- domain/rules.py: `relationship_balance(records, today)` — 相手別 received/given/diff/last_at、偏り分類（balanced/owe/ahead）、気になる関係（owe＋180日超）、attention優先・差分降順ソート。`RELATIONSHIP_ATTENTION_DAYS`。
- services.py: `relationships(user_id)`（本人データのみ）。
- main.py: `GET /api/relationships`。

## frontend
- api.ts: `relationships()`。
- App.tsx: マイページに「おつきあい」一覧（status バッジ owe/ahead/balanced、気になる関係を上位・やさしいコピー、もらった/あげた/最終やりとり）。
- styles.css: balbadge。

## 検証（実行済み）
- backend `pytest` → **53 passed**（+4: balance×3/api）。
- frontend `vitest` → 16、`tsc` 0、`vite build` 成功。
- 実HTTP/画面: いとこ=owe+attention、友人=balanced、姪=ahead を確認。

## 設計対応
- FR-6-1→relationship_balance/集計、FR-6-2→偏り分類/気になる関係、FR-6-3→マイページおつきあい一覧。BR-6-BALANCE 実装。OWASP（本人スコープ集計・監査・分類）不変。
