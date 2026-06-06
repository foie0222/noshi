# Functional Design — Plan（unit: noshi-service）

技術非依存のドメイン/業務ロジックを3成果物で記述。OWASP（入力検証・本人スコープ・分類）を業務ルールに織り込む。

## business-logic-model.md
- [x] アクター（owner）と各ワークフローの happy/exception パス
- [x] 撮影→抽出→確認→記録（全項目確認、低信頼は要確認、失敗→手入力）
- [x] お返しフロー（半返し→提案→礼状→イベント反映）
- [x] 削除/エクスポート（確認＋監査）
- [x] 本人スコープ強制（A01）を全ワークフローの前提条件として明記

## domain-entities.md
- [x] User, ConsentRecord, Party, GiftRecord, ExtractionJob, GiftEvent, ReturnSuggestion, Letter, AuditEntry
- [x] 属性・関係・不変条件・ライフサイクル（application-design の data-models を精緻化）
- [x] GiftEvent.status の状態モデル（received/considering/done・自由遷移・done は未完了一覧から除外）

## business-rules.md
- [x] BR-半返し: 用途別返礼率（香典1/2, 出産1/3〜1/2, 結婚1/2, 快気1/3〜1/2, 一般慶事1/3〜1/2, 中元歳暮=返礼不要）・1,000円丸め・上書き可
- [x] BR-抽出: 信頼度しきい値・全項目確認必須・確定前は未保存
- [x] BR-検証: 金額>0、必須項目、画像形式/サイズ（A03）
- [x] BR-認可: resource.ownerId==session.userId（A01）、違反は FORBIDDEN＋監査
- [x] BR-未完了: received/considering かつお返し未完了を一覧（通知なし）
- [x] BR-礼状: LLM送信は最小化（restricted を不要送信しない）
- [x] hard/soft 制約の区別
