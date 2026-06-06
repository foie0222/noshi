# Logical Components (NFR Design) — noshi-service

NFR 設計が導入する**論理**インフラコンポーネント（ベンダー非依存。具体サービス割当は infrastructure-design）。
各々: 責務 / 満たす NFR / 配置 / 関連パターン / **失敗モード**。

## LC-1 JobQueue（+ DeadLetterQueue）
- 責務: 抽出ジョブのバッファ・配信・リトライ・失敗隔離（DLQ）。
- 満たす NFR: NFR-R2, NFR-S2, NFR-P2。
- 配置: 境界(BFF)→enqueue、抽出ワーカーが consume。
- パターン: P-ASY-1/2/3。
- 失敗モード: キュー不可用→enqueue 失敗を呼び出し元に伝え、ユーザーには「あとで再試行」を提示（データ未喪失）。配信失敗が閾値超で DLQ、監視アラート。

## LC-2 ObjectStore
- 責務: 撮影画像の保管・署名付きURL発行・暗号化。
- 満たす NFR: NFR-SE2, NFR-P2, NFR-A2。
- 配置: フロント→直アップロード、Extraction が参照。
- パターン: P-PERF-2, P-SEC-1, P-AVL-1。
- 失敗モード: 取得不可→抽出を ExtractionFailed とし手入力 fallback。アップロード失敗→ユーザーに再試行提示。

## LC-3 ResiliencePolicy（Timeout/Retry/CircuitBreaker/Fallback）
- 責務: 外部ポート呼び出しの耐障害制御（順序は P-RES の定義に従う）。
- 満たす NFR: NFR-R1, NFR-A3。
- 配置: OcrLlmPort/GiftCatalogPort/IdP アダプタ内。
- パターン: P-RES-1/2/3（外側から Fallback▷CB▷Retry▷Timeout）。
- 失敗モード: 依存先全滅→Breaker 開放で即フォールバック。フォールバックも不可なら汎用エラー（内部情報秘匿）＋監査。

## LC-4 TokenManager
- 責務: セッション/トークンの発行・検証・失効・有効期限、認証レート制限。
- 満たす NFR: NFR-SE4。
- 配置: Identity / 境界(BFF)。
- パターン: P-SEC-3。
- 失敗モード: IdP 不可用→メールログインへフォールバック。トークン検証失敗→UNAUTHENTICATED（汎用）＋監査。

## LC-5 AuditSink
- 責務: セキュリティイベントの追記記録（改ざん不可前提）。
- 満たす NFR: NFR-SE6, NFR-O。
- 配置: 各コンポーネントから非同期記録。
- パターン: P-SEC-5。
- 失敗モード: 記録先一時不可→バッファ/再試行で欠落を防ぐ。永続的不可は重大アラート（監査は可用性要件）。

## LC-6 Observability（Logger/Metrics/Tracer）
- 責務: 構造化ログ・メトリクス・トレース・アラート。
- 満たす NFR: NFR-O1/O2/O3。
- 配置: 全コンポーネント横断。
- パターン: P-OBS-1/2。
- 失敗モード: テレメトリ送出失敗はビジネス処理をブロックしない（ベストエフォート、ローカルバッファ）。

## LC-7 KeyManagement
- 責務: at rest 暗号鍵の管理・ローテーション。
- 満たす NFR: NFR-SE2。
- 配置: データストア/オブジェクトストアの暗号化設定。
- パターン: P-SEC-1。
- 失敗モード: 鍵アクセス不可→該当データの読み書きを fail-secure で拒否（復号不可時にデータを露出しない）。
