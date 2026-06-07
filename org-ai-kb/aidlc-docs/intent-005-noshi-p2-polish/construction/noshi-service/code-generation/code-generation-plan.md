# Code Generation — Plan（intent-005 / TDD・磨き込み）
## frontend
- [x] lib/season.ts: seasonOf(month)/seasonNudge(season)（年始優先）＋vitest
- [x] App.tsx: ナビ中央FAB（撮影タブ廃止→ホーム/台帳/マイページ＋中央FAB）
- [x] App.tsx: お返し完了で水引モーション（reduced-motion尊重）
- [x] App.tsx: ホーム空状態/オンボ「まず1枚、撮ってみましょう」、季節ナッジ控えめ
- [x] App.tsx: 文字サイズトグル（標準/大、localStorage）、aria-label、コピー改善
- [x] components/SummaryBar.tsx + test 削除（未使用整理）
- [x] styles.css: fab / mizuhiki anim / textsize / nudge
## 検証
- [x] frontend vitest 全緑・tsc・build。backend pytest 緑維持。視覚スクショ。
