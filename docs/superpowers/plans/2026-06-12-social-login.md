# Google + LINE ソーシャルログイン実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** ログイン画面に「Google で続ける」「LINE で続ける」を追加し、同一メールのアカウントを安全に自動統合する。

**Architecture:** Cognito User Pool に Google IdP / LINE(OIDC) IdP / ドメインを追加し、フロントは認可コード+PKCE を素の fetch で実装（Hosted UI 画面はスキップ）。Pre-signup Lambda が email_verified ガード付きで既存 native ユーザーへ自動リンク（リンク直後はフロントが1回だけ自動リトライ）。スペック: `docs/superpowers/specs/2026-06-12-social-login-design.md`（**迷ったらスペックが正**）。

**Tech Stack:** Cognito（IdP/Domain/Trigger）/ CDK / Python 3.12（トリガ）/ TypeScript（素の fetch・Web Crypto）

**作業場所:** worktree `/home/inoue-d/dev/noshi/.claude/worktrees/social-login`（ブランチ `feat/social-login`）
**テスト実行:** backend は worktree の backend/ で `/home/inoue-d/dev/noshi/backend/.venv/bin/python -m pytest`。frontend は worktree の frontend/ で `npx vitest run`（node_modules 無ければ `npm ci`）。
**規約:** テスト名は日本語・コメント日本語・mypy strict・pre-commit（ruff/mypy/biome）。コミットに Co-Authored-By 等の署名は付けない。

---

## ファイル構成

```
backend/app/auth_triggers.py            # 新規: Pre-signup トリガ（自動統合）
backend/tests/test_auth_triggers.py     # 新規
infra/cdk/lib/auth-stack.ts             # 変更: Domain/Google/LINE/oAuth/トリガ/CfnOutput
.github/workflows/ci.yml                # 変更: VITE_COGNITO_DOMAIN 注入
frontend/src/lib/cognito.ts             # 変更: PKCE・socialSignIn・handleAuthCallback
frontend/src/lib/cognito.test.ts        # 新規: 純関数テスト
frontend/src/App.tsx                    # 変更: ボタン・起動時 callback 処理
frontend/src/styles.css                 # 変更: ソーシャルボタンの配色
docs/superpowers/specs/...-design.md    # 微修正: authEnabled→socialEnabled の表現（Task 4 で）
```

設計上の注意（整合性レビューの誤りを正す）: CDK の `authFlows` に authorizationCodeGrant という
キーは**存在しない**。OAuth コードグラントは `oAuth.flows.authorizationCodeGrant` で設定する。
既存の `authFlows: { userSrp, userPassword }` はそのまま維持する。

---

### Task 1: Pre-signup トリガ（auth_triggers.py）

**Files:**
- Create: `backend/app/auth_triggers.py`
- Test: `backend/tests/test_auth_triggers.py`

- [ ] **Step 1: 失敗するテストを書く**

```python
"""Pre-signup トリガ（ソーシャルログインの自動統合）のテスト。スペック§4。"""

import pytest

from app.auth_triggers import LINK_RETRY_MESSAGE, presignup_handler


def _event(provider="Google", sub="1234567890", email="user@example.com",
           email_verified="true", trigger="PreSignUp_ExternalProvider"):
    attrs = {"email": email}
    if email_verified is not None:
        attrs["email_verified"] = email_verified
    return {
        "triggerSource": trigger,
        "userPoolId": "ap-northeast-1_TEST",
        "userName": f"{provider}_{sub}",
        "request": {"userAttributes": attrs},
        "response": {},
    }


def _native_user(username="native-1", status="CONFIRMED", verified="true", identities=None):
    attrs = [{"Name": "email", "Value": "user@example.com"},
             {"Name": "email_verified", "Value": verified}]
    if identities is not None:
        attrs.append({"Name": "identities", "Value": identities})
    return {"Username": username, "UserStatus": status, "Attributes": attrs}


class FakeIdp:
    def __init__(self, users=None, link_fails=False):
        self.users = users or []
        self.link_fails = link_fails
        self.linked = []

    def list_users(self, **kw):
        return {"Users": self.users}

    def admin_link_provider_for_user(self, **kw):
        if self.link_fails:
            raise RuntimeError("boom")
        self.linked.append(kw)


def test_通常サインアップは対象外():
    ev = _event(trigger="PreSignUp_SignUp")
    out = presignup_handler(ev, None, client=FakeIdp())
    assert out is ev and out["response"] == {}


def test_メールが無ければ素通し():
    ev = _event(email="")
    out = presignup_handler(ev, None, client=FakeIdp())
    assert out["response"] == {}  # autoConfirm しない → Cognito の email required に委ねる


def test_Googleのメール未検証はリンクせず素通し():
    fake = FakeIdp(users=[_native_user()])
    ev = _event(email_verified="false")
    out = presignup_handler(ev, None, client=fake)
    assert fake.linked == [] and out["response"] == {}


def test_既存ユーザーなしはautoConfirmで新規作成():
    ev = _event()
    out = presignup_handler(ev, None, client=FakeIdp(users=[]))
    assert out["response"]["autoConfirmUser"] is True
    assert out["response"]["autoVerifyEmail"] is True


def test_検証済みnativeが1件ならリンクしてリトライ例外():
    fake = FakeIdp(users=[_native_user()])
    with pytest.raises(Exception, match=LINK_RETRY_MESSAGE):
        presignup_handler(_event(), None, client=fake)
    link = fake.linked[0]
    assert link["DestinationUser"]["ProviderAttributeValue"] == "native-1"
    assert link["SourceUser"]["ProviderName"] == "Google"
    assert link["SourceUser"]["ProviderAttributeValue"] == "1234567890"


def test_LINEはemail_verifiedが無くてもリンクする():
    """LINE は email_verified を返さない（スペック§1の受容リスク）。"""
    fake = FakeIdp(users=[_native_user()])
    with pytest.raises(Exception, match=LINK_RETRY_MESSAGE):
        presignup_handler(_event(provider="LINE", sub="Uabcdef", email_verified=None), None, client=fake)
    assert fake.linked[0]["SourceUser"]["ProviderName"] == "LINE"


def test_リンク対象は検証済みCONFIRMEDのnativeに限る():
    cases = [
        _native_user(status="UNCONFIRMED"),          # 未確認
        _native_user(verified="false"),               # メール未検証
        _native_user(identities="[{...}]"),          # federated（native でない）
    ]
    for user in cases:
        fake = FakeIdp(users=[user])
        out = presignup_handler(_event(), None, client=fake)
        assert fake.linked == [] and out["response"] == {}, user


def test_複数候補は決定不能として素通し():
    fake = FakeIdp(users=[_native_user("a"), _native_user("b")])
    out = presignup_handler(_event(), None, client=fake)
    assert fake.linked == [] and out["response"] == {}


def test_リンク失敗は素通しでログイン継続():
    fake = FakeIdp(users=[_native_user()], link_fails=True)
    out = presignup_handler(_event(), None, client=fake)
    assert out["response"] == {}


def test_引用符入りメールはインジェクション対策で素通し():
    out = presignup_handler(_event(email='a"b@example.com'), None, client=FakeIdp())
    assert out["response"] == {}
```

- [ ] **Step 2: 失敗を確認**

Run: `/home/inoue-d/dev/noshi/backend/.venv/bin/python -m pytest tests/test_auth_triggers.py -q`（backend/ で）
Expected: FAIL（ModuleNotFoundError）

- [ ] **Step 3: 実装**（backend/app/auth_triggers.py）

```python
"""Cognito Pre-signup トリガ。ソーシャルログインのアカウント自動統合（スペック§4）。

PreSignUp_ExternalProvider（Google/LINE の初回ログイン）で、同一メールの
「メール検証済み CONFIRMED な native ユーザー」が1件だけ存在すればリンクする。
リンク成功時は例外でサインアップ試行を中断し、フロントの自動リトライで
リンク済みユーザーとして再ログインさせる（Cognito の仕様上の制約）。

セキュリティ: Google は email_verified=true を必須とする。LINE は email_verified を
返さないため受容リスクとして検証済み扱い（スペック§1）。リンク先を検証済み native に
限定することで、未検証ユーザーへの乗っ取りリンクは双方向とも防ぐ。
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

LINK_RETRY_MESSAGE = "ALREADY_LINKED_RETRY"


def presignup_handler(event: dict[str, Any], context: Any, client: Any = None) -> dict[str, Any]:
    """Lambda エントリポイント。client はテスト用に注入可能（既定は boto3）。"""
    if event.get("triggerSource") != "PreSignUp_ExternalProvider":
        return event

    attrs = event.get("request", {}).get("userAttributes", {})
    email = (attrs.get("email") or "").strip()
    if not email or '"' in email:  # 空 or ListUsers フィルタに安全に渡せない値は素通し
        return event

    # userName は "<ProviderName>_<IdP側sub>" 形式（例: Google_12345 / LINE_Uabc）
    provider, _, source_sub = str(event.get("userName", "")).partition("_")
    if not provider or not source_sub:
        return event

    # Google はメール検証済みのときだけ自動統合の対象（乗っ取り防止・スペック§4-2）
    if provider == "Google" and attrs.get("email_verified") != "true":
        logger.warning("google email not verified; skip auto-link")
        return event

    if client is None:
        import boto3  # 遅延 import（テストは注入）

        client = boto3.client("cognito-idp")
    pool_id = event["userPoolId"]

    natives = _linkable_native_users(client, pool_id, email)
    if len(natives) == 0:
        # 新規ユーザー: メールは IdP 確認済み扱いで作成（確認メールを送らない）
        event.setdefault("response", {})["autoConfirmUser"] = True
        event["response"]["autoVerifyEmail"] = True
        return event
    if len(natives) > 1:
        logger.warning("multiple linkable users for the email; skip auto-link")
        return event

    try:
        client.admin_link_provider_for_user(
            UserPoolId=pool_id,
            DestinationUser={
                "ProviderName": "Cognito",
                "ProviderAttributeValue": natives[0]["Username"],
            },
            SourceUser={
                "ProviderName": provider,
                "ProviderAttributeName": "Cognito_Subject",
                "ProviderAttributeValue": source_sub,
            },
        )
    except Exception:  # noqa: BLE001 リンク失敗時はログイン継続を優先（別アカウント許容）
        logger.exception("admin_link_provider_for_user failed; fall back to separate account")
        return event

    # リンク成功。今回のサインアップ試行は中断し、フロントの自動リトライに委ねる
    raise Exception(LINK_RETRY_MESSAGE)  # noqa: TRY002


def _linkable_native_users(client: Any, pool_id: str, email: str) -> list[dict[str, Any]]:
    """リンク対象: メール一致かつ CONFIRMED・email_verified・native（identities 無し）。"""
    r = client.list_users(UserPoolId=pool_id, Filter=f'email = "{email}"')
    out = []
    for u in r.get("Users", []):
        if u.get("UserStatus") != "CONFIRMED":
            continue
        attr = {a["Name"]: a["Value"] for a in u.get("Attributes", [])}
        if attr.get("email_verified") != "true":
            continue
        if "identities" in attr:  # federated ユーザーはリンク先にしない
            continue
        out.append(u)
    return out
```

- [ ] **Step 4: パスを確認**

Run: `/home/inoue-d/dev/noshi/backend/.venv/bin/python -m pytest tests/test_auth_triggers.py -q`
Expected: 10 passed

- [ ] **Step 5: コミット**

```bash
git add backend/app/auth_triggers.py backend/tests/test_auth_triggers.py
git commit -m "feat(auth): ソーシャルログインの自動統合トリガ（email_verifiedガード付き）"
```

---

### Task 2: CDK — Cognito の IdP・ドメイン・OAuth 設定

**Files:**
- Modify: `infra/cdk/lib/auth-stack.ts`

bin/noshi.ts の変更は不要（AuthStack の props は不変）。

- [ ] **Step 1: import 追加**（auth-stack.ts 先頭）

```typescript
import { Stack, StackProps, Duration, CfnOutput, RemovalPolicy, SecretValue } from "aws-cdk-lib";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as iam from "aws-cdk-lib/aws-iam";
import { backendLambdaCode } from "./lambda-code";
```

（既存の cognito / route53 / ses import は維持）

- [ ] **Step 2: IdP・ドメイン・トリガを追加**

`this.userPool = new cognito.UserPool(...)` と `addDependency(emailIdentity)` の**後**、
既存 `addClient` の**前**に挿入:

```typescript
    // ---- ソーシャルログイン（Google + LINE）。スペック: 2026-06-12-social-login-design.md ----

    // Hosted UI ドメイン（画面は使わず /oauth2/authorize・/oauth2/token のみ利用）。
    // prefix "noshi-me" が取得済みで deploy が失敗する場合は "noshi-app" に変更する（スペック§3）。
    const domain = this.userPool.addDomain("NoshiCognitoDomain", {
      cognitoDomain: { domainPrefix: "noshi-me" },
    });

    // IdP の клиентID/シークレットは Secrets Manager "noshi/social-login"（デプロイ前に手動登録必須）。
    const secretJson = (field: string) =>
      SecretValue.secretsManager("noshi/social-login", { jsonField: field });

    const googleIdp = new cognito.UserPoolIdentityProviderGoogle(this, "GoogleIdp", {
      userPool: this.userPool,
      clientId: secretJson("googleClientId").unsafeUnwrap(),
      clientSecretValue: secretJson("googleClientSecret"),
      scopes: ["openid", "email", "profile"],
      attributeMapping: {
        email: cognito.ProviderAttribute.GOOGLE_EMAIL,
        // email_verified を取り込み、Pre-signup の乗っ取りガードに使う（スペック§4）
        custom: { email_verified: cognito.ProviderAttribute.other("email_verified") },
      },
    });

    // LINE は OIDC 準拠（discovery 自動）。プロバイダ名 "LINE" は cognito.ts の
    // identity_provider と同一文字列で統一（スペック§3）。
    const lineIdp = new cognito.UserPoolIdentityProviderOidc(this, "LineIdp", {
      userPool: this.userPool,
      name: "LINE",
      clientId: secretJson("lineChannelId").unsafeUnwrap(),
      clientSecret: secretJson("lineChannelSecret").unsafeUnwrap(),
      issuerUrl: "https://access.line.me",
      scopes: ["openid", "profile", "email"],
      attributeRequestMethod: cognito.OidcAttributeRequestMethod.GET,
      attributeMapping: { email: cognito.ProviderAttribute.other("email") },
    });

    // 自動統合トリガ（backend/app/auth_triggers.py）。pool_id は event から取るため env 不要
    //（env で pool_id を渡すと UserPool⇔Lambda の循環参照になる）。
    const presignupFn = new lambda.Function(this, "PresignupTrigger", {
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: "app.auth_triggers.presignup_handler",
      code: backendLambdaCode(),
      timeout: Duration.seconds(10),
      memorySize: 256,
    });
    presignupFn.addToRolePolicy(
      new iam.PolicyStatement({
        actions: ["cognito-idp:ListUsers", "cognito-idp:AdminLinkProviderForUser"],
        resources: [this.userPool.userPoolArn],
      }),
    );
    this.userPool.addTrigger(cognito.UserPoolOperation.PRE_SIGN_UP, presignupFn);
```

- [ ] **Step 3: 既存 addClient を OAuth 対応に拡張**

既存の `this.userPoolClient = this.userPool.addClient("NoshiWebClient", {...})` を次に置き換え
（authFlows・有効期限など既存項目は**そのまま**。oAuth と supportedIdentityProviders を追加）:

```typescript
    // SPA 用クライアント（シークレットなし）。既存の SRP/パスワード認証に加え、
    // ソーシャル用の認可コードグラントを有効化。
    // 注意: Cognito は public client でも PKCE を強制しない。フロント実装が常に
    // code_challenge/verifier を付与することで担保する（スペック§3）。
    this.userPoolClient = this.userPool.addClient("NoshiWebClient", {
      userPoolClientName: "noshi-web",
      generateSecret: false,
      authFlows: { userSrp: true, userPassword: true },
      oAuth: {
        flows: { authorizationCodeGrant: true },
        scopes: [cognito.OAuthScope.OPENID, cognito.OAuthScope.EMAIL, cognito.OAuthScope.PROFILE],
        // 本番 origin のみ（localhost を含めない＝コード横取りの足場を作らない。スペック§3）
        callbackUrls: ["https://noshi.me/"],
        logoutUrls: ["https://noshi.me/"],
      },
      supportedIdentityProviders: [
        cognito.UserPoolClientIdentityProvider.COGNITO,
        cognito.UserPoolClientIdentityProvider.GOOGLE,
        cognito.UserPoolClientIdentityProvider.custom("LINE"),
      ],
      idTokenValidity: Duration.hours(1),
      accessTokenValidity: Duration.hours(1),
      refreshTokenValidity: Duration.days(30),
      preventUserExistenceErrors: true,
    });
    // IdP の作成完了後にクライアントを作る（supportedIdentityProviders の参照整合）
    this.userPoolClient.node.addDependency(googleIdp);
    this.userPoolClient.node.addDependency(lineIdp);
```

- [ ] **Step 4: CfnOutput 追加**（既存 Issuer 出力の下）

```typescript
    new CfnOutput(this, "CognitoDomain", { value: domain.baseUrl() });
```

（`baseUrl()` は `https://noshi-me.auth.ap-northeast-1.amazoncognito.com` 形式の完全 URL）

- [ ] **Step 5: 検証・コミット**

Run: `cd infra/cdk && npx tsc --noEmit && npx cdk synth NoshiAuthStack > /dev/null; cd ../..`
Expected: tsc エラーなし（synth は AWS 認証が無ければ tsc のみで可）

```bash
git add infra/cdk/lib/auth-stack.ts
git commit -m "feat(infra): CognitoにGoogle/LINE IdP・ドメイン・自動統合トリガを追加"
```

---

### Task 3: CI — VITE_COGNITO_DOMAIN の注入

**Files:**
- Modify: `.github/workflows/ci.yml`（"build frontend" ステップ）

- [ ] **Step 1: 既存ステップに DOMAIN を追加**

`CLIENT=$(node -p ...UserPoolClientId")` の行の直後に1行、build コマンドに変数を1つ追加:

```yaml
          DOMAIN=$(node -p "require('../infra/cdk/cdk-outputs.json').NoshiAuthStack.CognitoDomain")
          VITE_API_BASE="$API" VITE_COGNITO_CLIENT_ID="$CLIENT" VITE_COGNITO_DOMAIN="$DOMAIN" VITE_AWS_REGION=ap-northeast-1 npm run build
```

（既存の `VITE_API_BASE=...npm run build` 行を上記の置き換え形にする）

- [ ] **Step 2: コミット**

```bash
git add .github/workflows/ci.yml
git commit -m "ci: フロントビルドにVITE_COGNITO_DOMAINを注入"
```

---

### Task 4: フロント — PKCE・socialSignIn・handleAuthCallback（cognito.ts）

**Files:**
- Modify: `frontend/src/lib/cognito.ts`
- Create: `frontend/src/lib/cognito.test.ts`
- Modify: `docs/superpowers/specs/2026-06-12-social-login-design.md`（§5 の「authEnabled は両方非空」を
  「socialEnabled（新設）が両方非空」に修正 — 既存のメール+パスワードを domain 未注入環境でも
  使えるようにするため）

- [ ] **Step 1: 失敗するテストを書く**（frontend/src/lib/cognito.test.ts）

```typescript
import { describe, expect, it } from "vitest";
import { b64url, buildAuthorizeUrl, classifyCallback, pkcePair } from "./cognito";

describe("PKCE", () => {
  it("verifier/challenge は base64url 形式", async () => {
    const { verifier, challenge } = await pkcePair();
    expect(verifier).toMatch(/^[A-Za-z0-9_-]{43}$/); // 32バイト→43文字
    expect(challenge).toMatch(/^[A-Za-z0-9_-]{43}$/); // SHA-256 32バイト→43文字
  });
  it("毎回異なる値を生成する", async () => {
    const a = await pkcePair();
    const b = await pkcePair();
    expect(a.verifier).not.toBe(b.verifier);
  });
  it("b64url はパディングなしで+/を-_に置換する", () => {
    expect(b64url(new Uint8Array([251, 255, 190]))).toBe("-_--");
  });
});

describe("buildAuthorizeUrl", () => {
  it("必須パラメータが全部乗る", () => {
    const url = new URL(
      buildAuthorizeUrl({
        domain: "https://noshi-me.auth.ap-northeast-1.amazoncognito.com",
        clientId: "abc",
        provider: "LINE",
        redirectUri: "https://noshi.me/",
        state: "st",
        challenge: "ch",
      }),
    );
    expect(url.pathname).toBe("/oauth2/authorize");
    expect(url.searchParams.get("identity_provider")).toBe("LINE");
    expect(url.searchParams.get("response_type")).toBe("code");
    expect(url.searchParams.get("client_id")).toBe("abc");
    expect(url.searchParams.get("redirect_uri")).toBe("https://noshi.me/");
    expect(url.searchParams.get("scope")).toBe("openid email profile");
    expect(url.searchParams.get("state")).toBe("st");
    expect(url.searchParams.get("code_challenge")).toBe("ch");
    expect(url.searchParams.get("code_challenge_method")).toBe("S256");
  });
});

describe("classifyCallback（コールバック分岐の純関数）", () => {
  const stored = { state: "st", provider: "Google" as const, retried: false };

  it("codeもerrorも無ければnone", () => {
    expect(classifyCallback(new URLSearchParams(""), stored).kind).toBe("none");
  });
  it("リンク直後のエラーは未リトライならretry", () => {
    const p = new URLSearchParams(
      "error=invalid_request&error_description=PreSignUp+failed+with+error+ALREADY_LINKED_RETRY.",
    );
    const r = classifyCallback(p, stored);
    expect(r.kind).toBe("retry");
    expect(r.kind === "retry" && r.provider).toBe("Google");
  });
  it("リトライ済みならerror", () => {
    const p = new URLSearchParams("error=x&error_description=ALREADY_LINKED_RETRY");
    expect(classifyCallback(p, { ...stored, retried: true }).kind).toBe("error");
  });
  it("別のエラーはリトライしない", () => {
    const p = new URLSearchParams("error=access_denied&error_description=user+cancelled");
    expect(classifyCallback(p, stored).kind).toBe("error");
  });
  it("providerが保存されていなければリトライしない", () => {
    const p = new URLSearchParams("error=x&error_description=ALREADY_LINKED_RETRY");
    expect(classifyCallback(p, { ...stored, provider: null }).kind).toBe("error");
  });
  it("codeありでstate一致ならtoken交換へ", () => {
    const p = new URLSearchParams("code=abc&state=st");
    const r = classifyCallback(p, stored);
    expect(r.kind).toBe("token");
    expect(r.kind === "token" && r.code).toBe("abc");
  });
  it("state不一致はerror（CSRF対策）", () => {
    const p = new URLSearchParams("code=abc&state=evil");
    expect(classifyCallback(p, stored).kind).toBe("error");
  });
});
```

- [ ] **Step 2: 失敗を確認**

Run（frontend/ で）: `npx vitest run src/lib/cognito.test.ts`
Expected: FAIL（export が無い）

- [ ] **Step 3: 実装（cognito.ts に追記）**

ファイル冒頭の定数群（TOKEN_KEY の下）に追加:

```typescript
const DOMAIN = (import.meta.env.VITE_COGNITO_DOMAIN ?? "").replace(/\/$/, "");
// sessionStorage キー（スペック§5で確定）
const VERIFIER_KEY = "noshi_pkce_verifier";
const STATE_KEY = "noshi_oauth_state";
const PROVIDER_KEY = "noshi_oauth_provider";
const RETRY_KEY = "noshi_oauth_retry";

export type SocialProvider = "Google" | "LINE";

/** ソーシャルログインが使えるか（Cognito ドメイン未注入のローカルではボタン非表示）。 */
export function socialEnabled(): boolean {
  return authEnabled() && DOMAIN.length > 0;
}
```

ファイル末尾に追加:

```typescript
// ---- ソーシャルログイン（認可コード + PKCE・依存ゼロ）。スペック§5 ----

/** バイト列を base64url（パディングなし）に。 */
export function b64url(bytes: Uint8Array): string {
  return btoa(String.fromCharCode(...bytes))
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");
}

/** PKCE の verifier と challenge（S256）を生成する。 */
export async function pkcePair(): Promise<{ verifier: string; challenge: string }> {
  const verifier = b64url(crypto.getRandomValues(new Uint8Array(32)));
  const digest = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(verifier));
  return { verifier, challenge: b64url(new Uint8Array(digest)) };
}

export function buildAuthorizeUrl(p: {
  domain: string;
  clientId: string;
  provider: SocialProvider;
  redirectUri: string;
  state: string;
  challenge: string;
}): string {
  const q = new URLSearchParams({
    identity_provider: p.provider,
    response_type: "code",
    client_id: p.clientId,
    redirect_uri: p.redirectUri,
    scope: "openid email profile",
    state: p.state,
    code_challenge: p.challenge,
    code_challenge_method: "S256",
  });
  return `${p.domain}/oauth2/authorize?${q.toString()}`;
}

/** Google/LINE の認証画面へリダイレクトする（Hosted UI はスキップ）。 */
export async function socialSignIn(provider: SocialProvider): Promise<void> {
  const { verifier, challenge } = await pkcePair();
  const state = b64url(crypto.getRandomValues(new Uint8Array(16)));
  sessionStorage.setItem(VERIFIER_KEY, verifier);
  sessionStorage.setItem(STATE_KEY, state);
  sessionStorage.setItem(PROVIDER_KEY, provider);
  location.href = buildAuthorizeUrl({
    domain: DOMAIN,
    clientId: CLIENT_ID,
    provider,
    redirectUri: `${location.origin}/`,
    state,
    challenge,
  });
}

export type CallbackResult = "ok" | "retry" | "error" | "none";

type CallbackClass =
  | { kind: "none" }
  | { kind: "retry"; provider: SocialProvider }
  | { kind: "token"; code: string }
  | { kind: "error" };

/** コールバック URL の分岐判定（純関数・テスト対象）。 */
export function classifyCallback(
  params: URLSearchParams,
  stored: { state: string | null; provider: SocialProvider | null; retried: boolean },
): CallbackClass {
  const code = params.get("code");
  const error = params.get("error");
  if (!code && !error) return { kind: "none" };
  if (error) {
    const desc = params.get("error_description") ?? "";
    // Pre-signup の自動統合直後だけ1回リトライ（スペック§4/§5）。provider は保存値のみ信用
    if (desc.includes("ALREADY_LINKED_RETRY") && !stored.retried && stored.provider) {
      return { kind: "retry", provider: stored.provider };
    }
    return { kind: "error" };
  }
  const state = params.get("state");
  if (!state || !stored.state || state !== stored.state) return { kind: "error" }; // CSRF対策
  return { kind: "token", code: code as string };
}

/** アプリ起動時に1回呼ぶ。URL の code/error を処理して結果を返す（スペック§5）。 */
export async function handleAuthCallback(): Promise<CallbackResult> {
  const params = new URLSearchParams(location.search);
  const cls = classifyCallback(params, {
    state: sessionStorage.getItem(STATE_KEY),
    provider: sessionStorage.getItem(PROVIDER_KEY) as SocialProvider | null,
    retried: sessionStorage.getItem(RETRY_KEY) === "1",
  });
  if (cls.kind === "none") return "none";

  const stripUrl = () => history.replaceState(null, "", location.pathname);
  const cleanup = () => {
    for (const k of [VERIFIER_KEY, STATE_KEY, PROVIDER_KEY, RETRY_KEY]) sessionStorage.removeItem(k);
    stripUrl();
  };

  if (cls.kind === "retry") {
    sessionStorage.setItem(RETRY_KEY, "1");
    stripUrl();
    await socialSignIn(cls.provider); // 新しい verifier/state で再認可（RETRY_KEY は残す）
    return "retry";
  }
  if (cls.kind === "error") {
    cleanup();
    return "error";
  }

  const verifier = sessionStorage.getItem(VERIFIER_KEY) ?? "";
  if (!verifier) {
    cleanup();
    return "error";
  }
  try {
    const res = await fetch(`${DOMAIN}/oauth2/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: new URLSearchParams({
        grant_type: "authorization_code",
        client_id: CLIENT_ID,
        code: cls.code,
        redirect_uri: `${location.origin}/`,
        code_verifier: verifier, // PKCE: verifier 無しの交換経路は作らない（スペック§3）
      }),
    });
    const data = (await res.json().catch(() => ({}))) as { id_token?: string };
    if (!res.ok || !data.id_token) {
      cleanup();
      return "error";
    }
    localStorage.setItem(TOKEN_KEY, data.id_token);
    cleanup();
    return "ok";
  } catch {
    cleanup();
    return "error";
  }
}
```

スペック修正（同コミットに含める・2箇所）:
1. §5「`authEnabled()` は CLIENT_ID と DOMAIN の両方が非空のとき true」→
   「新設の `socialEnabled()` が CLIENT_ID と DOMAIN の両方が非空のとき true（authEnabled は
   従来どおり CLIENT_ID のみ。メール+パスワードは domain 未注入環境でも使える）」
2. §6 の state 不一致の文面を「ログインに失敗しました。もう一度お試しください。」に統一
   （classifyCallback はエラー理由を区別せず "error" を返すため、フロントの表示文言は1種類。
   CSRF 疑いをユーザーに伝える意義も薄い）

- [ ] **Step 4: パスを確認**

Run: `npx vitest run src/lib/cognito.test.ts` → 11 passed
Run: `npx vitest run && npx tsc --noEmit` → 全パス

- [ ] **Step 5: コミット**

```bash
git add frontend/src/lib/cognito.ts frontend/src/lib/cognito.test.ts docs/superpowers/specs/2026-06-12-social-login-design.md
git commit -m "feat(frontend): PKCE付きソーシャルログインのコア処理（依存ゼロ）"
```

---

### Task 5: フロント — ログイン画面のボタンと起動時コールバック処理

**Files:**
- Modify: `frontend/src/App.tsx`
- Modify: `frontend/src/styles.css`

- [ ] **Step 1: import 追加**（App.tsx の lib/cognito import 群に）

`socialEnabled, socialSignIn, handleAuthCallback` を既存の cognito import に追加する。

- [ ] **Step 2: 起動時コールバック処理**

App コンポーネント内、既存の `notify` 定義（App.tsx:165 付近）より後の useEffect 群に追加。
**実装前に `doSignIn` 成功後の遷移処理を読み、"ok" の遷移をそれと同一にすること**
（go("home") ＋データ読み込みの呼び方を合わせる）:

```tsx
  // ソーシャルログインのコールバック処理（URL に ?code= / ?error= があるときだけ動く）
  useEffect(() => {
    if (!socialEnabled()) return;
    void handleAuthCallback().then((r) => {
      if (r === "ok") {
        // doSignIn 成功後と同じ遷移（実装時に doSignIn を参照して合わせる）
        go("home");
      } else if (r === "retry") {
        notify("アカウントを連携しました。続けてログインします…");
      } else if (r === "error") {
        setScreen("login");
        notify("ログインに失敗しました。もう一度お試しください。");
      }
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
```

- [ ] **Step 3: ログイン画面にボタン追加**

App.tsx の login 画面（740行付近）、`authEnabled()` が true の分岐のカード内・
メールアドレス field の**前**に挿入（signin モードのときだけ表示）:

```tsx
              {socialEnabled() && authMode === "signin" && (
                <>
                  <button
                    type="button"
                    className="btn social-google"
                    onClick={() => void socialSignIn("Google")}
                  >
                    <svg width="18" height="18" viewBox="0 0 18 18" aria-hidden="true">
                      <path fill="#4285F4" d="M17.64 9.2c0-.64-.06-1.25-.16-1.84H9v3.48h4.84a4.14 4.14 0 0 1-1.8 2.72v2.26h2.92c1.7-1.57 2.68-3.88 2.68-6.62z"/>
                      <path fill="#34A853" d="M9 18c2.43 0 4.47-.8 5.96-2.18l-2.92-2.26c-.8.54-1.84.86-3.04.86-2.34 0-4.32-1.58-5.03-3.7H.96v2.33A9 9 0 0 0 9 18z"/>
                      <path fill="#FBBC05" d="M3.97 10.72a5.41 5.41 0 0 1 0-3.44V4.95H.96a9 9 0 0 0 0 8.1l3.01-2.33z"/>
                      <path fill="#EA4335" d="M9 3.58c1.32 0 2.5.45 3.44 1.35l2.58-2.59A9 9 0 0 0 .96 4.95l3.01 2.33C4.68 5.16 6.66 3.58 9 3.58z"/>
                    </svg>
                    Google で続ける
                  </button>
                  <button
                    type="button"
                    className="btn social-line"
                    onClick={() => void socialSignIn("LINE")}
                  >
                    LINE で続ける
                  </button>
                  <div className="muted" style={{ textAlign: "center", margin: "10px 0 2px" }}>
                    または
                  </div>
                </>
              )}
```

- [ ] **Step 4: styles.css にボタン配色を追加**（既存 `.btn.danger` 定義の下）

```css
/* ---- ソーシャルログイン（各社ブランドガイドライン準拠の配色） ------------ */
.btn.social-google {
  background: #fff;
  color: #3c4043;
  border-color: var(--border-default);
}
.btn.social-line {
  background: #06c755; /* LINE ブランドカラー（規定値） */
  color: #fff;
}
.btn.social-line:active {
  background: #05b34c;
}
```

- [ ] **Step 5: テストとビルド確認**

Run（frontend/ で）: `npx vitest run && npx tsc --noEmit && npx biome check src/`
Expected: 全パス

- [ ] **Step 6: コミット**

```bash
git add frontend/src/App.tsx frontend/src/styles.css
git commit -m "feat(frontend): ログイン画面にGoogle/LINEボタンと起動時コールバック処理"
```

---

### Task 6: 仕上げ（全テスト・PR）

- [ ] **Step 1: 全テスト**

```bash
cd backend && /home/inoue-d/dev/noshi/backend/.venv/bin/python -m pytest -q
cd ../frontend && npx vitest run && npx tsc --noEmit && npx biome check src/
cd ../infra/cdk && npx tsc --noEmit
```
Expected: 全パス

- [ ] **Step 2: スペック突き合わせ**

スペック §3〜§8 を読み直し、§8 テスト戦略（フロント純関数・Lambda・CDK）の実装漏れがないか確認。

- [ ] **Step 3: PR 作成**

```bash
git push -u origin feat/social-login
gh pr create --title "feat: Google + LINE ソーシャルログイン" --body "..."
```

PR 本文に必ず書く: **マージ＝デプロイの前に Task 7（手動準備）が必須**であること
（Secrets Manager 未登録だと NoshiAuthStack のデプロイが失敗する）。

---

### Task 7: 手動準備（ユーザー作業・デプロイ前に必須）

コードではなく運用手順。**PR マージより前に 1〜4 を完了すること**（CDK がシークレットを参照するため）。

- [ ] **Step 1: Cognito ドメイン prefix の空き確認**

```bash
aws cognito-idp describe-user-pool-domain --domain noshi-me --region ap-northeast-1
```
`DomainDescription` が空（{}）なら空き。使用中なら auth-stack.ts の prefix を "noshi-app" に変更。

- [ ] **Step 2: Google Cloud Console**

OAuth クライアント ID（種類: ウェブアプリケーション）を作成。
- 承認済みの JavaScript 生成元: `https://noshi-me.auth.ap-northeast-1.amazoncognito.com`
- 承認済みのリダイレクト URI: `https://noshi-me.auth.ap-northeast-1.amazoncognito.com/oauth2/idpresponse`

- [ ] **Step 3: LINE Developers**

LINE ログインのチャネル作成（アプリタイプ: ウェブアプリ）。
- コールバック URL: `https://noshi-me.auth.ap-northeast-1.amazoncognito.com/oauth2/idpresponse`
- **「メールアドレス取得権限」を申請**（チャネル基本設定 → OpenID Connect → メールアドレス取得。
  利用目的とプライバシーポリシー URL を記入）。承認されるまで LINE ログインはエラーになる

- [ ] **Step 4: Secrets Manager 登録**

```bash
aws secretsmanager create-secret --region ap-northeast-1 --name noshi/social-login \
  --secret-string '{"googleClientId":"<...>","googleClientSecret":"<...>","lineChannelId":"<...>","lineChannelSecret":"<...>"}'
```

- [ ] **Step 5: マージ→デプロイ後の結合確認**

1. Google でログイン → 記録作成 → ログアウト → 同メールのパスワードログインで同一データが
   見えること（自動統合）
2. LINE でログイン（メール権限承認後）
3. Google 未検証メール相当の確認は省略可（実環境で作りにくいため。Lambda ユニットで担保済み）
