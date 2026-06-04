# External Dependencies — noshi

外部システムは内部ポート（抽象インターフェース）の背後に隔離する。ベンダー非依存・失敗フォールバック・restricted 送信境界を明確化（OWASP）。

## OcrLlmPort
- **Name:** OCR/LLM ポート（画像抽出・文面生成）
- **Purpose:** 画像からの項目抽出（Extraction）と礼状文面生成（LetterGenerator）。
- **Contract:** 抽出 = { imageRef[] } → { fields, confidence }（論理）。生成 = { purpose, relationship, tone } → { text }。送信は**最小化**（不要な氏名/住所等の restricted を含めない・必要時マスキング）。
- **Failure mode:** タイムアウト/不可用 → ExtractionFailed を発行し**手入力 fallback**へ（S-3）。生成失敗 → ユーザーに汎用エラー、再試行可。外部障害を内部詳細としてクライアントに漏らさない。
- **Consumers:** Extraction, LetterGenerator
- **Trust:** untrusted（外部送信境界）。送信データは confidential 最小、restricted は送らない。

## GiftCatalogPort
- **Name:** ギフトカタログ ポート（お返し品候補）
- **Purpose:** 予算・用途に合うお返し品候補と外部参照リンクの取得（GiftSuggestion）。
- **Contract:** { budgetBand, relationship, purpose } → { items[]{title, summary, externalRef, priceBand} }。
- **Failure mode:** 不可用 → 候補なしを丁寧に提示（フローは継続、お返し選択を後回し可）。
- **Consumers:** GiftSuggestion
- **Trust:** untrusted。送信は非PIIの条件（予算/用途/関係）に限定。

## IdentityProviderPort（任意）
- **Name:** 外部 IdP（OAuth2/OIDC）
- **Purpose:** ソーシャルログイン（Identity）。
- **Contract:** 標準 OIDC トークン交換（詳細は construction）。
- **Failure mode:** 不可用 → メールログインにフォールバック。失敗は汎用認証エラー。
- **Consumers:** Identity
- **Trust:** untrusted（トークン検証必須）。

## 備考
- 具体的なベンダー・SDK・エンドポイントは construction（nfr-assessment/infrastructure-design）で決定。
- いずれのポートも「外部送信前の最小化・マスキング」「失敗時フォールバック」「クライアントへの内部情報秘匿」を満たすこと。
