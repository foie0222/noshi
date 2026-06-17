# App Store 提出メタデータ（原案）

noshi（贈答とお返しの記録）の App Store Connect 提出に必要なメタデータ一式。コードではなく **App Store Connect 画面への転記用**。スクリーンショット(#211)以外は本ドキュメントの値をそのまま入力すればよい。

最終更新: 2026-06-16 / 対象ビルド: TestFlight #17 以降

---

## 1. App Privacy（プライバシー栄養ラベル）#199

App Store Connect → App Privacy で入力。**前提（コードで確認済み）**: サードパーティ解析/広告 SDK なし・IDFA 不使用・クロスアプリ追跡なし。アフィリエイトは Safari への外部リンクのみ（noshi 側で利用者を追跡しない）。

### Data Collection: **Yes**（データを収集する）

| データ種別（Apple カテゴリ） | 収集 | 用途 | 本人と紐付け | トラッキング |
|---|---|---|---|---|
| **Contact Info → Email Address** | Yes | App Functionality（アカウント・認証・お返し期限のメール通知） | Linked | No |
| **User Content → Photos or Videos**（ご祝儀袋の写真 #35） | Yes | App Functionality（記録・AI抽出） | Linked | No |
| **User Content → Other User Content**（贈答記録：金額・用途・相手の氏名・メモ） | Yes | App Functionality | Linked | No |
| **Identifiers → User ID**（Cognito sub / Apple・Google のサインイン識別子） | Yes | App Functionality（認証・本人のデータ識別） | Linked | No |

- 上記以外（位置情報・連絡先・ブラウズ履歴・購入履歴・診断・広告データ等）は **収集しない**。
- **Tracking**: 「**Data Not Used to Track You**」を選択（noshi はクロスアプリ/ブローカー共有の追跡をしない）。
- 補足（楽天アフィリエイト）: お返し提案の「商品を見る」は Safari で楽天市場を開く外部リンク。noshi は利用者データを楽天に共有しない（URL にアフィリエイトIDを付与するのみ）。楽天サイト上の Cookie 等は楽天の責任範囲でプライバシーポリシーに明記済み。Apple の "Tracking" 定義には該当しない判断。

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

- Unrestricted Web Access を **No** とする根拠: アプリ内ブラウザで任意の Web を開く機能はない。お返し提案のリンクは**特定の楽天市場商品ページ**を**システムの Safari**で開くのみ（アプリ内に汎用ブラウザを内包しない）。
- 結果の推定レーティング: **4+**。

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

EXTERNAL PURCHASE LINKS:
  Return-gift suggestions link out to Rakuten (rakuten.co.jp) in Safari via the Rakuten affiliate program.
  These are physical goods purchased on an external website, so no In-App Purchase is used (Guideline 3.1.1).

All text/UI is in Japanese.
```

---

## 4. プライバシーポリシー #200（対応済み）
`frontend/src/legal.ts` の「6. 保管・削除」に Apple トークン失効の一文を追加済み（本ブランチ）:
> 「Appleでサインイン」をご利用の場合、アカウント削除時に Apple のサインイン連携（トークン）も失効させます。

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
