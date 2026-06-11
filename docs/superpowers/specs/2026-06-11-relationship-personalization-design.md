# お返し品提案の続柄パーソナライズ（相手による出し分け）設計

日付: 2026-06-11
状態: 承認済み（キルスイッチはプレリリースのため不要と判断し削除）
前提: `docs/superpowers/specs/2026-06-11-return-gift-suggestion-design.md`（お返し品提案 MVP・リリース済み）

## 1. 目的

提案候補の精度はこのプロダクトの分かれ目である。同じ「出産内祝い × ¥5,000-9,999」でも、
親族・友人・職場では適切な品が違う。**相手の続柄に応じて提案の並び順を出し分け**、
体感精度を上げる。

設計原則:

- 精度の判断は LLM に乗せる（人力ルール保守に逃げない）
- **コスト構造を変えない**: 楽天API・LLM のコール数は現状維持（既存コールの出力拡張のみ）
- 配信レイテンシを増やさない（並べ替えのみ）
- 出し分けの効果を**数字で検証できる**こと（グループ別 CTR）

スコープ外（YAGNI）: 相手個人の履歴（過去に贈った品の除外・好み学習）は次フェーズ。
バケツ軸への続柄追加（候補母集団の出し分け）も今回はやらない。

## 2. 続柄グループ（4分類）

| グループ | 既定続柄 | LLM への判断基準 |
|---|---|---|
| family | 親 / 子 / 兄弟姉妹 / 祖父母 / 叔父・叔母 / いとこ / 配偶者の親族 | 格式・改まった品・上質さ |
| friend | 友人 | 気軽さ・センス・話題性 |
| work | 同僚・仕事 | 個包装で配りやすい・日持ち・かさばらない |
| other | 近所 / その他 / 続柄未設定（空文字） | 無難さ・万人受け |

既定続柄の全11値（`rules.RELATIONSHIP_DEFAULTS`、実機確認済み）:
親・子・兄弟姉妹・祖父母・叔父・叔母・いとこ・配偶者の親族・友人・同僚・仕事・近所・その他
（※「叔父・叔母」「同僚・仕事」は中黒を含む1値。family 7 + friend 1 + work 1 + other 2 = 11）

### 写像の実装

`backend/app/catalog/relationships.py`（新規・純粋関数。tone.py と同パターン）:

- `GROUPS = ("family", "friend", "work", "other")`
- `group_of(relationship: str) -> str`
  1. 既定11続柄は表引き
  2. 世帯カスタム続柄はキーワード部分一致で振り分け（**先勝ち: work → family → friend の順**）:
     - work: 上司・部下・先輩・後輩・会社・職場・取引・同僚
     - family: 親・兄・姉・弟・妹・祖・叔・伯・従・甥・姪・義父・義母・義兄・義姉・義弟・義妹・義理
       （※単独の「義」は使わない。「義務」等の誤マッチ防止）
     - friend: 友
  3. どれにも該当しなければ other
- 判定順を work 優先にする理由: 「会社の先輩」「職場の友人」等の複合語は職場マナーが
  支配的なため。**既知の許容誤分類**: 「部活の先輩」「友人の先輩」も work になるが、
  無難方向への誤りであり許容する（修正はキーワードリスト更新のみで可能）
- **キーワードリストは本仕様の一部**。変更時は本ドキュメントとテストを同時に更新する
- `rules.RELATIONSHIP_DEFAULTS` の全値が表に存在することをパリティテストで保証
- API の `relationship` パラメータは**生の続柄文字列**（フロントは変換しない。
  グループへの変換はバックエンドの責務）

## 3. LLM 出力の拡張（バッチ・既存コールに追加）

### 出力スキーマ

```json
{"items": [{"itemCode": "...", "score": 0-100, "reason": "...",
            "fit": {"family": 0-100, "friend": 0-100, "work": 0-100, "other": 0-100}}]}
```

- fit を出力するのは**選定したトップ10のみ**（候補30件全件に付けさせない。
  出力トークン抑制をプロンプトで明示）

### プロンプト追加（curation.py）

文面は `curation.py` の定数 `_FIT_INSTRUCTION` として管理する。ひな形（実装はこの文面を使用）:

```
さらに各商品について、贈る相手のタイプ別の適合度 fit を 0-100 で評価してください:
- family（親族）: 格式があり改まった品・上質さを重視
- friend（友人）: 気軽さ・センス・話題性を重視
- work（職場）: 個包装で配りやすい・日持ちする・かさばらないことを重視
- other（近所・その他）: 無難で万人受けすることを重視
タイプ間で適合度に差を付けること（全タイプ同値の評価は避ける）。
```

- 既存の禁止事項（セール数値・最上級表現等）は不変
- `maxTokens` は **2000 → 2500 に引き上げ**る。
  試算: 現出力 ≈ 900トークン（10件 × code+score+reason60字）+ fit 追加 ≈ +300トークン
  ≈ 1,200。2500 はその約2倍でマージン十分。コスト増は出力 +300トークン/コール
  （126コール/日で月数百円オーダー）

### 検証（壊れない設計・validate_output）

- fit が欠損・dict でない・キー欠け・数値でない・0-100 外 → **そのキーを score で埋める**
  （並べ替え中立）。**キー単位**で処理し、他のキー・他の商品に波及させない
- 戻り値の各項目は `{item_code, llm_score, reason, fit}` 形（fit は常に4キー揃った dict）
- **退化検知**: バケツ内の全商品で fit の4値がすべて同値（差別化放棄）の場合、
  ジョブが `CatalogFitDegenerationCount` メトリクス（EMF）に計上する。
  並べ替えは中立になるだけなので配信は止めない（可視化のみ）

## 4. データモデル（NoshiCatalogTable 拡張）

RANK アイテムにフラット4属性を追加:

```
fitFamily (N) / fitFriend (N) / fitWork (N) / fitOther (N)
```

- フラット属性にする理由: 既存 store の手書きシリアライザ（S/N 型）と整合
- **fit の保存規則（一貫性の要）**: アイテムの dict に fit がある場合のみ4属性を書く。
  **線形フォールバック品（LLM失敗）には fit を書かない**（Put に含めない）
- **読み取り補完**: `_from_ddb` は fit 4属性が**1つでも欠けていれば**全グループを
  `llmScore` で補完する → 旧データ・フォールバック品（llmScore=0）は全グループ同値
  ＝並べ替え中立。移行措置は不要（48h TTL で自然入れ替え）
- 書き込みは `replace_bucket` の Put 属性追加のみ（Transact 10オペ構成は不変）
- 命名規約: **DynamoDB 属性は camelCase（fitFamily/relGroup）、API・Python 内部は
  snake_case（fit/rel_group）**。変換は store 層の責務（既存の priceFetchedAt ⇔
  price_fetched_at と同じ規約）

## 5. 配信の並べ替え（DynamoCatalogAdapter）

```
suggest(budget, relationship, purpose):
  group = group_of(relationship)              # relationship は生文字列
  ① 自バケツの行を fit ソート（後述）
  ② 3件未満なら隣接帯補完（既存規則: 下→上・±1帯・item_code 重複排除）
     補完分も fit ソートし、①の末尾に連結
     （①の最低 fit より②の最高 fit が高くても順序は入れ替えない。
       価格帯の適合 > 続柄の適合）
  ③ 合計10件に切り詰め → position は表示順で採番
```

### fit ソートの定義（LLMノイズ対策込み）

`key = (-(fit[group] // 10), 元のRANK順)` — つまり **fit を10点刻みに量子化して降順、
同帯は元の RANK 順（= LLM 総合評価順）**。

- 量子化の理由: fit の1〜2点差は LLM のノイズであり、総合スコアの高い品（RANK 上位）が
  僅差で沈む逆転を防ぐ。10点刻みなら「明確に適性が違う」場合だけ並びが変わる
- RANK#01〜10 は LLM 総合スコア降順で付番済み（前提スペック§8）なので、
  タイブレークは「総合的に良い品が先」を意味する

### レスポンス

- `rel_group`（family/friend/work/other）を suggestion dict に追加（計測用 §7）
- 金額目安フォールバック（カタログ空）は並べ替え・rel_group 付与の対象外（従来どおり）

## 6. フロント配線

- `loadSuggestions()` の `"友人"` 固定をやめ、`event.relationship`（生文字列）を渡す
  （`EventView.relationship` は既存フィールド。未設定は空文字 → バックエンドで other）
- `Suggestion` 型に `rel_group?: string` を追加
- クリック計測 `clickSuggestion` は suggestion の `rel_group` をそのまま echo
- UI の見た目は変更なし（並び順だけが変わる）

## 7. 効果計測

- `SuggestionClickIn` に optional `rel_group: str = ""`（pattern `^(family|friend|work|other)?$`）
  を追加し、CLICK レコードに `relGroup` 属性として保存（空なら属性を書かない）
- **プライバシー**: CLICK レコードは従来どおり **user_id を持たない**（PIIなし方針は不変）。
  rel_group は粗い4値で、ユーザー非紐付けのため要配慮情報には該当しない
- **計測値の限界（明記）**: rel_group はクライアント echo の参考値であり改ざん検知はしない。
  v2 のランキング還元では使用せず、その際は配信ログとの照合を前提とする（前提スペック§12 と同方針）
- **集計の原則**: グループ別 CTR は**同一バケツ内での比較**を原則とし、主指標は
  「リリース前後の同一グループ内 CTR 変化」とする（グループ間は母数・用途構成が
  偏るため直接比較しない）。集計は DynamoDB CLICK レコード（relGroup × bucket ×
  position）を日次バッチ等で手元集計（運用手順）

## 8. エラー処理

| 障害 | 挙動 |
|---|---|
| LLM が fit を返さない/不正（キー単位） | score 埋めで並べ替え中立（棄却しない） |
| LLM 全滅 → 線形フォールバック品 | fit 属性を**書かない** → 読み取り補完（llmScore=0 で全グループ同値）→ 中立 |
| 旧データ（fit 属性なし） | 読み取り時に llmScore で全グループ補完 → 中立（並びは従来どおり） |
| fit 退化（全グループ同値） | 並べ替え中立＋`CatalogFitDegenerationCount` で可視化 |
| 未知の続柄文字列 | other グループ（安全側） |
| クリックの rel_group 欠落 | optional のため受理（集計時は unknown 扱い） |

既存の多段フォールバック（線形→前回データ→金額目安）は一切変更しない。

## 9. テスト戦略

1. `group_of`: 既定11続柄の表引き／カスタムのキーワード振り分け（「会社の先輩」→work・
   「義母」→family・「ママ友」→friend）／「義務さん」が family に誤マッチしないこと／
   空文字→other／RELATIONSHIP_DEFAULTS とのパリティ
2. `validate_output`: fit 正常系／欠損・非dict・キー欠け・範囲外→score埋め（キー単位）／
   戻り値の fit が常に4キー
3. store: fit ありの書き込みで4属性が乗る／fit なし（線形フォールバック）で属性が乗らない／
   読み取りで属性欠けは llmScore 補完
4. adapter: 同一バケツで group により順序が変わる／**量子化**（fit 差9点以内は RANK 順維持・
   10点跨ぎで逆転）／**補完分は高 fit でも自バケツの後ろ**（境界ケース）／
   旧データ（fit なし）で順序不変
5. プロンプト: `_FIT_INSTRUCTION` の4基準が含まれる／「トップ10のみ fit」の指示
6. job: fit が `_curate` のマージを通って store まで届く／退化検知メトリクス
7. API: rel_group 付きクリック 204・不正値 422・空文字 204
8. frontend: 既存テスト維持（配線変更のみ）

## 10. 実装の統合ポイント（実装計画用メモ）

整合性レビューで列挙された変更箇所の全リスト:
relationships.py（新規）／curation.py（プロンプト・validate_output・maxTokens）／
job.py（_curate マージに fit 透過・退化検知）／store.py（Put 4属性・_from_ddb 補完・
put_click relGroup）／adapter.py（fit ソート・rel_group 付与・キルスイッチ）／
services.py・main.py（rel_group の受け渡し）／schemas.py（SuggestionClickIn.rel_group）／
frontend: App.tsx（"友人"固定の除去）・api.ts（rel_group echo）・types.ts（rel_group?）

## 11. 将来拡張（次フェーズ候補）

- 相手個人の履歴: 同じ party に過去贈った品（ReturnSuggestion 履歴）の除外
- クリックデータが貯まったらグループ別 CTR を見て、グループ粒度の調整や
  バケツ軸への昇格を判断
- 推薦理由文の続柄別出し分け（出力トークン増のため効果検証後）
- ランキング還元時の rel_group は配信ログ照合を前提に再設計
