# Business Logic Model — noshi-service（技術非依存）

## Unit scope

- **Unit:** `noshi-service`（単一ユニット。intent-001 で units-generation を collapse＝MVP 全機能が1ユニット）。
- **Stories owned:** S-1, S-2, S-3, S-4, S-5, S-6, S-7, S-8, S-9, S-10, S-11, S-12, S-13, S-14（全ストーリー）。
- **Owning components（application-design より）:** Identity, ConsentPrivacy, GiftLedger, Extraction, HalfReturnCalculator, GiftSuggestion, LetterGenerator, GiftEvent, AuditLog, BFF。
- 本ユニットのワークフローは以下のとおり。

---

アクター: **owner**（本人）。すべてのワークフローは Identity が解決した本人スコープ下でのみ実行され、他者リソースへのアクセスは FORBIDDEN＋監査（A01）。すべての外部入力はトラスト境界（BFF）で検証（A03）。

## WF-1 オンボーディング
- Happy: signUp/logIn → 初回のみ同意取得（ConsentRecord）→ ホーム。
- Exception: 認証失敗 → 汎用エラー、連続失敗でレート制限（A07）。同意拒否 → 利用不可。

## WF-2 撮影 → 抽出 → 確認 → 記録
- Happy: 画像投入（形式/サイズ検証）→ ExtractionJob(pending) → ExtractionCompleted（候補＋信頼度）→ **全項目をユーザー確認/修正** → GiftRecord 作成 → 受領 GiftEvent 生成。
- Exception:
  - 抽出失敗（ExtractionFailed）→ 汎用エラー → **手入力 fallback** → 同じ確認画面で確定。
  - 低信頼項目 → 「要確認」フラグ。未確認のままの確定は不可。
  - 金額≤0・必須欠落 → VALIDATION_FAILED。

## WF-3 お返し（半返し → 提案 → 礼状）
- Happy: 受領イベント → 半返し算出（BR-HR）→ 候補提案（GiftCatalogPort）→ 選択を event に紐付け → 礼状生成（LLM最小化）→ 編集保存 → イベントを done に。
- Exception: カタログ不可用 → 候補なしを提示しフロー継続（お返しは後回し可）。生成失敗 → 汎用エラー・再試行。

## WF-4 台帳の閲覧・集計
- Happy: 検索/フィルタ（相手/用途/期間）→ 本人所有レコードのみ → 相手別 もらった/あげた/差分。
- Exception: 結果0 → 空状態。

## WF-5 イベント状態管理
- Happy: status を received/considering/done 間で**自由に遷移**（owner 操作）。
- 不変条件: status==done のイベントは「未完了お返し一覧」に出さない。done でもユーザーは任意に considering へ戻せる。

## WF-6 プライバシー（削除・エクスポート）
- Happy: 削除要求 → 確認 → 本人の全データ削除（完了で参照不能）→ AuditLog。エクスポート → 本人データ束 → AuditLog。
- 破壊的操作は確認必須。

## 横断前提
- すべての書き込み/読み取りで `resource.ownerId == session.userId` を検証（A01）。違反は FORBIDDEN＋ SecurityEventRecorded。
- セキュリティイベント（認証・認可失敗・削除・エクスポート）は監査（A09）。restricted を平文で記録しない。
