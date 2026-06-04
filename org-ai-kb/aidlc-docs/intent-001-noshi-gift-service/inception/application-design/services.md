# Services — noshi（業務ワークフロー）

コンポーネントを業務フローに編成するサービス層。各サービスは対応するストーリー S-n を満たす。

## OnboardingService
- **Purpose:** サインアップから同意までの導入。
- **Components used:** Identity, ConsentPrivacy, AuditLog
- **Operations:** signUp/logIn → 初回同意取得 → ホームへ。
- **Stories addressed:** S-1, S-14, S-12

## CaptureRecordService
- **Purpose:** 撮影→AI抽出→確認→台帳記録 の中核フロー。
- **Components used:** BFF, Extraction(OcrLlmPort), GiftLedger, GiftEvent, AuditLog
- **Operations:** 画像投入 → ExtractionJob → （完了/失敗）→ ユーザー確認/手入力 → GiftRecord 作成 → 受領 GiftEvent 生成。
- **Stories addressed:** S-3, S-9

## LedgerService
- **Purpose:** 台帳の閲覧・検索・集計。
- **Components used:** BFF, GiftLedger
- **Operations:** 検索/フィルタ、相手別/用途別集計、相手別差分。
- **Stories addressed:** S-4

## ReturnService
- **Purpose:** 半返し→お返し提案→礼状→完了 のお返しフロー。
- **Components used:** BFF, HalfReturnCalculator, GiftSuggestion(GiftCatalogPort), LetterGenerator(OcrLlmPort), GiftEvent
- **Operations:** 半返し算出 → 候補提案・選択 → 礼状生成・保存 → イベントを完了へ。
- **Stories addressed:** S-5, S-6, S-7, S-8

## PrivacyService
- **Purpose:** 同意管理・データ削除・エクスポート。
- **Components used:** ConsentPrivacy, Identity, GiftLedger, AuditLog
- **Operations:** 同意状況提示、アカウント/全データ削除、エクスポート（いずれも監査記録）。
- **Stories addressed:** S-2, S-14

## AccessControlService（横断）
- **Purpose:** 本人スコープの強制と認可（OWASP A01）。
- **Components used:** Identity, BFF, AuditLog
- **Operations:** 各リクエストで本人スコープ解決、他者リソース参照の拒否＋監査記録。
- **Stories addressed:** S-10, S-11, S-13
