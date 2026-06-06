# NFR Design — Clarification（unit: noshi-service）

確定スタック（TSD-1..8）により設計パターンは概ね決定済み。genuine ambiguity は無く、推奨値を記録して進める（人間は plan/artifact ゲートで確認）。

### Q1: レジリエンス（外部ポート）
- 推奨: OcrLlmPort/GiftCatalogPort/IdP に **タイムアウト＋リトライ（指数バックオフ）＋サーキットブレーカ**。失敗時は手入力/候補なし/メールへフォールバック（NFR-R1）。
[Answer]: 推奨どおり（タイムアウト＋リトライ＋CB＋フォールバック）

### Q2: 非同期（抽出）
- 推奨: SQS standard ＋ **DLQ**、可視性タイムアウト、冪等キー=jobId、ExtractionJob.candidates は TTL（NFR-R2/D2）。
[Answer]: 推奨どおり（SQS+DLQ、冪等、TTL）

### Q3: 性能
- 推奨: 一覧/サマリの **読み取り最適化**（DynamoDB GSI・必要に応じ事前集計）、画像は S3 直アップロード（署名付きURL）、フロントはコード分割（NFR-P1/P3）。
[Answer]: 推奨どおり

### Q4: セキュリティ
- 推奨: 暗号化（KMS at rest / TLS in transit）、本人スコープを **PK に内包**＋BFF 二重チェック（A01）、認証レート制限・トークン失効（A07）、入力検証（pydantic/エッジ・画像）、監査ログ（A09）。restricted 平文禁止・外部送信最小化。
[Answer]: 推奨どおり

### Q5: 可観測性
- 推奨: 構造化ログ＋相関ID、メトリクス（レイテンシ/エラー/DLQ/認可失敗）、アラート閾値（NFR-O*）。
[Answer]: 推奨どおり
