# CODE_SUMMARY — noshi otoshidama（intent-007 N2）

frontend のみ（静的・データ非依存）。TDD（vitest）。backend 変更なし。

## frontend
- lib/otoshidama.ts: `otoshidamaRange(age)`→{low,high,bracket,note}（未就学0-1000/低学年1000-3000/高学年3000-5000/中学5000/高校5000-10000/大学以上10000）。
- App.tsx: マイページ「お年玉の目安」（年齢入力→区分・相場レンジ・一言・地域差の注記）。

## 検証（実行済み）
- frontend `vitest` → **23 passed**（+7 otoshidama）、`tsc` 0、`vite build` 成功。
- backend `pytest` → 53（変更なし）。

## 設計対応
- FR-7-1→otoshidamaRange、FR-7-2/3→マイページお年玉ツール＋注記。BR-7-OTOSHIDAMA 実装。データ非依存のため本人スコープ/監査/分類に影響なし（OWASP 不変）。
