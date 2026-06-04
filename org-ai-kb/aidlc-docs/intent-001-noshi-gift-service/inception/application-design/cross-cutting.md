# Cross-Cutting Standards — noshi

すべての将来ユニットが継承するシステム標準。論理レベル（実装非依存）。OWASP lens 反映。

## エラー形式
- 論理エラーは `{ code, message, retriable }` の形。
- 外部アクター（クライアント）向けメッセージは**汎用文言**で、スタックトレース・内部パス・スキーマ・資格情報を含めない（OWASP A03/誤情報漏えい防止）。
- 代表コード: `UNAUTHENTICATED`, `FORBIDDEN`(他者リソース), `VALIDATION_FAILED`, `RATE_LIMITED`, `EXTRACTION_FAILED`, `NOT_FOUND`, `CONFLICT`, `INTERNAL`（詳細は内部ログのみ）。

## 認可モデル（OWASP A01）
- ロール: MVP は単一ロール `owner`（本人）。将来 `family-member` 等を追加可能な設計。
- ポリシー: **本人スコープ強制**。すべてのリソースアクセスは `resource.ownerId == session.userId` を満たすこと。満たさなければ `FORBIDDEN` を返し AuditLog に記録。
- 認可の判定点は BFF（最前線）＋各コンポーネント（多層防御 / defense in depth）。

## ログ分類（OWASP A09）
- 種別: `auth`（ログイン成否・レート制限）, `authz`（認可失敗）, `data`（作成/更新/削除/エクスポート）, `extraction`（ジョブ状態）, `system`（内部エラー）。
- 重大度: `info` / `warn` / `error`。
- セキュリティイベント（auth/authz/data の削除・エクスポート）は AuditLog に追記。**restricted データを平文で記録しない**（識別子・ハッシュ・マスクで参照）。

## 入力検証の位置
- **エッジ（BFF）で第一次検証**: 形式・型・サイズ（画像）・必須・許容値。トラスト境界での reject-by-default。
- **サービス/コンポーネントで業務検証**: 事前条件（金額>0、ステータス遷移の妥当性、本人所有）。
- 外部ポート（OCR/LLM/カタログ）への送信前に**最小化・必要時マスキング**（restricted の不要送信を禁止）。

## データ分類（基準）
- restricted: 認証資格情報、（将来）決済情報。
- confidential: 相手の氏名・住所・続柄・贈答金額（第三者PII）。
- internal: 集計値・ステータス・ジョブ状態。
- public: なし（本サービスは公開データを持たない）。
- 分類に応じて 暗号化（at rest/in transit）・アクセス制御・監査の要否を決める（詳細は data-models.md）。

## トラスト境界
- 外部利用者 → BFF（常に untrusted。入力検証・認証・認可）。
- BFF → 内部コンポーネント（trusted-but-verified。本人スコープを伝播）。
- コンポーネント → 外部ポート（OCR/LLM/カタログ。untrusted。送信最小化・失敗フォールバック）。
