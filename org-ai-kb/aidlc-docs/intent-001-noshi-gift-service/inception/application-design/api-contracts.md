# API Contracts — noshi（論理 API 面 / BFF 公開）

BFF が画面向けに公開する論理 API。入出力は論理型。エラーは cross-cutting のコードに従う。
全 API は認証必須・本人スコープ強制（特記なき限り）。Consumer は noshi モバイル Web クライアント。

## auth.login
- **Purpose:** ログイン。
- **Inputs:** { idpToken } または { email, secret }
- **Outputs:** { session }
- **Errors:** VALIDATION_FAILED, RATE_LIMITED, UNAUTHENTICATED（汎用文言）
- **Consumers:** login 画面（未認証可）

## consent.accept
- **Purpose:** 同意の記録。
- **Inputs:** { purposeVersion }
- **Outputs:** { ok }
- **Errors:** UNAUTHENTICATED, VALIDATION_FAILED
- **Consumers:** consent 画面

## home.get
- **Purpose:** ホーム集約（サマリ＋未完了お返し＋直近）。
- **Inputs:** { } （session から本人解決）
- **Outputs:** { summary{received,given,diff}, pendingReturns[], recent[] }
- **Errors:** UNAUTHENTICATED
- **Consumers:** home 画面

## capture.submit
- **Purpose:** 抽出ジョブの投入。
- **Inputs:** { images[] }（形式/サイズ検証）
- **Outputs:** { jobId, status }
- **Errors:** VALIDATION_FAILED, UNAUTHENTICATED
- **Consumers:** capture 画面

## capture.jobStatus
- **Purpose:** 抽出ジョブの状態取得。
- **Inputs:** { jobId }
- **Outputs:** { status, candidates?, confidence? }
- **Errors:** FORBIDDEN(他者ジョブ), NOT_FOUND, EXTRACTION_FAILED
- **Consumers:** loading / extract-review

## ledger.createRecord
- **Purpose:** 確認後の記録確定。
- **Inputs:** { party{name,relationship}, amount, purpose, occurredAt, direction, memo? }
- **Outputs:** { record, event }
- **Errors:** VALIDATION_FAILED, UNAUTHENTICATED
- **Consumers:** extract-review / extract-error

## ledger.search
- **Purpose:** 台帳の検索・集計。
- **Inputs:** { query?, party?, purpose?, period? }
- **Outputs:** { records[], partySummaries[] }
- **Errors:** UNAUTHENTICATED
- **Consumers:** ledger 画面

## returns.halfReturn
- **Purpose:** 半返し算出。
- **Inputs:** { amount, purpose }
- **Outputs:** { range, rationale[] }
- **Errors:** VALIDATION_FAILED
- **Consumers:** half-return 画面

## returns.suggest
- **Purpose:** お返し候補。
- **Inputs:** { budgetBand, relationship, purpose }
- **Outputs:** { suggestions[] }
- **Errors:** VALIDATION_FAILED
- **Consumers:** gift-suggest 画面

## returns.letter
- **Purpose:** 礼状生成。
- **Inputs:** { purpose, relationship, tone }（最小化）
- **Outputs:** { draftText }
- **Errors:** VALIDATION_FAILED
- **Consumers:** letter 画面

## event.setStatus / event.get
- **Purpose:** イベントの取得・ステータス更新。
- **Inputs:** { eventId, status? }
- **Outputs:** { event }
- **Errors:** FORBIDDEN(他者), NOT_FOUND, CONFLICT(不正遷移)
- **Consumers:** event-detail 画面

## privacy.delete / privacy.export
- **Purpose:** アカウント/全データ削除・エクスポート。
- **Inputs:** { confirm }
- **Outputs:** { ticket }
- **Errors:** UNAUTHENTICATED
- **Consumers:** settings 画面（破壊的＝確認必須・監査記録）
