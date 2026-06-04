# Components — noshi（論理コンポーネント）

技術非依存の論理コンポーネント。MVP は単一サービス内のモジュールとして実装しうるが、境界は将来のサービス分割に耐える形で定義する。

## Identity
- **Purpose:** 認証と本人スコープの確立。
- **Responsibilities:** サインアップ/ログイン、セッション/トークンの発行と失効、認証レート制限、リクエストの本人スコープ解決。
- **State:** stateful（資格情報・セッション）
- **Owns:** User, Session

## ConsentPrivacy
- **Purpose:** 利用同意と第三者PIIの取り扱い・削除権の管理。
- **Responsibilities:** 同意の記録、利用目的の提示、ユーザーおよびデータの削除要求の受理と完了、データエクスポート。
- **State:** stateful
- **Owns:** ConsentRecord

## GiftLedger
- **Purpose:** 贈答レコード（もらった/あげた）の台帳と集計。
- **Responsibilities:** レコードの作成/編集/削除、検索・フィルタ、相手別/用途別/期間別の集計、相手別差分。
- **State:** stateful
- **Owns:** GiftRecord, Party

## Extraction
- **Purpose:** 画像から贈答項目を抽出する非同期処理。
- **Responsibilities:** 抽出ジョブの受理・実行・状態管理、項目（金額/氏名/関係/用途/日付）と信頼度の算出、失敗時の通知（手入力 fallback を促す）。OCR/LLM は内部ポート経由。
- **State:** stateful（ジョブ）
- **Owns:** ExtractionJob

## HalfReturnCalculator
- **Purpose:** 半返し（推奨お返し額）の算出。
- **Responsibilities:** 金額・用途から推奨レンジを算出、適用ルールの根拠提示、上書きの保持。
- **State:** stateless
- **Owns:** （なし。ルール表は参照）

## GiftSuggestion
- **Purpose:** お返し品候補の提案（MVP は提案のみ）。
- **Responsibilities:** 予算・関係・用途から候補を生成、外部カタログ参照（内部ポート経由）、選択の記録。
- **State:** stateless（候補は都度生成）
- **Owns:** ReturnSuggestion

## LetterGenerator
- **Purpose:** 礼状文面の生成。
- **Responsibilities:** 相手・用途・トーンから文面生成（LLM ポート経由・送信データ最小化）、編集結果の保持。
- **State:** stateless
- **Owns:** Letter

## GiftEvent
- **Purpose:** 贈答イベントのライフサイクル管理。
- **Responsibilities:** 受領→検討中→完了 のステータス遷移、未完了の抽出、お返し（提案/礼状）の紐付け。
- **State:** stateful
- **Owns:** GiftEvent

## AuditLog
- **Purpose:** セキュリティ関連操作の証跡（OWASP A09）。
- **Responsibilities:** 認証試行・認可失敗・データ削除・エクスポート等の追記専用ログ。restricted データを平文で残さない。
- **State:** stateful（追記専用）
- **Owns:** AuditEntry

## BFF（Backend-for-Frontend）
- **Purpose:** 画面向けのデータ集約と認可境界の一元化。
- **Responsibilities:** home 等の複数コンポーネント集約、画面単位の API 提供、入力検証の最前線（トラスト境界）、本人スコープの強制委譲。
- **State:** stateless
- **Owns:** （なし。下流コンポーネントを集約）
