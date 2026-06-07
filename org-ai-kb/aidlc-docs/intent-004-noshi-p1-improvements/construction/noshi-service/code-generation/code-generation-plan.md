# Code Generation — Plan（intent-004 / TDD 改修）

## backend
- [x] rules.py: tone(purpose)→"mourning"/"celebration"（弔事キーワード）＋テスト
- [x] rules.py: gift_tax_summary(records, year)→{total,remaining,over}（received・香典/中元/歳暮除外・暦年）＋テスト
- [x] main.py: GET /api/gift-tax（今年の対象合計・remaining・over）

## frontend
- [x] lib/tone.ts: toneOf(purpose)→"mourning"/"celebration"＋vitest
- [x] api.ts: giftTax()
- [x] App.tsx: 弔事トーン（弔事文脈の accent を墨/グレーに）、信頼表示（氏名入力・consent）、設定に贈与税サマリ＋免責
- [x] styles.css: mourning / trustnote / taxcard

## 検証
- [x] backend pytest 全緑 / frontend vitest 全緑・tsc・build
