# App Store 提出メタデータ（原案）

noshi（贈答とお返しの記録）の App Store Connect 提出に必要なメタデータ一式。コードではなく **App Store Connect 画面への転記用**。スクリーンショット(#211)以外は本ドキュメントの値をそのまま入力すればよい。

最終更新: 2026-09-16（#468 アフィリエイト再開を反映） / 対象ビルド: TestFlight build 26（1.2）以降

> 公開中のバージョンは iTunes Lookup で認証なしに確認できる:
> `https://itunes.apple.com/lookup?bundleId=me.noshi.app&country=jp`（2026-09-16 時点で 1.1）。
> TestFlight に上げる新ビルドはそれより高いマーケティングバージョンが必須（#495）。

---

## 1. App Privacy（プライバシー栄養ラベル）#199

App Store Connect → App Privacy で入力。**前提（コードで確認済み）**: サードパーティ解析/広告 SDK なし・IDFA 不使用・クロスアプリ追跡なし。アフィリエイトの広告リンクは掲載するが、アプリ内に広告 SDK は入れていない（#468）。

### Data Collection: **Yes**（データを収集する）

| データ種別（Apple カテゴリ） | 収集 | 用途 | 本人と紐付け | トラッキング |
|---|---|---|---|---|
| **Contact Info → Email Address** | Yes | App Functionality（アカウント・認証・お返し期限のメール通知） | Linked | No |
| **User Content → Photos or Videos**（ご祝儀袋の写真 #35） | Yes | App Functionality（記録・AI抽出） | Linked | No |
| **User Content → Other User Content**（贈答記録：金額・用途・相手の氏名・メモ） | Yes | App Functionality | Linked | No |
| **Identifiers → User ID**（Cognito sub / Apple・Google のサインイン識別子） | Yes | App Functionality（認証・本人のデータ識別） | Linked | No |

- 上記以外（位置情報・連絡先・ブラウズ履歴・購入履歴・診断・広告データ等）は **収集しない**。
- **Tracking**: 「**Data Not Used to Track You**」を選択（noshi はクロスアプリ/ブローカー共有の追跡をしない）。
- 補足: お返し提案は自前の編集コンテンツ（品目の提案と のし のマナー）が主。各提案の下に楽天市場の実商品を最大3件、「広告」と明示して掲載する（#468）。
  - 商品リストは CI が週次で生成した静的 JSON。アプリにもサーバーにも広告 SDK・計測タグは入れない。
  - **リンクを押すまで楽天へお客様の情報は送られない**。押した時点でアプリ外（システムのブラウザ）に出るため、以降の取得は楽天側のポリシーによる。
  - 商品画像の表示のため `thumbnail.image.rakuten.co.jp` への通信は発生する（画像取得のみ。識別子は送らない）。
  - したがって **Tracking は引き続き「Data Not Used to Track You」** のままでよい。アフィリエイトIDが識別するのは*掲載者である当方*であって、お客様個人ではない。

> 入力のコツ: 各データ種別で「Used for Tracking? → No」「Linked to the user's identity? → Yes」「Purposes → App Functionality」。

---

## 2. Age Rating（年齢制限）#201

App Store Connect → Age Rating の質問票はすべて **None / No** → 結果 **4+**。

| 質問 | 回答 |
|---|---|
| Cartoon or Fantasy Violence | None |
| Realistic Violence | None |
| Sexual Content or Nudity | None |
| Profanity or Crude Humor | None |
| Alcohol, Tobacco, or Drug Use | None |
| Mature/Suggestive Themes | None |
| Horror/Fear Themes | None |
| Medical/Treatment Information | None |
| Gambling | None |
| Contests | None |
| **Unrestricted Web Access** | **No** |

- Unrestricted Web Access を **No** とする根拠: アプリ内ブラウザで任意の Web を開く機能はない。外部サイトを開くのは**サインイン（Cognito Hosted UI）**と**お返し品の広告リンク**だけで、どちらも `@capacitor/browser` 経由で**システムのブラウザ**に出す（`lib/external.ts`）。アプリ自身の WebView に外部サイトを読み込ませないため、汎用ブラウザを内包したことにはならない。
- **要判断（#468 で新たに発生）**: 慶事の品目に「お酒」があり、日本酒の商品リンクが並ぶ。質問票の
  **Alcohol, Tobacco, or Drug Use** を現状の **None** のままにするかは、Apple の判断に委ねられる論点。
  - そのままにする根拠: アプリは酒類を販売せず、飲酒を推奨も描写もしない。贈答品目の一つとして名前が出るだけ。
  - 変えるなら **Infrequent/Mild** を選ぶ（推定レーティングが 4+ から上がる可能性がある）。
  - コード側で回避する手もある: `backend/tools/catalog/keywords.py` から `("cele", "sake")` を外す
    （＝そのバケツの商品を集めない）。編集コンテンツとしての「お酒」の案内は残したまま、実商品リンクだけ出さなくなる。
- 結果の推定レーティング: **4+**（上記の判断次第）。

---

## 3. デモアカウント＋レビューノート #212

### デモアカウント（作成済み）
Apple 審査員がメール/パスワードでログインできる専用アカウント（Sign in with Apple/Google も利用可だが、審査員はメール/パスワードを使うのが一般的）。

- **メール: `appreview@noshi.me`**（Cognito 作成済み・CONFIRMED）。
- **パスワード: 公開リポジトリには載せない**。実値は運用メモ（ローカル）管理。App Store Connect のレビューノート（非公開）入力時に実値を記入する。
- 種データ: 贈答記録7件を seed 済み（お返し期限・お返し提案が映える）。

> ⚠️ 下の英語ノートの `<DEMO_PASSWORD>` は **App Store Connect 貼り付け時に実パスワードへ必ず置換**すること（プレースホルダのまま提出すると審査員がログインできずリジェクトされる）。

### App Review Information → Notes（審査員向け・英語）
```
noshi is a Japanese app for recording gifts received/given and managing "okaeshi" (return gifts).

DEMO ACCOUNT (email/password):
  Email:    appreview@noshi.me
  Password: <DEMO_PASSWORD>   # ← App Store Connect 入力時に実値へ置換
Sign in with Apple and Sign in with Google are also available.

ACCOUNT DELETION (Guideline 5.1.1(v)) — fully in-app:
  Tab "マイページ" (My Page, bottom-right) → section "アカウント" → "アカウントを削除" (Delete Account)
  → confirm dialog → (for Sign in with Apple accounts) the native Apple re-authentication sheet appears
  → deletion completes inside the app. For Apple accounts we also revoke the Apple token via Apple's REST API.

EXTERNAL LINKS TO PHYSICAL GOODS (Guideline 3.1.3(e) / 3.1.5(a)):
  Return-gift suggestions are primarily editorial guidance (gift categories and "noshi" etiquette).
  Under each suggestion we also list up to three real products from Rakuten Ichiba, a Japanese
  online marketplace. These are clearly labeled "広告" (advertisement) next to the listing, and a
  notice at the top of the list states that the section contains advertising links.

  All listed items are PHYSICAL GOODS (towels, sweets, tea, tableware, detergent, catalog gift
  booklets, sake) that are bought and shipped outside the app. The app sells nothing, offers no
  digital content or subscriptions, and uses no In-App Purchase.

  Tapping a product opens the Rakuten page in the system browser (SFSafariViewController via
  @capacitor/browser). The app never loads external sites inside its own WebView, so there is no
  in-app browsing of arbitrary web content.

  We participate in the Rakuten affiliate program and may receive a referral fee when a purchase
  is made through these links. No advertising or analytics SDK is embedded in the app, and no user
  data is sent to Rakuten unless the user taps a link and leaves the app.

ALCOHOL REFERENCE: one celebration gift category is Japanese sake, so a few product listings are
  alcoholic drinks. The app does not sell alcohol and has no age-gated content of its own.

All text/UI is in Japanese.
```

> このノートの原本は `fastlane/review_notes.txt`。片方だけ直すとずれるので、変更は両方に入れること。

---

## 4. プライバシーポリシー #200（対応済み）
`frontend/src/legal.ts` の「6. 保管・削除」に Apple トークン失効の一文を追加済み（本ブランチ）:
> 「Appleでサインイン」をご利用の場合、アカウント削除時に Apple のサインイン連携（トークン）も失効させます。

アフィリエイト再開（#468）に伴い、同ファイルに「**9. 広告（アフィリエイト）について**」を追加した。
掲載の事実・紹介料を受け取ること・リンクを押すまで楽天へ情報が送られないこと・贈答記録を広告目的で
第三者提供しないことを明記している。「8. Cookie・ローカルストレージ」にあった
「アフィリエイト事業者への外部送信もありません」は事実と合わなくなるため書き換えた。

---

## 5. スクリーンショット #211（あなたの作業）
- 必須サイズ: **6.7"（iPhone 15/16 Pro Max 等, 1290×2796）** を最低用意（App Store はこのサイズから他サイズへ自動縮小可）。可能なら 6.5" も。
- 推奨カット（4〜6枚）: ①ホーム（記録一覧/お返し期限）②記録の詳細 ③お返し提案（購入導線）④ご祝儀袋の写真からAI抽出 ⑤マイページ（家族共有）。
- 撮影は実機 or シミュレータ。私が画面の選定・トリミング指示は出せます。

---

## 提出前チェックリスト
- [ ] App Privacy 入力（§1）
- [ ] Age Rating 入力（§2）→ 4+
- [ ] デモアカウント作成＋レビューノート貼付（§3）
- [x] プライバシーポリシーに削除/revoke 条項（§4・コード反映済み）
- [ ] スクリーンショット（§5）
- [ ] 掲載名「noshi 贈答とお返しの記録」/ カテゴリ ライフスタイル(主)＋ショッピング(副) / 価格 無料
- [ ] 輸出コンプライアンス（ITSAppUsesNonExemptEncryption=false 注入済み・#213）
