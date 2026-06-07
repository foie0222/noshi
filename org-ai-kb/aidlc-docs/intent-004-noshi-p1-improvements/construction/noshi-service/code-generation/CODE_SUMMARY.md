# CODE_SUMMARY — noshi P1 improvements（intent-004 code-generation）

既存 noshi を TDD で改修（pytest/vitest、日本語の検証説明）。stack 不変。

## backend
- domain/rules.py: `tone(purpose)`（弔事キーワード→mourning/celebration）、`gift_tax_summary(records, year)`（received・香典/中元/歳暮除外・暦年・110万枠 total/remaining/over）、`GIFT_TAX_EXEMPTION`。
- services.py: `gift_tax(user_id, year?)`（本人データのみ）。
- main.py: `GET /api/gift-tax`。

## frontend
- lib/tone.ts: `toneOf(purpose)`。
- api.ts: `giftTax()`。
- App.tsx: マイページ追加（贈与税サマリ＋免責、プライバシー安心文）、tabbar に「マイページ」、review に TrustNote🔒、event 詳細の弔事トーン（朱→墨・タイトル/コピー控えめ・香典返し表現）。
- styles.css: trustnote / disclaimer / mournnote / mourning。

## 検証（実行済み）
- backend `pytest` → **49 passed**（+7: tone/gift_tax×4/api）。
- frontend `vitest` → **12 passed**（+2: toneOf）、`tsc` 0、`vite build` 成功。
- 実HTTP: gift-tax が香典除外で対象合計100万・あと10万、本人スコープ集計。

## 設計対応
- FR-4-1→tone/弔事UI、FR-4-2→TrustNote/マイページ、FR-4-3→gift_tax_summary/api/マイページ＋免責。BR-4-TONE/TAX/TRUST 実装。OWASP（本人スコープ・監査・分類）不変、信頼は表示のみ。
