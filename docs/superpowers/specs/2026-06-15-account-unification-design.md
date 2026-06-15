# アカウント統合（account unification）設計

- 日付: 2026-06-15
- 関連: #204（Sign in with Apple）, #198（アカウント削除）, #192(Epic), 2026-06-12-social-login-design.md
- ステータス: 設計（3エージェントのレビュー反映済み・条件付き承認の条件を織り込み）

## 1. 背景と問題

noshi の認証は Amazon Cognito User Pool。バックエンドは JWT の `sub`（不変のユーザー識別子）でユーザーを識別し、DynamoDB テーブル `noshi` 上で **世帯（household）単位**にデータをスコープする（`backend/app/auth.py`・`backend/app/services.py: resolve_household`）。

`resolve_household(user_id)` は、その `sub` に membership が無ければ**新しい世帯を自動作成**する。したがって **同一人物が複数のログイン手段（メール/パスワード・Google・Apple）を使うと、それぞれ別の `sub` になり別世帯に分裂**し、ログイン手段ごとに違うデータが見える。

### 実測された分裂（開発者本人）
| ログイン手段 | JWT sub | 世帯 | 役割 | 中身 |
|---|---|---|---|---|
| Google | `<dev-google-sub>` | `<shared-household-id>` | owner | **RECORD×3 / EVENT×3 / JOB×1（本物）。配偶者が member** |
| メール/パスワード | `<dev-email-sub>` | `<email-household-id>` | owner | 空 |
| Apple（非公開, email_verified=false） | `<dev-apple-sub>` | `<apple-household-id>` | owner | 空 |

→ 実データと配偶者は Google 世帯 `<shared-household-id>` にあり、メール/Apple は空世帯に隔離されている。

### 既存の自動リンクが取りこぼした理由
`backend/app/auth_triggers.py` の Cognito pre-signup は「federated 初回ログイン時に、同一の検証済みメールを持つ CONFIRMED native ユーザーへ `AdminLinkProviderForUser` でリンク」する片方向の仕組み。作成順が Google(先) → native(後) だったため、Google ログイン時にリンク先 native が存在せず単独世帯になった。pre-signup は federated→native の一方向・初回のみで、逆順や Apple 非公開（relay メールで突合不能）を救えない。

## 2. ゴールと非ゴール

### ゴール
- **1人＝1アカウント**：ログイン手段に依存せず同一人物が同じ世帯・同じデータに解決される。
- 将来の分裂を**予防**（自動）し、突合できないケース（Apple 非公開・LINE）は**安全な手動連携**で繋ぐ。
- 開発者本人の既存分裂を、配偶者と実データを壊さず**ワンオフで解消**。

### 非ゴール（YAGNI）
- 一般ユーザー向けの汎用「アカウント統合 UI でデータをマージ」機能（一般ユーザーはまだ居ない）。既存分裂の解消は開発者本人のワンオフのみ。
- 非空世帯どうしの自動マージ（重複排除を伴う複雑処理）。手動連携では「連携先が非空ならエラー」で安全側に倒す。

## 3. 方式の選定

| 案 | 概要 | 判定 |
|---|---|---|
| A: Cognito ネイティブ集約 | 全 provider を `AdminLinkProviderForUser` で1ユーザーに集約 | Apple 非公開・federated 同士を救えない。Cognito 制約に縛られる。**不採用（手動連携の補助としてのみ言及）** |
| **B: アプリ層エイリアス** | backend に `sub→代表sub` のエイリアス層 | 全 provider 組合せに対応・既存設計への追加が小さい・連携導線が安全。**採用** |
| C: ハイブリッド | 検証済みメールは Cognito、他はアプリ層 | 2系統混在で整合困難。**不採用** |

**採用＝案B（アプリ層エイリアス）。** Cognito 旧 pre-signup 自動リンクは撤去し、アプリ層の1系統に統一する。

## 4. アーキテクチャ

### 4.1 用語と不変条件
- **代表 sub（canonical sub）**：論理アカウントの主 sub。世帯 membership は代表 sub のみが保持する。
- **別名 sub（alias sub）**：同一人物の別ログイン。`account_link` で代表に張られる。
- 不変条件:
  - I1. 別名 sub は membership を持たない（連携確定時に削除）。世帯メンバーは代表 sub だけ。
  - I2. 代表 sub は自身が別名でない（`account_link` を持たない）。
  - I3. `account_link` の指す先は常に**終端の代表**（chain compression：作成時に解決して終端を書く）。これにより解決は1ホップで足りる。
  - I4. 1つの検証済みメールに対して代表は1つ（`EMAIL#` ユニーク制約）。

### 4.2 DynamoDB 追加アイテム
テーブル `noshi`（既存スキーマに追加）:
- **エイリアス**：`PK=USER#<alias_sub>`, `SK=ACCOUNT_LINK`, 値 `{primary_sub, source_provider, source_email, linked_at, linked_by}`。
- **逆引き（代表→別名）**：`PK=PRIMARY#<primary_sub>`, `SK=ALIAS#<alias_sub>`。削除時の掃除に使う。
- **メール→代表ユニーク**：`PK=EMAIL#<検証済みメール小文字>`, `SK=PRIMARY`, 値 `{primary_sub}`。`attribute_not_exists` の条件付き put でアトミックに確保（同時初回ログインの分裂防止）。

### 4.3 sub 正規化は「リクエスト境界で1回」
`backend/app/main.py: current_identity` で、生 sub をエイリアス解決して**代表 sub に正規化した `Identity`** を1つ作る。以降の全サービス呼び出し（`delete_account`/`leave_household`/`notification_prefs`/`remove_member`/`household_members`/監査 actor 含む）は代表 sub だけを見る。
- 「メソッドごとに解決し忘れる」クラスのバグを構造的に排除する。
- 物理的にどの sub でログインしたか残したい場合は `Identity` に `raw_user_id` を別フィールドで併記（型で代表/生を区別）。
- リクエスト内で解決は1回（read 増を最小化）。

`Identity`（`backend/app/auth.py`）拡張:
- `user_id`（= 代表 sub）, `raw_user_id`（= 生 sub）, `email`, `email_verified: bool`。
- `decode_identity` で `email_verified`（id_token クレーム）を取得する。
- **link/自動リンク経路は id_token のみ受理**（`token_use=="id"` を強制）。access token には email が無いため、通常 API のみ access を許可。

### 4.4 解決順序（`resolve_household` / 正規化ロジック）
membership 取得前に、生 sub に対し以下の順で解決:
1. `account_link` があれば代表 sub に置換（1ホップ・I3 により終端）。
2. 代表 sub の membership があればその世帯を返す（現行どおり）。**この時点で `email_verified=true` かつ自分のメールの `EMAIL#` が未登録なら、自己修復 backfill として `EMAIL#<メール> → 自分(=代表)` を条件付き put**（既存ユーザーも将来の別ログインで自動統合可能にする）。
3. membership が無い初回 sub の場合のみ **自動リンク判定**（4.5）。
4. 自動リンクも不成立（メール未検証 等）なら、現行どおり新規世帯を作成。

### 4.5 自動リンク（ログイン時・予防）
**`email_verified=true` の provider（Google・メール/パスワード）のみが対象**。LINE・Apple 非公開（`email_verified=false`）は対象外＝手動連携のみ。

初回 sub（membership 無し）かつ `email_verified=true` のとき、**`EMAIL#<メール小文字>` への条件付き put（`attribute_not_exists`）一発で「代表確保」と「既存代表への合流」をアトミックに分岐**する:
- **put 成功** → このメールの代表は自分。→ §4.4 step4 に進み**新規世帯を作成**（自分が代表）。
- **put 失敗（既に存在）** → 既存代表 `primary_sub` を読み出し、`account_link(生sub → primary_sub)` ＋逆引き `PRIMARY#` を条件付きで作成。**新規世帯は作らない**。

これにより:
- `EMAIL#` は SK=PRIMARY で構造上 **0/1 件**。「複数一致」は起こり得ず、**同時初回ログインの競合も条件付き put の勝者1人で決まり分裂しない**。
- データソースは DynamoDB の `EMAIL#`（Cognito `list_users` の60件上限・eventual consistency に非依存）。
- 既存 membership を持つ sub は**絶対に再エイリアスしない**（step2 で確定済み）。判定不能・書き込み競合敗者は **fail-closed**（新規世帯＝手動連携へ誘導）。
- 自動リンク発生時はユーザーに通知（「○○と△△のログインを1つのアカウントに統合しました」）。

### 4.6 手動連携導線（Apple 非公開・LINE の本命）
ログイン後の設定画面「連携済みアカウント」。「Apple を連携 / Google を連携 / …」ボタン。

**セキュリティ要件（最重要）**: client が連携先トークンを運ぶ方式は採らない（盗んだ id_token での乗っ取りを防ぐ）。**backend 起点の OAuth 往復**にする:
1. `POST /api/account/link/start`（代表トークンで認証）→ backend が短命・単回の `state`（代表 sub にバインド・サーバ保管）と PKCE を生成し、Hosted UI authorize URL（`identity_provider=<連携先>`）を返す。
2. フロントは既存の OAuth フローでそれを開く（iOS は Browser、Web はリダイレクト）。
3. コールバックの `code`+`state` を `POST /api/account/link/complete` で backend に渡す。**backend が** PKCE で token 交換し連携先 id_token を取得（client は連携先トークンに触れない）。
4. backend は `state` の単回・短命・代表バインドを検証 → 連携先 sub を取り出す。
5. 不変条件チェック（条件付き書き込み）:
   - 連携先 sub が既存の別代表のエイリアスでない（I3）。
   - 連携先 sub の世帯が**空**である（非空なら 409 衝突を返し、サイレントにデータを失わない）。
   - 代表（呼び出し元）が自身エイリアスでない（I2）。
6. `account_link(連携先sub → 代表sub)` ＋逆引き `PRIMARY#` を作成。連携先の空世帯（`HOUSEHOLD#…/META` ＋ `INVITE#<code>/INVITE` ＋ `HOUSEHOLD#…/MEMBER#<sub>` ＋ `USER#<sub>/MEMBERSHIP`）を削除。
7. **連携先が検証済みメールの `EMAIL#` を持っていた場合（例: 別メールの Google）は、その `EMAIL#<連携先メール>` を代表 sub に張り替える**（I3 維持。放置すると EMAIL# が別名を指し、そのメールでの将来ログインが壊れる）。Apple 非公開は `EMAIL#` を持たないため不要。
- セキュリティ根拠: 「代表として認証済み」＋「連携先の OAuth を backend 主導で完了」＝両方の所有を能動的に証明。リプレイ・トークン取り違え・出所詐称を防ぐ。
- 監査に `link_account` を記録。

### 4.7 旧 Cognito 自動リンクの撤去（順序厳守）
1. backend にエイリアス解決＋手動連携を追加しデプロイ。
2. フロントに連携導線を追加。
3. 動作確認後、`auth-stack.ts` の `PresignupTrigger` をトリガから外し Lambda と `ListUsers`/`AdminLinkProviderForUser` IAM を削除。
4. フロントの `ALREADY_LINKED_RETRY` retry（`cognito.ts` の RETRY_KEY・classifyCallback の retry 分岐）を削除（死にコード化を防ぐ）。
- 注意: pre-signup の `autoConfirmUser`/`autoVerifyEmail`（新規 federated の確認/検証付与）が消える。撤去前に「新規 federated ユーザーが確認メールでブロックされない」ことを検証する。

### 4.8 アカウント削除（#198）との整合
`delete_account` を**論理アカウント（代表＋全別名）単位**に再定義:
1. 入口で代表 sub に正規化。
2. 世帯データの purge / owner 継承を代表 sub で実行。
3. `PRIMARY#<代表>` の全エイリアスを列挙し `account_link` と逆引きを削除。さらに**代表 sub を指す全 `EMAIL#` エントリ**（代表自身のメール＋連携時に張り替えた分）を削除し、メールを解放する。
4. Cognito は代表＋全リンク identity を削除（`admin_delete_user`）。
- **Apple revoke（別トラック・#198 のブロッカー）**: Sign in with Apple 利用アプリは App Store 5.1.1(v) によりアカウント削除時に Apple トークン失効が必須。サインイン時に Apple の refresh token を受け取り保存し、削除時に client_secret(JWT) を生成して `https://appleid.apple.com/auth/revoke` を呼ぶ追加設計が要る。**本設計とは独立に #198 で対応**（解消まで App Store 提出不可）。

## 5. ワンオフ移行（開発者本人のみ）

スクリプト `scripts/migrate-account-links.py`（読み取り→dry-run→`--apply`）。

### 事前確認
- 全 Cognito ユーザーの `identities` 属性をダンプし、**既存の Cognito レベルのリンク残存が無い**ことを確認（残っていればエイリアス方式と競合するため個別判断）。

### 操作内容
- `account_link(<dev-email-sub> → <dev-google-sub>)`、`account_link(<dev-apple-sub> → <dev-google-sub>)` ＋逆引き＋`EMAIL#<本人メール>→<dev-google-sub>` を作成。
- 空世帯 `<email-household-id>`・`<apple-household-id>` を畳む（`META`＋`INVITE#`＋`MEMBER#`＋`MEMBERSHIP` を両キー削除）。
- email 空の謎の owner 世帯（`<other-household-id>` 等）は**今回のスコープ外**（触らない）。

### 必須ガード
1. `--apply` 無しは dry-run（副作用ゼロ・削除予定キーと作成予定を全件出力）。
2. 削除対象 sub は**厳密ホワイトリスト** `{<dev-email-sub>, <dev-apple-sub>}` のみ。前方一致削除は禁止。
3. 代表世帯 `<shared-household-id>` または配偶者 sub が削除集合に含まれたら**即 abort**（assert）。
4. 空世帯を消す前に配下 `RECORD#/EVENT#/JOB#/PARTY#/REL#/PUR#` が**0件**と確認。1件でもあれば中断。
5. membership 削除は `USER#…/MEMBERSHIP` と `HOUSEHOLD#…/MEMBER#…` の両面。
6. 世帯削除は `HOUSEHOLD#…/META` と `INVITE#<code>/INVITE`（code は META から取得）の両方。
7. 作成前に代表 `<dev-google-sub>` の membership と世帯 `<shared-household-id>` META の実在を確認。
8. 実行直前に影響範囲全件を JSON バックアップ＋テーブルの PITR 有効化＋on-demand backup を1本。
9. 冪等（再実行安全・条件付き書き込み）。
10. エイリアス target が自身エイリアスでないこと（多段防止）を assert。
11. 監査は削除せず保全。統合操作自体を新規 AUDIT に記録。

## 6. コンポーネント分割（単一責任・テスタビリティ）

- **`account_links` リポジトリ**（`repository.py`）: `get_link/put_link(条件付き)/delete_link/list_aliases/get_email_primary/put_email_primary(条件付き)`。InMemory 実装も用意。
- **正規化純関数**（`services.py` or 新 `account.py`）: `canonical_sub(raw_sub) -> sub`（link 1引きのみ）。
- **自動リンク判定**（`services.py`）: `resolve_household` 内の初回分岐に組込み（4.4/4.5）。Cognito 非依存（`EMAIL#` を引く）。
- **link エンドポイント**（`main.py`）: `/api/account/link/start`・`/api/account/link/complete`・`GET /api/account/links`（連携済み一覧）。**連携解除（unlink）は MVP 非対象**（`EMAIL#` の戻し・解除後の世帯再付与が非自明でユーザー要望も無いため将来 Issue 化）。
- **フロント**（`cognito.ts`/設定画面）: 連携モードの OAuth 起動とコールバック、連携済み一覧 UI。
- **移行スクリプト**（`scripts/`）: 上記 `account_links` リポジトリ層を再利用。

## 7. エラーハンドリング
- 連携先が非空世帯: 409（「先にその世帯から退出してください」等のメッセージ）。
- 自動リンクの複数一致/判定不能: 新規世帯（fail-closed）＋手動連携を案内。
- `state` 不一致/期限切れ/再利用: 401/400 で拒否、監査に `authz_denied`。
- access token で link/自動を試行: 拒否（id_token 必須）。

## 8. テスト
- 純ロジック（InMemoryRepository）: `canonical_sub` 1ホップ解決、解決順序（alias→membership→自動→新規）、自動リンクのガード（email_verified 必須・既存membership再リンク禁止）、**`EMAIL#` 条件付き put による「代表確保 vs 既存合流」分岐**、**同時初回ログインで勝者1人に収束し分裂しない**、**検証済みメールユーザーの `EMAIL#` 自己修復 backfill**、`household_members` の代表のみ表示/dedupe、`delete_account` の論理アカウント単位削除＋代表を指す全 `EMAIL#` 解放。
- link エンドポイント: 正常（空世帯連携）、衝突（非空＝409）、未検証メール、state 単回/期限切れ、id_token 強制、**連携先の `EMAIL#` が代表へ張り替わる**。
- 移行スクリプト: dry-run 出力、ホワイトリスト外 abort、非空世帯 abort、冪等再実行。
- テスト名は日本語一文（例「別名 sub でログインしても代表世帯の台帳が見える」）。

## 9. フェーズ計画
- **Phase 1**：境界正規化＋エイリアス解決＋自動リンク（Google/メール限定）＋`EMAIL#` ユニーク＋ガード付きワンオフ移行。→ 開発者本人の「同じデータが見えない」が解消。
- **Phase 2**：手動連携導線（backend 起点 OAuth・設定画面・連携一覧/解除）。Apple 非公開・LINE を統合可能に。
- **Phase 3（並行・別Issue #198）**：Apple トークン revoke を削除フローに実装（App Store 提出ブロッカー）。Phase 1 後に旧 pre-signup 撤去（4.7）。

## 10. 受け入れ条件
- [ ] 同一人物がメール/Google/Apple のどれでログインしても同じ世帯・同じ台帳が見える。
- [ ] 検証済みメール一致（Google/メール）は自動で1アカウントに収束。同時初回ログインでも分裂しない。
- [ ] Apple 非公開・LINE は手動連携で代表に統合できる。連携は backend 起点 OAuth で、client は連携先トークンを運ばない。
- [ ] link/自動リンクは id_token のみ・email_verified 必須。エイリアスはアトミックで、サイクル/連鎖/二重リンク/既存membership再リンクが起きない。
- [ ] `delete_account` が代表＋全別名を論理1アカウントとして削除し、孤児エイリアスを残さない。
- [ ] ワンオフ移行で配偶者と実データが一切変化しない（dry-run とバックアップで検証）。
- [ ] 旧 pre-signup と ALREADY_LINKED_RETRY が撤去され、退行が無い。
- [ ] （#198）Apple 連携ユーザーの削除で Apple トークンが revoke される。
