# Workflow Composition — Clarification Questions

Intent: noshi-gift-service（greenfield / 新規ギフト・熨斗サービス / prototype）

明確化が必要な点のみを質問する（合成ルール §1 の right-sizing を適用）。
requirements-analysis / code-generation / build-and-test は always-on。

### Q1: 今回の intent をどこまで進めるか（パイプライン深度）

a) Inception まで（構想〜論理設計図。requirements → user-stories → wireframes → application-design）。コード生成は別 intent に回す。
b) 設計を最後まで（inception + NFR/インフラ設計）。実装直前まで固める。
c) コード生成まで一気通貫（フルパイプライン）。

**Trade Offs:** 「サービスを考えたい」という intent からは、まず構想と設計を固める (a) が自然。AI-DLC は後から intent を継ぎ足してコード生成へ進められる。(c) は手戻りリスクが大きい。

**Recommendation:** a) まず Inception で構想・設計を固める。

[Answer]: a) Inception（構想〜設計図）まで

### Q2: noshi の規模感（units-generation の要否）

a) 単一サービス（1ユニットに collapse、units-generation はスキップ）
b) 複数サービス（units-generation で複数ユニットに分割）
c) おまかせ（application-design の結果を見て判断）

**Trade Offs:** 構想初期は単一サービス前提で十分。複数サービス化は application-design 後に判断しても遅くない（合成ルール §5: 後から挿入可能）。

**Recommendation:** a) 単一サービス前提。

[Answer]: a) 単一サービス前提

### Q3: noshi は UI を持つか（wireframes ステージの要否）

a) UI あり（Web 画面。wireframes ステージを含める）
b) UI なし（API/バックエンドのみ。wireframes をスキップ）

**Trade Offs:** ギフト購入・熨斗選択は利用者向け画面が中核。wireframes は画面とデータの対応を早期に可視化でき、構想段階で価値が高い。

**Recommendation:** a) UI あり、wireframes 含む。

[Answer]: a) UI あり（wireframes 含む）

### Q4: OWASP セキュリティ lens を有効化するか（default-activation: true）

a) 有効化（推奨）
b) 無効化

**Trade Offs:** noshi は購入・個人情報（氏名・住所・贈り先）を扱う見込みで、インターネット公開の消費者向けサービス。OWASP lens は全ステージにセキュリティ観点を注入する。

**Recommendation:** a) 有効化。

[Answer]: a) 有効化

### Q5（OWASP tailoring・Q4で有効化時のみ）: セキュリティ前提

構想初期のため、暫定の推奨値で記録し requirements 以降で精緻化する。

- 扱うデータの機微度: **confidential 中心 + 一部 restricted**（氏名・住所・贈答先などの PII。決済を内製する場合は restricted）
- コンプライアンス: 暫定で **個人情報保護法（APPI）相当**。決済導入時は **PCI-DSS** を再評価
- 認証モデル: 暫定 **セッション/OAuth2（外部IdP）** を想定
- 公開範囲: **インターネット公開（消費者向け）**
- リスク許容度: **バランス型**（情報漏洩は重大視、過剰統制は避ける）

**Recommendation:** 上記の暫定値で lens-owasp-answers.md に記録し、requirements-analysis で確定。

[Answer]: 暫定の推奨値で記録し、requirements-analysis で確定する（承認済み）
