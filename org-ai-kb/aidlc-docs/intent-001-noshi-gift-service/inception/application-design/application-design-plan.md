# Application Design — Plan

方針: 能力/ドメイン単位の論理コンポーネント / 抽出は非同期ジョブ＋イベント / BFF で集約 / 外部依存は内部ポート隔離。
inception フェーズ: 技術非依存（言語/FW/DB/ブローカーに踏み込まない）。OWASP lens（データ分類・トラスト境界・入力検証・エラー秘匿）。

## 論理コンポーネント（components.md）
- [x] Identity（認証・本人スコープ）
- [x] ConsentPrivacy（同意・第三者PII方針・削除）
- [x] GiftLedger（贈答レコードの台帳・集計）
- [x] Extraction（画像→項目抽出・非同期ジョブ・信頼度）
- [x] HalfReturnCalculator（半返し算出・ルール根拠）
- [x] GiftSuggestion（お返し品提案・外部カタログ参照）
- [x] LetterGenerator（礼状文面生成・LLM送信最小化）
- [x] GiftEvent（受領→検討中→完了 のイベント/ステータス）
- [x] AuditLog（セキュリティ関連操作の証跡）
- [x] BFF（画面向け集約・認可境界の集約）

## その他の always-on
- [x] component-methods.md — 各コンポーネントの論理メソッド（入出力・事前/事後条件）
- [x] component-dependencies.md — 依存マトリクス（sync/async/event）・循環の有無
- [x] services.md — 業務ワークフロー（記録・お返し・礼状・削除）と S-n 紐付け
- [x] cross-cutting.md — エラー形式 / 認可モデル（本人スコープ）/ ログ分類 / 入力検証の位置

## 条件付き成果物
- [x] data-models.md（永続化あり）— User, ConsentRecord, GiftRecord, Party(相手), GiftEvent, ExtractionJob, ReturnSuggestion, Letter, AuditEntry。データ分類（confidential/restricted）付き。
- [x] api-contracts.md（BFF が API 公開）— 論理 API 面（入出力・エラー・consumer）
- [x] event-catalog.md（イベント駆動）— ExtractionRequested / ExtractionCompleted / ExtractionFailed 等（producer/consumer/payload/配信・順序）
- [x] external-dependencies.md（外部連携）— OcrLlmPort（OCR/LLM）, GiftCatalogPort（外部カタログ）。失敗モード・restricted送信境界。

## OWASP 反映
- [x] 各データフロー/フィールドに分類、トラスト境界の検証/エンコード、外部入力面の入力検証、エラーの内部情報秘匿。
