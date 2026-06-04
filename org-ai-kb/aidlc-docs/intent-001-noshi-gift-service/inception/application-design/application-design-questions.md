# Application Design — Clarification Questions

Input: requirements.md, stories.md, personas.md, screen-data-map.md。Lens: OWASP active（トラスト境界・データ分類）。
inception フェーズ: 技術スタックには踏み込まず、論理コンポーネント構造を設計する。

### Q1: コンポーネント分割の方針

a) 能力/ドメイン単位の論理コンポーネント（Identity / Ledger / Extraction / HalfReturn / Suggestion / LetterGen / GiftEvent / Consent / Audit）＝モジュラーな単一サービス
b) レイヤー単位（UI / アプリ / ドメイン / データ）
c) おまかせ（requirements から最適を提案）

**Trade Offs:** MVP は単一サービスだが、AI抽出・生成など責務が明確に分かれる。(a) は将来のサービス分割もしやすい。

**Recommendation:** a) 能力/ドメイン単位の論理コンポーネント。

[Answer]: a) 能力/ドメイン単位の論理コンポーネント

### Q2: AI抽出の通信パターン

a) 非同期ジョブ＋イベント（撮影→ジョブ投入→抽出完了イベント。loading画面と整合、event-catalog を作成）
b) 同期リクエスト/レスポンス（呼び出しで待つ）
c) おまかせ

**Trade Offs:** 抽出は p95<10s だが画像/LLM 処理は変動。非同期は体験が安定しスケールしやすいが、イベント基盤が要る。同期は単純。

**Recommendation:** a) 抽出のみ非同期（他は同期）。

[Answer]: a) 抽出のみ非同期ジョブ＋イベント（他は同期）

### Q3: フロントエンドのデータ集約（screen-data-map より）

home など複数コンポーネントからデータを集約する画面がある。

a) BFF（Backend-for-Frontend）で集約（モバイル1往復・認可境界を集約）
b) フロントから各サービス直接呼び出し
c) クライアント側合成

**Trade Offs:** BFF はモバイルの往復削減・トラスト境界の一元化（OWASP）に有利だが層が増える。直接呼びは単純だが画面ごとに多数呼び出し。

**Recommendation:** a) BFF を置く。

[Answer]: a) BFF で集約

### Q4: 外部依存（OCR/LLM）の論理的扱い

a) 内部ポート（抽象インターフェース）の背後に隔離し、external-dependencies.md に失敗モードを明記（ベンダー非依存）
b) 各コンポーネントから直接利用

**Trade Offs:** (a) はベンダー差し替え可・失敗時フォールバック（手入力）と整合・restricted データの外部送信境界を明確化（OWASP）。

**Recommendation:** a) 内部ポートで隔離。

[Answer]: a) 内部ポートで隔離（external-dependencies に失敗モード明記）
