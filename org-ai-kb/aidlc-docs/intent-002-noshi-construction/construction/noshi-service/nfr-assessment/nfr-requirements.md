# NFR Requirements — noshi-service

## Unit scope
- Unit: `noshi-service`（単一ユニット・MVP 全機能）。
- Owning components: Identity, ConsentPrivacy, GiftLedger, Extraction, HalfReturnCalculator, GiftSuggestion, LetterGenerator, GiftEvent, AuditLog, BFF。
- 機能複雑度: 中（生成AI/OCR の非同期処理を含むが単一ユーザー・単一データ境界）。

## Performance（→ NFR-1）
- NFR-P1: 主要画面（home/ledger/event）初回表示 p95 < 2.5s（モバイル回線）。参照: WF-4。
- NFR-P2: 抽出ジョブ（submit→結果/進捗）p95 < 10s。参照: WF-2。
- NFR-P3: 同期 API（半返し算出・台帳検索）p95 < 500ms。

## Scalability
- NFR-S1: 消費者向け・バースト負荷（季節: 年末年始/お中元）。サーバレス/オートスケールで吸収。
- NFR-S2: 抽出は SQS でバッファし、ワーカー水平スケール。ピークでもキュー滞留で平滑化。
- NFR-S3: DynamoDB はオンデマンドキャパシティ（MVP）でスパイク対応。

## Availability（→ NFR-3）
- NFR-A1: 月間 99%（MVP・単一リージョン）。
- NFR-A2: RTO ≤ 4h、RPO ≤ 24h（DynamoDB PITR・S3 バージョニング）。
- NFR-A3: 抽出は非同期のため一時障害でもジョブ滞留で継続（即時性より完了性を優先）。

## Security（→ NFR-2 / OWASP）
- NFR-SE1: データ分類: restricted（authIdentifier/secretHash）、confidential（氏名/関係/金額/住所/用途/礼状本文）、internal（集計/状態/ジョブ）。
- NFR-SE2: 暗号化 at rest（DynamoDB/S3 KMS）・in transit（TLS1.2+）。
- NFR-SE3: 本人スコープ強制（A01）— 全アクセスで ownerId==userId。SQS/S3 も userId スコープのキー設計。
- NFR-SE4: 認証（A07）— OIDC + メール、トークン失効、認証レート制限。
- NFR-SE5: 入力検証（A03）— BFF エッジ＋画像形式/サイズ。外部送信前の最小化（礼状/カタログ）。
- NFR-SE6: 監査（A09）— 認証/認可失敗/削除/エクスポートを AuditLog。restricted 平文禁止。
- NFR-SE7: コンプライアンス: 個人情報保護法（APPI）。第三者PIIの同意・削除権。

## Reliability
- NFR-R1: 外部ポート（OcrLlmPort/GiftCatalogPort/IdP）障害時のフォールバック（手入力/候補なし/メールログイン）。
- NFR-R2: SQS リトライ＋ DLQ（抽出失敗の隔離）。冪等性は jobId。
- NFR-R3: エラーバジェット: 抽出失敗率 < 5%（DLQ 監視）。

## Observability
- NFR-O1: メトリクス: API レイテンシ/エラー率、抽出ジョブ滞留・失敗率、認可失敗数。
- NFR-O2: 構造化ログ（cross-cutting の分類 auth/authz/data/extraction/system）＋トレース（リクエスト相関ID）。
- NFR-O3: アラート: DLQ 増加、認可失敗スパイク、p95 逸脱。

## Usability / Accessibility（→ NFR-4）
- NFR-U1: モバイルファースト・レスポンシブ（基準 375px、≥768 は中央カラム）。主要操作は片手・3タップ以内。
- NFR-U2: WCAG 2.1 AA — コントラスト 4.5:1 以上、フォーム項目にラベル、フォーカス可視、画像/アイコンに代替テキスト、エラーは色＋テキスト併記。
- NFR-U3: 日本語 UI（単一言語）。PWA 視野（オフライン閲覧は将来）。
- 実現: TSD-2（React+TS、コード分割で初回表示）。

## Data
- NFR-D1: 規模目安: ユーザー数千〜、1ユーザーあたり贈答レコード〜数百。DynamoDB に十分。
- NFR-D2: 保持: 記録はユーザー削除まで。ExtractionJob の中間 candidates は確定後 TTL で破棄。AuditEntry は保持期間ポリシー。
- NFR-D3: リージョン: 日本（ap-northeast-1）。データ residency を国内に。

## NFR traceability
- NFR-P* → NFR-1 / NFR-S*,A* → NFR-3 / NFR-SE* → NFR-2,NFR-5 / NFR-O* → NFR-2.6 / **NFR-U* → NFR-4** / NFR-D* → NFR-5。
