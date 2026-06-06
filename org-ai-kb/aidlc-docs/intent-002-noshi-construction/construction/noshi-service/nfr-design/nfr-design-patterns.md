# NFR Design Patterns — noshi-service

NFRカテゴリ別の採用パターン（**論理レベル・ベンダー非依存**。具体サービス割当は infrastructure-design）。
各パターンは満たす NFR-* / OWASP に紐付け、NFR から導いた**既定値**を付す。

## Resilience（→ NFR-R1, NFR-A3）
- **P-RES-1 Timeout + Retry（指数バックオフ＋ジッタ）:** 外部ポート（OcrLlmPort/GiftCatalogPort/IdP）。
  - 既定値: タイムアウト 3s（同期）/ 抽出は非同期で個別、最大試行 3、初回バックオフ 200ms×2^n、上限 2s。根拠: 同期 API p95<500ms（NFR-P3）を阻害しない範囲。
- **P-RES-2 Circuit Breaker:** 連続失敗で開放→即フォールバック、半開で回復確認。
  - 既定値: 失敗率 50%/直近20件で開放、開放 30s 後に半開。
- **P-RES-3 Fallback:** 抽出失敗→手入力、カタログ不可用→候補なし継続、IdP不可用→メールログイン。
- **パターン順序（Rule 5）:** 外側から **Fallback ▷ CircuitBreaker ▷ Retry ▷ Timeout**。各呼び出しは Timeout 付き→失敗で Retry→試行尽きるか Breaker 開放で Fallback。Breaker は Retry を含む単位で失敗を計数（リトライ中の一時失敗は1事象として扱う）。

## Async / Scalability（→ NFR-R2, NFR-S2, NFR-P2）
- **P-ASY-1 Queue + DLQ:** 抽出ジョブをキューイング、最大受信超過で DLQ 隔離。
  - 既定値: 可視性タイムアウト 60s（抽出 p95<10s の余裕）、最大受信 3 で DLQ。
- **P-ASY-2 Idempotency:** jobId を冪等キーに。重複配信でも一度だけ確定。
- **P-ASY-3 Worker Autoscale:** キュー深さでワーカースケール（しきい値: 滞留>100 でスケールアウト）。

## Performance（→ NFR-P1, NFR-P3）
- **P-PERF-1 Read-optimized access:** 二次インデックスで一覧/未完了を効率取得。重い集計は事前計算 or オンデマンド。
- **P-PERF-2 Direct upload:** 画像は **オブジェクトストアへ署名付きURLで直接アップロード**（API 負荷削減）。署名URLは短命（既定 5分）。
- **P-PERF-3 Frontend code-splitting:** 画面単位の遅延読込で初回表示 p95<2.5s。

## Security（→ NFR-SE*, OWASP）
- **P-SEC-1 Encryption:** at rest（鍵管理サービス）/ in transit（TLS1.2+）。restricted 平文保存・ログ禁止（A02）。
- **P-SEC-2 Owner-scope enforcement:** パーティションキーに userId を内包＋境界（BFF）で二重チェック（多層防御, A01）。
- **P-SEC-3 AuthN hardening:** 外部 IdP（OIDC）、トークン失効・有効期限（既定: アクセス 15分/リフレッシュ 14日）、認証レート制限（既定: 5回/分でロック）（A07）。
- **P-SEC-4 Input validation:** スキーマ検証＋エッジ検証、画像形式/サイズ（既定: 上限 10MB、JPEG/PNG/HEIC）、外部送信前の最小化/マスキング（A03）。
- **P-SEC-5 Audit:** セキュリティイベントを追記ログ（A09）。
- **P-SEC-6 Fail-secure:** 認可判定失敗時は拒否（deny by default）。

## Availability / Reliability（→ NFR-A, NFR-R3）
- **P-AVL-1 Point-in-time recovery / Versioning:** データストアの PITR、オブジェクトのバージョニングで RPO（既定 RPO≤24h）。
- **P-AVL-2 DLQ monitoring + error budget:** 抽出失敗率<5% をアラート。

## Observability（→ NFR-O*）
- **P-OBS-1 Structured logs + correlation id:** 分類（auth/authz/data/extraction/system）、相関ID で追跡。
- **P-OBS-2 Metrics + alerts:** レイテンシ/エラー率/キュー滞留/認可失敗数、p95 逸脱アラート。
