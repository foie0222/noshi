# NFR Design — Plan（unit: noshi-service）

確定スタック（TSD-1..8）と NFR 値に基づき、設計パターンと論理インフラコンポーネントを定義。

## nfr-design-patterns.md（NFRカテゴリ別）
- [x] Resilience: タイムアウト/リトライ(指数バックオフ)/サーキットブレーカ、ポート別フォールバック（NFR-R1）
- [x] Async/Scalability: SQS+DLQ・冪等(jobId)・可視性タイムアウト・水平スケール（NFR-R2/S2）
- [x] Performance: GSI 読み取り最適化・事前集計・S3 直アップロード・フロントコード分割（NFR-P*）
- [x] Security: KMS/TLS 暗号化・本人スコープ(PK内包)+BFF二重チェック・認証レート制限/失効・入力検証・監査（A01/02/03/07/09）
- [x] Availability/Reliability: PITR、DLQ 監視、エラーバジェット（NFR-A/R）
- [x] Observability: 構造化ログ+相関ID・メトリクス・アラート（NFR-O*）
- [x] 各パターンを NFR-* と OWASP に紐付け

## logical-components.md（NFR設計が導入する論理コンポーネント）
- [x] JobQueue（SQS 抽象）+ DeadLetterQueue
- [x] ObjectStore（S3 抽象・署名付きURL）
- [x] CircuitBreaker/RetryPolicy（外部ポート）
- [x] TokenManager（セッション/トークン失効・レート制限）
- [x] AuditSink（追記ログ）
- [x] Metrics/Tracing（可観測性）
- [x] 各コンポーネントの責務・満たす NFR・配置（BFF/ワーカー）
