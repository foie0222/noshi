# CODE_SUMMARY — noshi record given（intent-008 bugfix+feature）

## backend
- main.py: create_record の event を None 安全化（given は event=null で 200。500 TypeError を修正）。FR-8-1。

## frontend
- App.tsx: 記録確認画面に「種類」受領/贈与 トグル（draft.direction、aria）。FR-8-2。

## 検証（実行済み）
- backend `pytest` → **54 passed**（+1: given 200/event null、台帳に出るが pending 非表示）。
- frontend `vitest` 23 / `tsc` 0 / `vite build` 成功。

## 設計対応
- FR-8-1→create_record None 安全化、FR-8-2→方向トグル。BR-8-GIVEN-RECORD 実装。given除外・本人スコープ不変（OWASP）。
