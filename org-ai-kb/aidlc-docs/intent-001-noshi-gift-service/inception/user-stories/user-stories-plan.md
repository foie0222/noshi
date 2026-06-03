# User Stories — Plan

ジャーニー軸・ユーザー中心＋要のsystem・主＋attacker ペルソナ。OWASP lens 適用（abuse case）。

## personas.md

- [x] 主ペルソナ: 個人の贈答管理者（名前・役割・goals・context をドメインに即して）
- [x] attacker ペルソナ: 他人のデータ/PII を狙う第三者（abuse case の発生源）

## stories.md（ジャーニー順、S-n、各 AC と Requirements トレース付き、INVEST）

- [x] アカウント/認証（FR-1, NFR-2.3/2.4）
- [x] 撮影→AI抽出→確認修正→保存（FR-2, NFR-1.2, NFR-2.5）
- [x] Give 履歴台帳・集計・差分（FR-3）
- [x] 半返し計算＋根拠＋上書き（FR-4）
- [x] お返し品提案（提案のみ）＋イベント紐付け（FR-5, FR-7）
- [x] 礼状文面生成・編集（FR-6, NFR-2.7）
- [x] 贈答イベント ステータス管理・未完了一覧（FR-7）
- [x] system story: AI抽出サービスの挙動（信頼度・失敗時 fallback）（FR-2, NFR-1.2）
- [x] system story: アクセス制御＝本人スコープ強制（NFR-2.3, A01）
- [x] security/abuse story: 他人データ参照の拒否（attacker, NFR-2.3）
- [x] security story: 認証レート制限・セッション失効（NFR-2.4, A07）
- [x] security story: データ削除/エクスポートの監査ログ（NFR-2.6）
- [x] 横断 AC: 性能（NFR-1）・モバイルファースト/アクセシビリティ（NFR-4）を関連ストーリーに付与

## 留意
- inception フェーズ: 技術スタックに踏み込まない。AC は pass/fail 検証可能に。
