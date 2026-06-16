# アカウント削除に Apple トークン revoke（論理アカウント単位）設計

- 日付: 2026-06-16
- 関連: #198（アプリ内アカウント削除・5.1.1(v)）, #204（Sign in with Apple）, アカウント統合 §4.8（2026-06-15-account-unification-design.md）
- ステータス: 設計（井上さん承認済み）

## 1. 背景と問題

App Store ガイドライン 5.1.1(v)：アカウント作成を持つアプリは**アプリ内で完結する恒久的なアカウント削除**を提供必須。さらに **Sign in with Apple を使うアプリは Apple の REST `/auth/revoke` でトークンを失効**させること（"should"。レビュアーが実質要求するため対応する）。Apple 公式：refresh/access トークンや authorization code を**持っていない場合は、削除リクエストを果たせばよい**。

noshi の現状の問題:
1. **Cognito（Hosted UI）は Apple の refresh token をアプリに渡さない** → revoke を呼ぶ手段が無い。
2. 現状の `delete_account`（services.py）は **canonical sub 1つ分の世帯処理のみ**。アカウント統合後は 1人＝複数 Cognito ユーザー（代表＋別名）なので、**別名 Cognito ユーザー・`account_link`・`EMAIL#` が残り「恒久削除」になっていない**（別ログインで復活し得る）。
3. 削除導線は確認ダイアログのみで再認証なし（App.tsx）。

## 2. ゴールと非ゴール

### ゴール
- Apple 連携アカウントの削除時、**ネイティブ Sign in with Apple で再認証 → authorization code 取得 → Apple とコード交換 → `/auth/revoke` で失効**（トークンは保存しない）。
- 削除を**論理アカウント（代表＋全別名）単位**にし、Apple revoke ＋ データ purge ＋ `account_link`/`EMAIL#`/逆引き掃除 ＋ **全 Cognito ユーザー削除**で恒久削除を成立させる（統合 §4.8 を同時解消）。

### 非ゴール（YAGNI）
- メール/Google のみのアカウントへのパスワード再認証（本人確認）追加。今回は **Apple 連携アカウントのみ再認証**（revoke の手段を兼ねる）。メール/Google は現状の確認ダイアログのまま（別途・後回し）。
- Web での Apple revoke。Web はネイティブ Apple シートが無いため revoke なしで削除（Apple の「トークンを持たない場合は削除のみでよい」に合致。審査対象は iOS アプリ）。
- Apple トークンの長期保存（Option B＝削除時に都度取得し即 revoke、保存しない）。

## 3. 全体フロー

```
「アカウントを削除」タップ
 → 確認ダイアログ（既存）
 → apple_linked（/api/household が返すフラグ）で分岐
    ├ true かつ iOS ネイティブ: ASAuthorization 起動 → authorization code 取得
    │   → DELETE /api/account（body: {apple_authorization_code}）
    └ false（または Web）: DELETE /api/account（code なし）
 → backend（論理削除）:
    ① code があれば Apple とコード交換 → refresh_token → /auth/revoke（ベストエフォート）
    ② データ purge（既存 _purge_household・owner 引き継ぎ）
    ③ account_link / 逆引き PRIMARY# / 代表を指す EMAIL# を掃除
    ④ 本人の全 Cognito ユーザー（代表＋全別名 sub）を削除
 → アプリ内で「削除しました」表示（in-app 完結）
```

## 4. コンポーネント

### 4.1 フロント（`frontend/`）
- **`@capacitor-community/apple-sign-in` を追加**（iOS ネイティブ ASAuthorization 用）。
- 再認証要否は **専用エンドポイント `GET /api/account/delete-info` → `{apple_linked: boolean}`** で取得（削除画面を開いた時のみ呼ぶ。Apple 判定は Cognito を引くため、頻繁な `/api/household` には載せない）。
- 削除フロー（App.tsx の `deleteAccount` ハンドラ拡張）:
  - `apple_linked && Capacitor.isNativePlatform()` の時のみ、確認後に `SignInWithApple.authorize({ scopes:[], ... })` 相当を呼び `response.authorizationCode` を取得し、`api.deleteAccount({ appleAuthorizationCode })` で送る。
  - それ以外は従来どおり `api.deleteAccount()`（code なし）。
  - Apple シートをユーザーがキャンセルしたら削除は中止（エラー表示せず元の画面へ）。
- `api.deleteAccount(opts?)`（api.ts）: `DELETE /api/account`、body に `apple_authorization_code` を任意で載せる。

### 4.2 バックエンド: Apple revoke（新規 `backend/app/apple_revoke.py`）
純度高めの関数群（HTTP クライアントとシークレット取得を注入可能にしテスト容易化）:
- `build_client_secret(team_id, key_id, private_key_pem, client_id, now) -> str`: ES256 JWT。header `{alg:ES256, kid:key_id}`、claims `{iss:team_id, iat, exp(数分), aud:"https://appleid.apple.com", sub:client_id}`。`client_id` は**ネイティブ用に App ID `me.noshi.app`**（Web の Services ID とは別。同じ鍵 `appleKeyId` で署名可）。**既存の `pyjwt[crypto]==2.13.0` で ES256 署名可（依存追加なし）**。
- `exchange_code(code, client_id, client_secret, http) -> dict`: POST `https://appleid.apple.com/auth/token`（`grant_type=authorization_code`, `code`, `client_id`, `client_secret`）→ `{access_token, refresh_token, ...}`。redirect_uri はネイティブコード交換では不要。
- `revoke(token, token_type_hint, client_id, client_secret, http) -> None`: POST `https://appleid.apple.com/auth/revoke`（`token`, `token_type_hint`, `client_id`, `client_secret`）。2xx で成功。
- `revoke_apple_for_code(code, secret_provider, http, now) -> bool`: 上記をまとめる高レベル関数。シークレット（appleTeamId/appleKeyId/applePrivateKey）を取得→client_secret 生成→code 交換→refresh_token を revoke。**例外は握りつぶして False を返す**（削除をブロックしない）。
- 設定: `APPLE_NATIVE_CLIENT_ID = "me.noshi.app"`（App ID）。シークレットは Secrets Manager `noshi/social-login`（`appleTeamId`/`appleKeyId`/`applePrivateKey`）。

### 4.3 バックエンド: 論理アカウント削除（services + main）
- `services.delete_account(user_id)` を拡張（user_id は境界正規化済み＝代表 sub）:
  1. 既存のデータ purge / owner 引き継ぎ（現行ロジック維持）。
  2. **`account_link` 掃除**: `list_aliases(代表)` で別名一覧 → 各 `delete_account_link(別名)`（逆引きも消える）。
  3. **`EMAIL#` 掃除**: Phase 1 では別名 sub は自前の `EMAIL#` を持たない（auto-link 敗者は claim 失敗で EMAIL# を作らず、移行の別名も同様）。**論理アカウントの `EMAIL#` は代表のメール1件のみ**。代表 membership の `email` について `get_email_primary(email) == 代表` を確認し、一致時のみ `delete_email_primary(email)`（他人の EMAIL# を誤って消さない）。
  4. `delete_membership(代表)`（既存）。
  - 戻り値で**削除対象の全 sub（代表＋別名）と Apple 連携の有無**を呼び出し側（main）に返す（Cognito 削除に使う）。例: `DeletionResult(subs:list[str], apple_linked:bool)`。
- `main.delete_account` ルート（拡張）:
  1. body から `apple_authorization_code`（任意）を受ける。
  2. code があれば `apple_revoke.revoke_apple_for_code(...)`（ベストエフォート・失敗しても続行）。
  3. `result = svc.delete_account(ident.user_id)`。
  4. `result.subs` の各 sub について、Cognito Username を `list_users(Filter='sub="<sub>"')` で引き、`admin_delete_user(Username)`。**JWT sub ≠ Cognito Username（federated は `Provider_id`）なので sub→Username 解決が必須**。見つからない/失敗は警告ログのみ（データは消えている）。
- `apple_linked` の判定は **Cognito を真実源**にする（移行済み別名は `account_link` に provider を持たないため）。新規 `backend/app/cognito_admin.py` に注入可能なヘルパー: `username_for_sub(client, pool_id, sub) -> str|None`（`list_users(Filter='sub="<sub>"')` で Cognito Username を引く）、`is_apple_sub(...) -> bool`（Username が `SignInWithApple` 始まり）、`delete_user_by_sub(client, pool_id, sub)`（Username 解決→`admin_delete_user`）。services は DynamoDB に専念し `account_subs(user_id) -> list[str]`（代表＋`list_aliases`）を提供。`GET /api/account/delete-info` は `account_subs` の各 sub を `is_apple_sub` で判定して `apple_linked` を返す。

### 4.4 インフラ（`infra/cdk`）
- API Lambda の IAM に追加: `secretsmanager:GetSecretValue`（`noshi/social-login` の ARN）、`cognito-idp:ListUsers`（既存の AdminDeleteUser に加えて）。
- backend 依存追加なし: ES256 は既存 `pyjwt[crypto]`。Apple への HTTP は **標準ライブラリ `urllib.request`**（app コードに httpx/requests は無く dev のみのため、prod 依存を増やさない）。テストでは HTTP 関数を注入してモックする。

## 5. データフロー / 不変条件
- Apple のコードは**ワンショット**（交換で消費）。保存しない。
- revoke は refresh_token に対して実行（access_token でも可だが refresh の方が確実）。
- 削除は**冪等寄り**: 二度目の DELETE でも membership 無し→データ無し→Cognito 無しで安全に通る。

## 6. エラーハンドリング
- revoke 失敗（network / Apple 4xx/5xx / code 無効）: ログ（actor/理由）＋**削除は続行**。Apple の「トークンを持たなくても削除を果たせばよい」に合致。
- Apple code 欠落（Web・古いアプリ）: revoke スキップ＋削除続行。
- Cognito `list_users`/`admin_delete_user` 失敗: 警告ログ。データは既に削除済みなのでユーザー影響は限定。
- フロントの Apple シートキャンセル: 削除中止（破壊操作なので安全側）。

## 7. テスト
- `apple_revoke`: `build_client_secret` の JWT 構造（header.kid、iss/sub/aud/exp、ES256 で検証可能）。`exchange_code`/`revoke` は注入 HTTP モックで 2xx/4xx 分岐。`revoke_apple_for_code` が例外時 False（削除ブロックしない）。
- `services.delete_account`: 別名ありユーザーで account_link/EMAIL# が消え、`DeletionResult.subs` に代表＋全別名が入る。owner 引き継ぎ・purge の既存挙動が不変。`account_has_apple` の真偽。
- `main.delete_account`: code ありで revoke 呼び出し（モック）→ 各 sub の admin_delete_user 呼び出し（注入 Cognito クライアントで検証）。code 無しは revoke 未呼び出し。
- **TestFlight 実機**: Apple ログイン→設定→削除→Apple シート再認証→削除完了。Apple ID 設定の「このAppを使用中のApp」から noshi が消えることを確認（revoke 成功の証跡）。

## 8. 受け入れ条件
- [ ] iOS で Apple 連携アカウントを削除すると、Apple シート再認証→Apple トークンが revoke される（実機で「使用中のApp」から消える）。
- [ ] 削除で本人の全 Cognito ユーザー（代表＋別名）と app データ・`account_link`/`EMAIL#` が消え、別ログインで復活しない（恒久削除）。
- [ ] revoke が失敗してもアカウント削除自体は完了する。
- [ ] メール/Google のみのアカウントは従来どおり確認ダイアログのみで削除でき、退行が無い。
- [ ] 削除はアプリ内で開始〜完了（Web 誘導なし）。
- [ ] レビューノート（#212）に削除手順の画面パスを記載できる。
