# Event Catalog — noshi

非同期イベント。MVP の非同期は「抽出」と「監査記録」。payload は論理型で、restricted データは識別子で参照し平文で運ばない（OWASP）。

## ExtractionRequested
- **Purpose:** 抽出ジョブの開始を通知。
- **Producer:** Extraction（submitJob）
- **Consumers:** Extraction の実行ワーカー（runExtraction）
- **Payload:** { jobId, userId, imageRef[] }（imageRef は参照、画像本体は安全なストレージ）
- **Delivery semantics:** at-least-once
- **Ordering:** none（jobId で冪等）

## ExtractionCompleted
- **Purpose:** 抽出成功と候補項目の提示。
- **Producer:** Extraction
- **Consumers:** BFF（capture.jobStatus が参照）, （ユーザー確認後）GiftLedger
- **Payload:** { jobId, userId, candidates(参照/最小), confidence }
- **Delivery semantics:** at-least-once
- **Ordering:** none

## ExtractionFailed
- **Purpose:** 抽出失敗の通知（手入力 fallback を促す）。
- **Producer:** Extraction
- **Consumers:** BFF（汎用エラー提示・内部理由はログのみ）
- **Payload:** { jobId, userId, reasonCode(internal) }
- **Delivery semantics:** at-least-once
- **Ordering:** none

## SecurityEventRecorded
- **Purpose:** 認証・認可失敗・データ削除/エクスポート等の監査記録。
- **Producer:** Identity / ConsentPrivacy / GiftLedger
- **Consumers:** AuditLog
- **Payload:** { actorId, action, targetRef(識別子), at, metadata(平文restricted禁止) }
- **Delivery semantics:** at-least-once
- **Ordering:** partitioned by actorId（同一アクターの順序保持）

## 備考
- 同期で十分なフロー（半返し・提案・礼状・台帳閲覧）はイベント化しない（過剰な非同期を避ける）。
- イベント基盤の具体（ブローカー等）は construction フェーズで決定。
