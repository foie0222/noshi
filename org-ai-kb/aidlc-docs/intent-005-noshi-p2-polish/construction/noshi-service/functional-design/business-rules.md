# Business Rules — noshi P2 polish（intent-005, unit: noshi-service）

intent-002..004 の BR を保持。P2 の僅少な新規ルール（多くは UI、ロジックは季節判定のみ）。

## BR-5-SEASON 季節ナッジ判定（新規・P2-2）
- **Stories:** S5-3, S5-6
- **BR-5-SEASON-1 (soft):** 現在月から季節を判定する: お中元=6〜8月、お歳暮=11〜12月、年始=12〜1月。
- **BR-5-SEASON-2 (soft):** 重なり（12月）は **年始を優先**。該当なしは「なし」。
- **BR-5-SEASON-3 (hard):** 判定は確定的（月ベース・日本時間）。

## BR-5-A11Y / BR-5-MOTION / BR-5-COPY（UI規約・新規）
- **Stories:** S5-1, S5-2, S5-4, S5-5
- **BR-5-A11Y-1 (hard):** 文字サイズ（標準/大）切替を提供。主要要素に代替テキスト/aria。コントラスト AA（弔事トーン含む）。
- **BR-5-MOTION-1 (hard):** 完了アニメは prefers-reduced-motion を尊重（動きを抑制可）。
- **BR-5-COPY-1 (soft):** 開発者語を排しやさしい言い回し。

## 不変（intent-002..004）
- 本人スコープ(A01)・入力検証(A03)・監査(A09)・分類・お返し期限・given除外・弔事トーン・贈与税。
