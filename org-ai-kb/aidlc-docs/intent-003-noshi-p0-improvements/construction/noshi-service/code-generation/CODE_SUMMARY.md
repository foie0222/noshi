# CODE_SUMMARY — noshi P0 improvements（intent-003 code-generation）

既存 noshi 実装を TDD で改修（pytest/vitest、日本語の検証説明）。stack 不変。

## backend 変更
- domain/rules.py: `due_date(occurred_at, purpose)`（香典+49日/他+30日/中元歳暮=None）、`days_left(due, today)` 追加。
- domain/entities.py: ExtractionJob に `field_confidence` 追加。
- ports.py: OcrLlmMock に項目別 `field_confidence`（氏名だけ低信頼）。
- services.py: create_record は **received のみ**イベント生成（given除外）。pending_views に due_at/days_left、期限なし除外、**残日数昇順**ソート。`field_review` 追加。
- main.py: /api/home から**収支差分を撤去**、pending を期限つき・昇順で返す。/api/capture が field_review を返す。

## frontend 変更
- lib/format.ts: `daysLeftLabel(days)`（のこり◯日/きょうが期限/期限超過）。
- App.tsx home: SummaryBar 撤去 → **お返し期限ダッシュボード**（残日数バッジ・期限超過は朱・昇順）。
- App.tsx review: **要所だけ確認**（高信頼=✓確定、低信頼のみ要確認バッジ＋warn枠、「◯か所だけ確認」）。
- styles.css: between/duebadge/warn/reviewbadge/okbadge。

## 検証（実行済み）
- backend `pytest` → **43 passed**（+9: due_date/days_left/given除外/期限ビュー/昇順/per-field信頼度）。
- frontend `vitest` → **10 passed**（+4: daysLeftLabel）、`tsc` 0 errors、`vite build` 成功。
- ローカル実HTTP: home が期限順・given/中元除外・summary無し、capture が field_review（氏名のみ要確認）。

## 設計対応
- FR-3-1→due_date/days_left/pending_views, FR-3-2→home差分撤去+ダッシュボード, FR-3-3→field_review+review UI, FR-3-4→received限定イベント。
- BR-3-DUE/GIVEN/CONF を実装。OWASP（本人スコープ/入力検証/監査/分類）不変。

## 既知の負債（次段階）
- SummaryBar コンポーネントは未使用化（収支撤去のため）。次intentで削除候補。
