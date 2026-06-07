# Requirements — noshi otoshidama（intent-007, N2）

## Intent summary
- Type: feature（brownfield）/ Scope: 単一サービス noshi-service / Classification: brownfield / Affected repos: noshi
- 源泉: design-review-002 の N2。intent-001..006 を保持。

## Functional requirements
- **FR-7-1 お年玉相場テーブル**
  - FR-7-1.1 年齢（学齢区分）から一般的な相場レンジ（low〜high）を返す: 未就学=0〜1,000 / 小学校低学年=1,000〜3,000 / 小学校高学年=3,000〜5,000 / 中学生=5,000 / 高校生=5,000〜10,000 / 大学生以上=10,000。
  - FR-7-1.2 区分の一言（例: 「低学年は1,000〜3,000円が目安」）を返す。
- **FR-7-2 お年玉の目安ツール**
  - FR-7-2.1 年齢を入力すると相場レンジと一言が表示される。
  - FR-7-2.2 「家庭・地域で異なる一般的な目安」である旨を明記する。
- **FR-7-3 配置**
  - FR-7-3.1 マイページに「お年玉の目安」として控えめに配置する。

## Non-functional requirements
- NFR は intent-001..006 を維持。相場判定は確定的（年齢→区分）。データ非依存（本人データを参照しない）。WCAG AA。
- 本人スコープ・監査・分類は不変（本機能はデータを読み書きしない）。

## Assumptions
- 技術スタック不変。相場は一般的な目安（出典は一般慣習）。学齢は年齢から概算。

## Out of scope
- 地域別/家庭別の精緻な相場、贈与記録との自動連携、通知
