# Business Logic Model — noshi P2 polish（intent-005）
## Unit scope
- Unit: noshi-service。Stories owned: S5-1..6。Owning components: UI（ナビ/モーション/オンボ/a11y/コピー）/ 僅少 system（季節判定）。
## 変更WF（差分）
- ナビ: 撮影を中央FABに（UI）。
- 完了: 水引モーション（UI、reduced-motion尊重）。
- 季節ナッジ: season(month) を判定しホームに控えめ表示（BR-5-SEASON）。
- オンボ/空状態: 記録ゼロで撮影導線（UI）。a11y: 文字サイズ・代替テキスト（UI）。コピー改善。
## 不変
- ドメイン（期限/given/トーン/贈与税/本人スコープ）は intent-002..004 のまま。
