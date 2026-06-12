# Google + LINE ソーシャルログイン設計

日付: 2026-06-12
状態: レビュー中（マルチエージェントレビュー反映済み v2）
関連: infra/cdk/lib/auth-stack.ts（Cognito User Pool）、frontend/src/lib/cognito.ts、backend/app/auth.py

## 1. 目的

メールアドレス＋パスワードの登録摩擦を解消する。第一弾として **Google と LINE** を導入する
（LINE は日本のコンシューマで Google と並ぶ主流）。Apple は iOS アプリ展開時（#150）、
パスキーは第二弾（#151）。

設計原則:

- 既存方針の踏襲: フロントは**依存ゼロ（素の fetch）**・IdToken を localStorage・backend の
  JWT 検証は無変更
- 既存のメール+パスワードログインと**並存**（置き換えない）
- 同一メールのアカウントは**自動統合**（§4。ただしメール検証の安全弁つき）
- ログイン画面の見た目はブランドトーン維持（Hosted UI 画面は使わない）

### セキュリティ上の受容リスク（明示）

- **IdToken を localStorage に保存**（既存方針）: XSS があればトークンが窃取され得る。
  緩和は IdToken の1時間失効のみ。ソーシャル追加で新たに増えるリスクではないため踏襲する。
- **LINE のメールを「検証済み」とみなして自動統合**（§4）: LINE は OIDC で email_verified を
  返さないが、LINE 自身が登録時にメール確認を行うため実質検証済みと判断し、ユーザー判断で
  受容する。被害最小化として、リンク先の既存ユーザーが**メール確認済み**の場合に限定する。

## 2. アーキテクチャ概要

```
[ログイン画面] Googleで続ける / LINEで続ける ボタン
   ↓ /oauth2/authorize?identity_provider=...（Hosted UI スキップ・PKCE付き）
[Google / LINE の認証画面]
   ↓ Cognito が登録済み callback URL（https://noshi.me/）へ code/state を付けてリダイレクト
[フロント] state照合 → /oauth2/token へ code+verifier を POST（素のfetch）
   → IdToken を既存 localStorage キーへ → 以降は完全に既存フロー
[backend] 変更なし（同一 User Pool の IdToken。既存の aud/iss/JWKS 検証が通る）
```

注: 登録する callback URL は `https://noshi.me/`（完全一致）。Cognito がそこへ
`?code=...&state=...` を付けてリダイレクトするが、付加クエリは URI 一致検証の対象外。

## 3. CDK（auth-stack 拡張）

- **UserPoolDomain**: prefix 方式 `noshi-me`
  → `https://noshi-me.auth.ap-northeast-1.amazoncognito.com`
  - **prefix 衝突時**: `cdk deploy` が失敗する。デプロイ前に AWS Console / CLI で空きを確認し、
    取得済みなら `noshi-app` を代替に使う（手順は §7）。独自ドメイン auth.noshi.me は将来の磨き込み
- **Google IdP**: `UserPoolIdentityProviderGoogle`
  - scopes: `openid email profile`
  - attributeMapping: email→email、**email_verified→email_verified（必須・§4のガードに使う）**
- **LINE IdP**: `UserPoolIdentityProviderOidc`（**プロバイダ名 `LINE`** — §5 の identity_provider と
  CDK の providerName を同一文字列で統一）
  - issuer: `https://access.line.me`（OIDC discovery 自動）
  - scopes: `openid profile email`
  - attributeMapping: email→email（LINE は email_verified を返さないためマップしない）
  - attributesRequestMethod: GET
- **UserPoolClient（既存 NoshiWebClient を拡張）**:
  - authFlows: 既存の userSrp/userPassword に加え **authorizationCodeGrant**
  - oAuth.flows: authorizationCodeGrant（クライアントシークレットなし）
  - oAuth.scopes: OPENID / EMAIL / PROFILE
  - **callbackUrls / logoutUrls: `https://noshi.me/` のみ**（本番クライアントに localhost は
    含めない＝認可コード横取りの足場を作らない。ローカルではソーシャルボタンを非表示にする
    設計（§5）で開発に支障なし。ローカル実機検証が要るときは別クライアントを将来用意）
  - supportedIdentityProviders: COGNITO, Google, LINE
  - PKCE に関する注意: **Cognito は public client でも PKCE を強制しない**。フロント実装が
    常に code_challenge/verifier を付与し、verifier 無しのトークン交換経路をコード上作らない
    ことで担保する（§5・§8）
- **シークレット管理**: Secrets Manager に1シークレット `noshi/social-login`
  （JSON: googleClientId / googleClientSecret / lineChannelId / lineChannelSecret）。
  CDK は `SecretValue.secretsManager(...).unsafeUnwrap()` 相当で参照（CFN 動的参照。
  SSM SecureString は UserPoolIdentityProvider で未対応のため不可）。**シークレットは
  デプロイ前に手動登録が前提**（§7）
- **Pre-signup Lambda**（§4）: **AuthStack 内**で `lambda.Function`（runtime python3.12・
  handler `app.auth_triggers.presignup_handler`・code は既存 `backendLambdaCode()` 流用・
  timeout 10s・env に `NOSHI_COGNITO_POOL_ID`）として定義し、`userPool.addTrigger(PRE_SIGN_UP, fn)`。
  権限は `userPool.grant(fn, "cognito-idp:ListUsers", "cognito-idp:AdminLinkProviderForUser")`
  （grantAdmin は広すぎるので個別付与）
- 既存 User Pool（email required・不変、selfSignUp、SES 送信）は変更しない。
  **CfnOutput に `CognitoDomain`（= domain.domainName）と既存 UserPoolClientId/UserPoolId/Issuer**

## 4. アカウント自動統合（Pre-signup Lambda）

トリガ: `PreSignUp_ExternalProvider`（Google/LINE での初回サインアップ時のみ発火。
メール+パスワードの通常サインアップ＝`PreSignUp_SignUp` は対象外）。

```
presignup_handler(event):
  attrs = event["request"]["userAttributes"]
  email = attrs.get("email", "")
  provider = (event["userName"] のプレフィックス: "Google" | "LINE")

  1. email が空 → 何も設定せず event をそのまま返す
     （Cognito の email required が後段で自然にエラー → §6 のメッセージ）

  2. IdP 側メール検証ガード:
     - Google: attrs["email_verified"] == "true" でなければ「リンクせず素通し」
       （= 別アカウント作成。autoConfirm はしない＝Cognito 既定の確認フローに委ねる）
     - LINE: email_verified は来ない。受容リスク（§1）として検証済みとみなし次へ進む

  3. ListUsers(Filter='email = "..."') で既存ユーザーを取得
     - 候補は「status==CONFIRMED かつ email_verified==true かつ native ユーザー
       （identities 属性を持たない＝メール+パスワード登録）」に限定
     - 該当0件 → リンク不要。autoConfirmUser=true / autoVerifyEmail=true で素通し（新規作成）
     - 該当1件 → その native ユーザーへ AdminLinkProviderForUser でリンク（下記4）
     - 該当2件以上 → 決定不能。リンクせず素通し＋CloudWatch に warning ログ
       （重複は通常起こらないが、起きたら安全側で別アカウント）

  4. AdminLinkProviderForUser(destinationUser=native, sourceProvider=provider, sourceSub=...)
     成功 → raise Exception("ALREADY_LINKED_RETRY")  # 今回試行を中断しフロントに自動リトライさせる
     失敗（例外）→ ログに記録し event をそのまま返す（別アカウントとして作成・ログイン継続優先）
```

- **email_verified ガードの意味（最重要）**: Google で未検証メールのアカウントや、既存ユーザーが
  メール未確認のケースを自動リンクから除外し、なりすましによるアカウント乗っ取りを防ぐ。
  LINE のみ受容リスクとして検証済み扱いだが、**リンク先 native ユーザーは email_verified==true
  必須**としているため逆方向の乗っ取り（未検証の既存ユーザーへのリンク）は防げる
- **native 登録時の既存 federated ユーザー（逆順）**: メール+パスワード登録は本トリガ対象外。
  既存 User Pool は email を alias にしていない（signInAliases は email のみ＝サインイン識別子）。
  同一メールの federated ユーザーが先に居る状態で native 登録すると Cognito が
  UsernameExistsException 相当で弾く想定。**プレリリースでは「同一メールの先客 federated が
  いると native 登録できない」挙動を受容**し、恒久対応（ログイン後の手動連携 UI）は別 Issue とする
- Lambda 実装: `backend/app/auth_triggers.py`（presignup_handler・boto3 遅延 import・
  ListUsers/AdminLinkProviderForUser はクライアント注入可能にしてユニットテスト）
- 既知の挙動: 初回リンク時のみリダイレクト1往復ぶん余計に待つ（数秒）。2回目以降は通常どおり

## 5. フロント（cognito.ts 拡張・依存ゼロ）

sessionStorage キー（確定）: `noshi_pkce_verifier` / `noshi_oauth_state` /
`noshi_oauth_provider` / `noshi_oauth_retry`。

新規関数（既存のメール+パスワード関数・localStorage キーは不変）:

- `socialSignIn(provider: "Google" | "LINE")`
  1. PKCE: `code_verifier`（crypto.getRandomValues 32バイト→base64url）、
     `code_challenge`（SHA-256 → base64url、`crypto.subtle.digest`）
  2. `state`（16バイト base64url）。verifier / state / provider を sessionStorage へ
  3. `/oauth2/authorize` へリダイレクト（identity_provider=provider・response_type=code・
     client_id・redirect_uri=`location.origin + "/"`・scope=`openid email profile`・state・
     code_challenge・code_challenge_method=S256）
- `handleAuthCallback(): Promise<"ok" | "retry" | "error" | "none">`
  アプリ起動時に1回呼ぶ:
  - URL に `code` も `error` も無ければ "none"
  - `error` あり:
    - `error_description` に `ALREADY_LINKED_RETRY` を含み、かつ `noshi_oauth_retry` が
      未設定・かつ `noshi_oauth_provider` が保存済み → フラグを立てて**同じ保存済み provider**へ
      自動再認可（戻り値 "retry"。関数内でリダイレクト発火）
    - それ以外（別エラー、または既にリトライ済み）→ 一時値とフラグを掃除して "error"
  - `code` あり: state 照合（`noshi_oauth_state` と不一致なら掃除して "error"）→
    `/oauth2/token` へ POST（grant_type=authorization_code・client_id・code・
    redirect_uri・**code_verifier 必須**、application/x-www-form-urlencoded）→
    IdToken を既存キーへ保存 → 掃除して "ok"
  - **掃除**: "ok"/"error" を返す際に verifier/state/provider/retry をすべて削除し、
    `history.replaceState` で URL から code/state/error/error_description を除去。
    これによりリロード時の code 再利用と無限リトライを防ぐ
- 環境変数: `VITE_COGNITO_DOMAIN` を追加（ci.yml が cdk-outputs.json の
  `NoshiAuthStack.CognitoDomain` から注入）。新設の `socialEnabled()` が CLIENT_ID と DOMAIN の
  両方が非空のとき true（authEnabled は従来どおり CLIENT_ID のみ。メール+パスワードは
  domain 未注入環境でも使える。未注入のローカルではソーシャルボタン非表示）

### App.tsx の処理対応（戻り値ごと）

- 起動時 useEffect で `handleAuthCallback()` を1回 await
- `"none"` → 何もしない（通常起動・既存の pickInitialScreen）
- `"ok"` → ログイン済みへ。ホーム表示
- `"retry"` → 関数内で再認可リダイレクト済み。App は何もしない（「アカウントを連携しました…」の
  一瞬表示はリダイレクト前に notify で出す）
- `"error"` → ログイン画面へ＋エラー表示

### ログイン画面（App.tsx）

- 既存フォームの上に「Google で続ける」「LINE で続ける」ボタン＋「または」区切り
- ブランド準拠: Google = 白地・枠線・Gロゴ配色 ／ LINE = #06C755 白文字。`.btn` の形状踏襲

## 6. エラー処理

| 障害 | 挙動 / 文面 |
|---|---|
| state 不一致（CSRF の疑い） | token 交換せずログイン画面＋「ログインに失敗しました。もう一度お試しください。」（classifyCallback はエラー理由を区別せず "error" を返すため文言は1種類） |
| トークン交換失敗（4xx/5xx/ネットワーク） | ログイン画面＋「ログインに失敗しました。もう一度お試しください。」（cognitoErrorMessage に追記） |
| リンク直後の ALREADY_LINKED_RETRY | 自動リトライ1回（フラグ）。再失敗は通常エラー表示 |
| LINE がメール未提供（権限未申請・ユーザー拒否） | 「LINEログインにはメールアドレスの許可が必要です。」 |
| Pre-signup の email_verified 未充足（Google 未検証） | リンクせず別アカウント作成（ログインは成功・データは別） |
| Pre-signup の AdminLink 失敗 | CloudWatch ログ記録し素通し（別アカウント許容・ログイン継続優先） |
| callback 処理中の二重実行（リロード等） | code は一度しか使えず token 交換失敗 → 通常エラー表示で安全 |

文面は cognitoErrorMessage パターンに追記。確定文面は上表のとおり。

## 7. 手動準備（ユーザー作業）

1. **Cognito ドメイン prefix の空き確認**:
   `aws cognito-idp describe-user-pool-domain --domain noshi-me` が NotFound なら空き。
   取得済みなら §3 の代替 prefix `noshi-app` を使う（CDK 定数も合わせる）
2. **Google Cloud Console**: OAuth クライアント ID（ウェブアプリ）作成。承認済みリダイレクト URI =
   `https://noshi-me.auth.ap-northeast-1.amazoncognito.com/oauth2/idpresponse`
3. **LINE Developers**: LINE ログインのチャネル作成（ウェブアプリ）。コールバック URL = 同上。
   **「メールアドレス取得権限」を申請**（無料・利用目的の記入。未承認のうちは LINE ログインが
   エラーになるため、承認後にリリース）
4. **Secrets Manager 登録**（デプロイより先に必須・コマンドは実装計画に含める）:
   `noshi/social-login` = {"googleClientId","googleClientSecret","lineChannelId","lineChannelSecret"}

## 8. テスト戦略

1. **フロント純関数（vitest）**: PKCE 生成（base64url 形式・長さ）／authorize URL 組み立て／
   callback パース（code/error/none・**error_description の ALREADY_LINKED_RETRY 判別**）／
   state 照合（不一致拒否）／リトライ（未設定→retry・設定済み→error の1回上限）／
   掃除（成功/失敗時に sessionStorage と URL がクリアされる）
2. **Pre-signup Lambda（pytest・boto3 クライアント注入）**:
   email 欠落→素通し／Google email_verified!=true→リンクせず素通し／既存検証済み native 1件→
   リンク+ALREADY_LINKED_RETRY 例外／既存0件→autoConfirm 素通し／既存2件以上→素通し+警告／
   AdminLink 失敗→素通し
3. **CDK**: tsc + synth（IdP・ドメイン・クライアント・Lambda トリガがエラーなく合成）
4. **結合（手動）**: 実 Google / 実 LINE でログイン→記録作成→ログアウト→メール+パスワードで
   同一データが見えること（自動統合の確認）。Google 未検証メールでは別アカウントになることも確認

## 9. スコープ外（YAGNI）

- Apple サインイン（#150）・パスキー（#151）
- ログイン後の手動アカウント連携 UI（同一メールの先客 federated 対応・LINE の安全な統合強化）→
  効果検証後に別 Issue
- 独自認証ドメイン（auth.noshi.me）・ローカル用の別クライアント
- Cognito の logout エンドポイント連携（localStorage クリアのみ。共有端末では IdP 側セッションが
  残る一般的挙動。ユーザー向け注記は将来）
- リフレッシュトークンの利用（既存どおり IdToken 1時間・再ログイン方式を維持）

## 10. 申し送り

- backend は federated ユーザーの email クレームを native と区別しない。将来 email を信頼境界に
  する機能（家族共有の招待でメール照合する等）を追加する際は、IdP 由来 email の検証状態を
  別途考慮すること（本スコープ外）。
