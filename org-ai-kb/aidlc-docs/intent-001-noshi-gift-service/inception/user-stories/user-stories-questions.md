# User Stories — Clarification Questions

Input: requirements.md（FR-1..7, NFR-1..5）。Lens: OWASP active（abuse case / attacker persona を考慮）。

### Q1: ストーリーの整理軸

a) ユーザージャーニー（撮影→記録→半返し→お返し選択→礼状→完了）
b) 機能エリア（FR 単位）
c) システムレイヤー（UI/バックエンド/連携/運用）

**Recommendation:** a) ジャーニー軸。「贈答を続けられる」体験の流れに沿い、MVP の検証ポイントが明確。

[Answer]: a) ユーザージャーニー

### Q2: カバレッジの広さ

a) ユーザー向け中心 ＋ 重要なシステムストーリー（AI抽出・セキュリティ）のみ
b) ユーザー向け＋バックエンド＋連携＋運用まで網羅
c) ユーザー向けのみ

**Recommendation:** a) MVP 相応。ユーザー向けを主軸に、AI抽出やアクセス制御など要のシステム挙動だけ system story 化。運用は最小。

[Answer]: a) ユーザー向け中心＋要のシステムストーリー

### Q3: ペルソナの範囲

a) 主ペルソナ（個人の贈答管理者）＋ attacker ペルソナ（abuse case 用）
b) 主ペルソナのみ
c) 複数の利用者ペルソナを細分化

**Trade Offs:** MVP はソロ利用なので利用者ペルソナは実質1種。OWASP lens 的には attacker ペルソナを置くと abuse/security ストーリーが書きやすい。

**Recommendation:** a) 主ペルソナ＋attacker ペルソナ。

[Answer]: a) 主ペルソナ＋attacker ペルソナ

### Q4: NFR の扱い

a) 主要なセキュリティ/プライバシー NFR は独立ストーリー化、その他は横断的な受け入れ条件
b) すべて独立ストーリー
c) すべて横断的 AC

**Recommendation:** a) ミックス。NFR-2（セキュリティ）の要は独立ストーリー、性能/UX は横断 AC。

[Answer]: a) 主要セキュリティNFRは独立ストーリー、その他は横断AC（推奨採用）
