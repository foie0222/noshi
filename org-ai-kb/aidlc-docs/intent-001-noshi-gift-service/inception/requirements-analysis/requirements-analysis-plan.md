# Requirements Analysis — Plan

`requirements.md` を以下の構成で作成する。確定した明確化回答に基づく。
OWASP lens を適用（セキュリティ/プライバシー要件・機微データ分類を含める）。

## 作成する requirements.md の中身

- [x] **Intent summary** — type=prototype（新規）、scope=単一サービス、complexity、greenfield、affected repos=none、MVP対象=個人ソロ
- [x] **Functional requirements（FR-n、各 pass/fail 検証可能）** 中核ループを網羅:
  - [x] FR: アカウント/認証（本人のみ、最小権限）
  - [x] FR: ①撮影→記録（画像アップロード → OCR/AI抽出: 金額・氏名・関係・用途・日付 → 確認・修正 → 保存）
  - [x] FR: ②Give 履歴台帳（もらった/あげたの一覧・検索・相手別/用途別の集計）
  - [x] FR: ③半返し計算（もらった額・用途から推奨お返し額を算出。ルールの根拠提示）
  - [x] FR: ④お返し品提案（予算・関係・用途から品物候補を提案。MVPは提案のみ＝外部リンク表示）
  - [x] FR: ⑤礼状文面生成（相手・用途・トーン指定で文面を生成、編集可）
  - [x] FR: 贈答イベント管理（受領→お返し検討→完了 のステータス遷移）
- [x] **Non-functional requirements（測定可能）**:
  - [x] 性能（例: 画像抽出のレスポンス目標、画面 p95）
  - [x] セキュリティ/プライバシー（OWASP）: PII を confidential〜restricted に分類、保存時暗号化・転送時TLS、本人のみアクセス（A01対策）、認証（A07）、入力検証（A03）、監査ログ（security events）
  - [x] 可用性・スケール（MVP相応）、ユーザビリティ（モバイルファースト）、アクセシビリティ
  - [x] コンプライアンス: 個人情報保護法（APPI）、第三者PIIの取り扱い同意・削除権
- [x] **Assumptions** — 暫定の前提（決済なし、ネイティブアプリなし、共有なし、認証は外部IdP想定 等）を assumption として明示
- [x] **Out of scope** — ⑥発送/物流、⑦お年玉相場、⑧贈与税110万枠、⑨親族間バランス警告、家族/親族共有、EC購入連携、決済

## 留意（scope-by-phase）

- inception フェーズのため、技術スタック・フレームワーク・DB・インフラには踏み込まない（NFR は「何を満たすか」を測定可能に記述、How は construction フェーズ）。
