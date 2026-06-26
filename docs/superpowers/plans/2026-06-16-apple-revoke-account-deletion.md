# アカウント削除に Apple revoke（論理アカウント単位）実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** アカウント削除時に Apple トークンを `/auth/revoke` で失効させ、削除を論理アカウント（代表＋全別名）単位の恒久削除にする（#198 / App Store 5.1.1(v)）。

**Architecture:** 削除時にネイティブ Sign in with Apple で authorization code を取得 → backend が Apple とコード交換 → revoke（ベストエフォート）。削除は DynamoDB データ purge ＋ `account_link`/`EMAIL#` 掃除（services）＋ 全 Cognito ユーザー削除（cognito_admin）。Apple/Cognito の外部呼び出しは関数注入またはモジュール monkeypatch でテスト。

**Tech Stack:** Python 3.12 / FastAPI / boto3 / pyjwt[crypto]（ES256・追加なし）/ 標準 urllib / React+Vite / `@capacitor-community/apple-sign-in` / AWS CDK。spec: `docs/superpowers/specs/2026-06-16-apple-revoke-account-deletion-design.md`（迷ったら spec が正）。

**検証ゲート（主張前に必ず）:** backend は `cd backend && .venv/bin/python -m pytest <該当> -q` ＋ push 前に **`ruff check .`・`ruff format --check .`・`mypy`** も。コミットは `--no-verify`。frontend の vitest はサンドボックスで exit 216 → CI。iOS ネイティブ（Apple シート・entitlement）は TestFlight 実機。

---

## ファイル構成
- `backend/app/apple_revoke.py`（新規）— Apple client_secret 生成・code交換・revoke。
- `backend/app/cognito_admin.py`（新規）— sub→Username 解決・Apple判定・ユーザー削除。
- `backend/app/services.py`（変更）— `delete_account` を論理削除化＋戻り値 subs、`account_subs` 追加。
- `backend/app/schemas.py`（変更）— `DeleteAccountIn` 追加。
- `backend/app/main.py`（変更）— `GET /api/account/delete-info`、`DELETE /api/account` 拡張。
- `frontend/src/api.ts`（変更）— `deleteAccount(opts?)`・`getDeleteInfo()`。
- `frontend/src/App.tsx`（変更）— 削除フローに Apple 再認証。
- `frontend/package.json`（変更）— `@capacitor-community/apple-sign-in` 追加。
- `infra/cdk/lib/api-stack.ts`（変更）— IAM（ListUsers・SecretsManager）。
- `scripts/ios-configure-plist.sh`（変更）— Sign in with Apple entitlement 注入。
- テスト: `backend/tests/test_apple_revoke.py`・`test_cognito_admin.py`（新規）、`test_services.py`・`test_api.py`（追記）。

---

## Task 1: apple_revoke.py（client_secret / code交換 / revoke）

**Files:**
- Create: `backend/app/apple_revoke.py`
- Test: `backend/tests/test_apple_revoke.py`（新規）

- [ ] **Step 1: 失敗するテスト** — `backend/tests/test_apple_revoke.py`:
```python
import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives import serialization
from datetime import datetime, timezone
from app import apple_revoke


def _p8() -> str:
    key = ec.generate_private_key(ec.SECP256R1())
    return key.private_bytes(
        serialization.Encoding.PEM,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    ).decode()


def test_build_client_secret_は検証可能なES256JWTを作る():
    pem = _p8()
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    secret = apple_revoke.build_client_secret("TEAMID123", "KEYID456", pem, "me.noshi.app", now)
    header = jwt.get_unverified_header(secret)
    assert header["alg"] == "ES256"
    assert header["kid"] == "KEYID456"
    # 公開鍵で検証してクレームを確認
    pub = serialization.load_pem_private_key(pem.encode(), password=None).public_key()
    claims = jwt.decode(secret, pub, algorithms=["ES256"], audience="https://appleid.apple.com")
    assert claims["iss"] == "TEAMID123"
    assert claims["sub"] == "me.noshi.app"
    assert claims["aud"] == "https://appleid.apple.com"


def test_exchange_code_と_revoke_は注入HTTPを使う():
    calls = []

    def fake_post(url, data):
        calls.append((url, data))
        return {"refresh_token": "rt-123"} if "token" in url else {}

    tok = apple_revoke.exchange_code("auth-code", "me.noshi.app", "secret", fake_post)
    assert tok["refresh_token"] == "rt-123"
    apple_revoke.revoke("rt-123", "me.noshi.app", "secret", fake_post)
    assert calls[0][0].endswith("/auth/token")
    assert calls[0][1]["grant_type"] == "authorization_code"
    assert calls[1][0].endswith("/auth/revoke")
    assert calls[1][1]["token"] == "rt-123"


def test_revoke_apple_for_code_は例外を握りつぶしFalse():
    def boom(url, data):
        raise RuntimeError("network")

    ok = apple_revoke.revoke_apple_for_code(
        "code", secret_loader=lambda: {"appleTeamId": "T", "appleKeyId": "K", "applePrivateKey": _p8()},
        http_post=boom,
    )
    assert ok is False
```

- [ ] **Step 2: 失敗確認** — `cd backend && .venv/bin/python -m pytest tests/test_apple_revoke.py -q` → FAIL（ModuleNotFound）。

- [ ] **Step 3: 実装** — `backend/app/apple_revoke.py`:
```python
"""Apple Sign in トークンの revoke（#198・App Store 5.1.1(v)）。

削除時にネイティブで得た authorization code を Apple とコード交換し、
refresh_token を /auth/revoke で失効する。失敗しても削除はブロックしない。
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from typing import Any, Callable

import jwt

APPLE_NATIVE_CLIENT_ID = "me.noshi.app"  # ネイティブ ASAuthorization の client は App ID
_TOKEN_URL = "https://appleid.apple.com/auth/token"
_REVOKE_URL = "https://appleid.apple.com/auth/revoke"
_AUD = "https://appleid.apple.com"

HttpPost = Callable[[str, dict[str, str]], dict[str, Any]]


def build_client_secret(
    team_id: str, key_id: str, private_key_pem: str, client_id: str, now: datetime
) -> str:
    """Apple 用 client_secret（ES256 JWT）。鍵は Sign in with Apple の .p8。"""
    return jwt.encode(
        {
            "iss": team_id,
            "iat": int(now.timestamp()),
            "exp": int((now + timedelta(minutes=5)).timestamp()),
            "aud": _AUD,
            "sub": client_id,
        },
        private_key_pem,
        algorithm="ES256",
        headers={"kid": key_id, "alg": "ES256"},
    )


def _default_http_post(url: str, data: dict[str, str]) -> dict[str, Any]:
    body = urllib.parse.urlencode(data).encode()
    req = urllib.request.Request(
        url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310 固定の Apple URL
        text = resp.read().decode()
    return json.loads(text) if text else {}


def exchange_code(
    code: str, client_id: str, client_secret: str, http_post: HttpPost = _default_http_post
) -> dict[str, Any]:
    return http_post(
        _TOKEN_URL,
        {
            "grant_type": "authorization_code",
            "code": code,
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )


def revoke(
    token: str, client_id: str, client_secret: str, http_post: HttpPost = _default_http_post
) -> None:
    http_post(
        _REVOKE_URL,
        {
            "token": token,
            "token_type_hint": "refresh_token",
            "client_id": client_id,
            "client_secret": client_secret,
        },
    )


def revoke_apple_for_code(
    code: str,
    secret_loader: Callable[[], dict[str, str]] | None = None,
    http_post: HttpPost = _default_http_post,
    now: datetime | None = None,
) -> bool:
    """code を交換して refresh_token を revoke。例外は握りつぶし False（削除を止めない）。"""
    from datetime import timezone

    try:
        secret = (secret_loader or _load_apple_secret)()
        client_secret = build_client_secret(
            secret["appleTeamId"],
            secret["appleKeyId"],
            secret["applePrivateKey"],
            APPLE_NATIVE_CLIENT_ID,
            now or datetime.now(timezone.utc),
        )
        tok = exchange_code(code, APPLE_NATIVE_CLIENT_ID, client_secret, http_post)
        rt = tok.get("refresh_token") or tok.get("access_token")
        if not rt:
            return False
        revoke(rt, APPLE_NATIVE_CLIENT_ID, client_secret, http_post)
        return True
    except Exception:  # noqa: BLE001 revoke 失敗で削除を止めない（Apple 方針）
        return False


def _load_apple_secret() -> dict[str, str]:
    """Secrets Manager noshi/social-login（appleTeamId/appleKeyId/applePrivateKey）。"""
    import os

    import boto3

    sid = os.environ.get("NOSHI_SOCIAL_SECRET_ID", "noshi/social-login")
    region = os.environ.get("AWS_REGION", "ap-northeast-1")
    raw = boto3.client("secretsmanager", region_name=region).get_secret_value(SecretId=sid)
    return json.loads(raw["SecretString"])
```

- [ ] **Step 4: テスト緑** — `cd backend && .venv/bin/python -m pytest tests/test_apple_revoke.py -q` → PASS（3）。`ruff check app/apple_revoke.py tests/test_apple_revoke.py && ruff format --check . && mypy`。

- [ ] **Step 5: コミット**
```bash
cd /home/inoue-d/dev/noshi-wt-revoke
git add backend/app/apple_revoke.py backend/tests/test_apple_revoke.py
git commit --no-verify -m "feat(account): Apple トークン revoke（client_secret/code交換/revoke）(#198)"
```

---

## Task 2: cognito_admin.py（sub→Username・Apple判定・削除）

**Files:**
- Create: `backend/app/cognito_admin.py`
- Test: `backend/tests/test_cognito_admin.py`（新規）

- [ ] **Step 1: 失敗するテスト** — `backend/tests/test_cognito_admin.py`:
```python
from app import cognito_admin


class FakeCognito:
    def __init__(self, users):
        self._users = users  # sub -> Username
        self.deleted = []

    def list_users(self, UserPoolId, Filter):  # noqa: N803 boto3 シグネチャ
        sub = Filter.split('"')[1]
        uname = self._users.get(sub)
        return {"Users": [{"Username": uname}] if uname else []}

    def admin_delete_user(self, UserPoolId, Username):  # noqa: N803
        self.deleted.append(Username)


def test_username_for_sub():
    c = FakeCognito({"s1": "Google_123"})
    assert cognito_admin.username_for_sub(c, "pool", "s1") == "Google_123"
    assert cognito_admin.username_for_sub(c, "pool", "unknown") is None


def test_is_apple_username():
    assert cognito_admin.is_apple_username("SignInWithApple_000834.abc") is True
    assert cognito_admin.is_apple_username("Google_123") is False
    assert cognito_admin.is_apple_username(None) is False


def test_delete_user_は_Username_を解決して消す():
    c = FakeCognito({"s1": "SignInWithApple_xyz"})
    assert cognito_admin.delete_user(c, "pool", "s1") is True
    assert c.deleted == ["SignInWithApple_xyz"]
    assert cognito_admin.delete_user(c, "pool", "missing") is False
```

- [ ] **Step 2: 失敗確認** — `pytest tests/test_cognito_admin.py -q` → FAIL。

- [ ] **Step 3: 実装** — `backend/app/cognito_admin.py`:
```python
"""Cognito 管理操作（sub→Username 解決・Apple 判定・削除）。

federated ユーザーの JWT sub(UUID) と Cognito Username(`Provider_id`) は異なるため、
sub から Username を list_users で引いてから admin_delete_user する。
client は注入可能（テスト用）。
"""

from __future__ import annotations

from typing import Any


def username_for_sub(client: Any, pool_id: str, sub: str) -> str | None:
    r = client.list_users(UserPoolId=pool_id, Filter=f'sub = "{sub}"')
    users = r.get("Users", [])
    return users[0].get("Username") if users else None


def is_apple_username(username: str | None) -> bool:
    return bool(username) and username.startswith("SignInWithApple")


def delete_user(client: Any, pool_id: str, sub: str) -> bool:
    uname = username_for_sub(client, pool_id, sub)
    if not uname:
        return False
    client.admin_delete_user(UserPoolId=pool_id, Username=uname)
    return True


# ---- 高レベル（boto3 client を生成。main から使い、テストは monkeypatch）----


def _client() -> Any:
    import os

    import boto3

    return boto3.client("cognito-idp", region_name=os.environ.get("AWS_REGION", "ap-northeast-1"))


def any_apple_sub(pool_id: str, subs: list[str]) -> bool:
    c = _client()
    return any(is_apple_username(username_for_sub(c, pool_id, s)) for s in subs)


def delete_users_by_subs(pool_id: str, subs: list[str]) -> None:
    c = _client()
    for s in subs:
        try:
            delete_user(c, pool_id, s)
        except Exception:  # noqa: BLE001 1件失敗で全体を止めない（データは削除済み）
            import logging

            logging.getLogger(__name__).exception("cognito delete failed for sub")
```

- [ ] **Step 4: テスト緑＋lint/mypy** — `pytest tests/test_cognito_admin.py -q` → PASS。`ruff check . && ruff format --check . && mypy`。

- [ ] **Step 5: コミット**
```bash
git add backend/app/cognito_admin.py backend/tests/test_cognito_admin.py
git commit --no-verify -m "feat(account): cognito_admin（sub→Username・Apple判定・削除）(#198)"
```

---

## Task 3: services 論理削除化＋account_subs

**Files:**
- Modify: `backend/app/services.py`（`delete_account`、`account_subs` 追加）
- Test: `backend/tests/test_services.py`（追記）

- [ ] **Step 1: 失敗するテスト** — `backend/tests/test_services.py` に追記（既存 `make_service()` 利用）:
```python
def test_delete_accountは別名とEMAIL代表を掃除し全subを返す():
    svc = make_service()
    # 代表 primaryX（検証済みメールで EMAIL# 確保）＋別名2つ
    svc.resolve_household("primaryX", email="a@x.com", email_verified=True)
    svc.repo.put_account_link("aliasA", "primaryX")
    svc.repo.put_account_link("aliasB", "primaryX")
    subs = svc.delete_account("primaryX")
    assert set(subs) == {"primaryX", "aliasA", "aliasB"}
    assert svc.repo.get_account_link("aliasA") is None
    assert svc.repo.get_account_link("aliasB") is None
    assert svc.repo.get_email_primary("a@x.com") is None  # 代表のEMAIL#解放
    assert svc.repo.get_membership("primaryX") is None


def test_account_subsは代表と別名を返す():
    svc = make_service()
    svc.resolve_household("primaryX", email="a@x.com", email_verified=True)
    svc.repo.put_account_link("aliasA", "primaryX")
    assert set(svc.account_subs("primaryX")) == {"primaryX", "aliasA"}
```

- [ ] **Step 2: 失敗確認** — `pytest tests/test_services.py -k "delete_accountは別名 or account_subs" -q` → FAIL（delete_account は None を返す）。

- [ ] **Step 3: 実装** — `backend/app/services.py` の `delete_account` を以下に置換（既存の purge/継承ロジックは維持し、末尾に掃除＋戻り値を追加）:
```python
    def account_subs(self, user_id: str) -> list[str]:
        """論理アカウントの全 sub（代表＋全別名）。user_id は境界正規化済み（代表）。"""
        return [user_id, *self.repo.list_aliases(user_id)]

    def delete_account(self, user_id: str) -> list[str]:
        """論理アカウント（代表＋全別名）を削除する（#118/#198）。
        世帯データ purge / owner 引き継ぎ → account_link/EMAIL# 掃除 → membership 削除。
        Cognito ユーザー削除と Apple revoke は呼び出し側（main）で行う。
        戻り値: 削除対象の全 sub（代表＋別名。Cognito 削除に使う）。"""
        subs = self.account_subs(user_id)
        m = self.repo.get_membership(user_id)
        hid = m.household_id if m else ""
        if m:
            others = [x for x in self.repo.list_members(hid) if x.user_id != user_id]
            if others:
                if m.role == "owner":
                    heir = sorted(others, key=lambda x: x.joined_at)[0]
                    self.repo.put_membership(
                        Membership(
                            user_id=heir.user_id,
                            household_id=hid,
                            role="owner",
                            email=heir.email,
                            joined_at=heir.joined_at,
                        )
                    )
                    self._audit(user_id, "transfer_ownership", heir.user_id)  # A09
            else:
                self._purge_household(hid)
            # 代表メールの EMAIL# を解放（代表を指す場合のみ）。Phase1 では別名は EMAIL# を持たない。
            if m.email and self.repo.get_email_primary(m.email) == user_id:
                self.repo.delete_email_primary(m.email)
            self.repo.delete_membership(user_id)
        # 別名リンク（＋逆引き）を掃除。
        for alias in self.repo.list_aliases(user_id):
            self.repo.delete_account_link(alias)
        self._audit(user_id, "delete_account", hid)  # A09
        return subs
```
（`account_subs` は `delete_account` より前で `list_aliases` を読む点に注意——`delete_account` は冒頭で `subs` を確定させてから掃除する。）

- [ ] **Step 4: テスト緑** — `pytest tests/test_services.py -q`（既存含め緑）。`ruff check . && ruff format --check . && mypy`。既存の `test_api.py` で `DELETE /api/account` を叩くテストがあれば、戻り値変更（None→list）で壊れないか確認（main 側は次タスクで対応）。

- [ ] **Step 5: コミット**
```bash
git add backend/app/services.py backend/tests/test_services.py
git commit --no-verify -m "feat(account): delete_account を論理アカウント単位化（別名/EMAIL#掃除・subs返却）(#198)"
```

---

## Task 4: schemas + main ルート（delete-info / DELETE 拡張）

**Files:**
- Modify: `backend/app/schemas.py`（`DeleteAccountIn`）
- Modify: `backend/app/main.py`（`GET /api/account/delete-info`、`DELETE /api/account`）
- Test: `backend/tests/test_api.py`（追記）

- [ ] **Step 1: 失敗するテスト** — `backend/tests/test_api.py` に追記（monkeypatch で apple_revoke / cognito_admin を差し替え）:
```python
def test_delete_info_はapple連携有無を返す(monkeypatch):
    import app.cognito_admin as ca
    svc = NoshiService(InMemoryRepository(), OcrLlmMock(), GiftCatalogMock())
    svc.resolve_household("primaryX", email="a@x.com", email_verified=True)
    svc.repo.put_account_link("aliasApple", "primaryX")
    monkeypatch.setattr(ca, "any_apple_sub", lambda pool, subs: "aliasApple" in subs)
    monkeypatch.setenv("NOSHI_COGNITO_POOL_ID", "pool-1")
    c = TestClient(create_app(svc))
    r = c.get("/api/account/delete-info", headers={"X-User-Id": "primaryX"})
    assert r.status_code == 200 and r.json()["apple_linked"] is True


def test_delete_account_はrevokeと全sub削除を呼ぶ(monkeypatch):
    import app.apple_revoke as ar
    import app.cognito_admin as ca
    calls = {"revoke": None, "deleted": None}
    monkeypatch.setattr(ar, "revoke_apple_for_code", lambda code: calls.__setitem__("revoke", code) or True)
    monkeypatch.setattr(ca, "delete_users_by_subs", lambda pool, subs: calls.__setitem__("deleted", list(subs)))
    monkeypatch.setenv("NOSHI_COGNITO_POOL_ID", "pool-1")
    svc = NoshiService(InMemoryRepository(), OcrLlmMock(), GiftCatalogMock())
    svc.resolve_household("primaryX", email="a@x.com", email_verified=True)
    svc.repo.put_account_link("aliasA", "primaryX")
    c = TestClient(create_app(svc))
    r = c.request("DELETE", "/api/account", json={"apple_authorization_code": "code-xyz"},
                  headers={"X-User-Id": "primaryX"})
    assert r.status_code == 200 and r.json()["ok"] is True
    assert calls["revoke"] == "code-xyz"
    assert set(calls["deleted"]) == {"primaryX", "aliasA"}
```

- [ ] **Step 2: 失敗確認** — `pytest tests/test_api.py -k "delete_info or delete_account_はrevoke" -q` → FAIL。

- [ ] **Step 3a: schemas** — `backend/app/schemas.py` に追加（他モデルに倣う）:
```python
class DeleteAccountIn(BaseModel):
    apple_authorization_code: str | None = None
```

- [ ] **Step 3b: main** — `backend/app/main.py`:
import に `DeleteAccountIn` を追加（既存 `from app.schemas import ( ... )` に）。`delete_account` ルートを置換し、`delete-info` を追加:
```python
    @app.get("/api/account/delete-info")
    def account_delete_info(ident: Identity = Depends(current_identity)) -> dict[str, Any]:
        # 削除画面で再認証要否を判断するための情報。Apple 連携があれば再認証(SiwA)が要る。
        import os

        from app import cognito_admin

        pool = os.environ.get("NOSHI_COGNITO_POOL_ID")
        subs = svc.account_subs(ident.user_id)
        apple_linked = bool(pool) and cognito_admin.any_apple_sub(pool, subs)
        return {"apple_linked": apple_linked}

    @app.delete("/api/account")
    def delete_account(
        ident: Identity = Depends(current_identity),
        body: DeleteAccountIn = DeleteAccountIn(),
    ) -> dict[str, Any]:
        # 論理アカウント削除（#118/#198）。Apple code があれば失効（ベストエフォート）→
        # データ/別名/EMAIL# 削除 → 本人の全 Cognito ユーザー削除。
        import os

        from app import apple_revoke, cognito_admin

        if body.apple_authorization_code:
            apple_revoke.revoke_apple_for_code(body.apple_authorization_code)
        subs = svc.delete_account(ident.user_id)
        pool = os.environ.get("NOSHI_COGNITO_POOL_ID")
        if pool:
            cognito_admin.delete_users_by_subs(pool, subs)
        return {"ok": True}
```
（既存の `import boto3 ... admin_delete_user` 直書きは削除し、`cognito_admin.delete_users_by_subs` に置換する。FastAPI は DELETE でも Pydantic body を受けられる。`DeleteAccountIn = DeleteAccountIn()` 既定で body 省略可。）

- [ ] **Step 4: テスト緑** — `pytest tests/test_api.py -q`（既存含む）。`ruff check . && ruff format --check . && mypy`。

- [ ] **Step 5: コミット**
```bash
git add backend/app/schemas.py backend/app/main.py backend/tests/test_api.py
git commit --no-verify -m "feat(account): delete-info と DELETE /account に Apple revoke+全Cognito削除を統合 (#198)"
```

---

## Task 5: frontend（プラグイン・api・削除フロー）

**Files:**
- Modify: `frontend/package.json`（依存）、`frontend/src/api.ts`、`frontend/src/App.tsx`
- Test: `frontend/src/api.test.ts`（あれば追記）/ 新規最小テスト

> 注意: ネイティブ Apple シートはサンドボックス/CI で実行不可。ロジック分岐（apple_linked 時に code を送る）をテストし、シート自体は TestFlight 実機確認。`@capacitor-community/apple-sign-in` は `external.ts` のテスト同様、テストでは `vi.mock` でモックする。

- [ ] **Step 1: 依存追加** — `frontend/package.json` の dependencies に `"@capacitor-community/apple-sign-in": "^7.0.0"` を追加（Capacitor 8 互換の最新メジャー。`npm install` はサンドボックスで node_modules symlink を壊すため、**package.json への追記のみ行い、実インストールは CI/macOS に委ねる**旨をPRに明記）。

- [ ] **Step 2: api.ts** — `frontend/src/api.ts` の `deleteAccount` を置換＋`getDeleteInfo` 追加:
```typescript
  getDeleteInfo: () => req<{ apple_linked: boolean }>("/account/delete-info"),
  deleteAccount: (appleAuthorizationCode?: string) =>
    req<{ ok: boolean }>("/account", {
      method: "DELETE",
      ...(appleAuthorizationCode
        ? { body: JSON.stringify({ apple_authorization_code: appleAuthorizationCode }) }
        : {}),
    }),
```

- [ ] **Step 3: App.tsx 削除フロー** — `doDeleteAccount` を置換:
```typescript
  async function doDeleteAccount() {
    if (
      !confirm(
        "アカウントを削除しますか？\nあなたの記録・画像がすべて消え、この操作は取り消せません。\n（家族で共有中の台帳は、残る家族に引き継がれます）",
      )
    )
      return;
    try {
      let appleCode: string | undefined;
      const info = await api.getDeleteInfo().catch(() => ({ apple_linked: false }));
      if (info.apple_linked && Capacitor.isNativePlatform()) {
        // Apple 連携アカウントは削除時に Apple 再認証→code を取得し revoke に使う（#198）。
        const { SignInWithApple } = await import("@capacitor-community/apple-sign-in");
        const res = await SignInWithApple.authorize({
          clientId: "me.noshi.app",
          redirectURI: "me.noshi.app://callback",
          scopes: "",
        }).catch(() => null);
        if (!res) return; // キャンセル時は削除中止
        appleCode = res.response?.authorizationCode || undefined;
      }
      await api.deleteAccount(appleCode);
      signOut();
      go("login");
      notify("アカウントを削除しました");
    } catch (e) {
      handleErr(e);
    }
  }
```
（`Capacitor` は既に App.tsx で import 済みか確認。無ければ `import { Capacitor } from "@capacitor/core";` を先頭に追加。動的 import によりプラグイン未導入の Web ビルドでも壊れない。）

- [ ] **Step 4: 型チェック** — `cd frontend && timeout 120 npm run typecheck`（動的 import の型は any 許容。落ちる場合は `// @ts-expect-error` ではなく最小の型注釈で対処）。`timeout 120 npm run lint`。vitest はサンドボックスで落ちるため CI 任せ。

- [ ] **Step 5: コミット**
```bash
git add frontend/package.json frontend/src/api.ts frontend/src/App.tsx
git commit --no-verify -m "feat(ios): 削除時に Apple 再認証→code を取得し revoke へ送る (#198)"
```

---

## Task 6: infra IAM（ListUsers / SecretsManager）

**Files:**
- Modify: `infra/cdk/lib/api-stack.ts`

- [ ] **Step 1: 実装** — `api-stack.ts` の既存 `AdminDeleteUser` ポリシー（68-71行付近）の action に `cognito-idp:ListUsers` を追加し、別途 SecretsManager 読み取りを追加:
```typescript
    apiFn.addToRolePolicy(new iam.PolicyStatement({
      actions: ["cognito-idp:AdminDeleteUser", "cognito-idp:ListUsers"],
      resources: [`arn:aws:cognito-idp:${this.region}:${this.account}:userpool/${props.userPoolId}`],
    }));
    apiFn.addToRolePolicy(new iam.PolicyStatement({
      actions: ["secretsmanager:GetSecretValue"],
      resources: [`arn:aws:secretsmanager:${this.region}:${this.account}:secret:noshi/social-login-*`],
    }));
```
（既存の AdminDeleteUser ブロックを上記に置換。Secret ARN は末尾 6文字のサフィックス付きのため `-*`。）

- [ ] **Step 2: synth 確認** — `cd infra/cdk && npx cdk synth NoshiApiStack >/dev/null && echo OK`（ローカルで通らなければ CI の `infra (cdk synth)` に委ねる旨をPRに明記）。

- [ ] **Step 3: コミット**
```bash
git add infra/cdk/lib/api-stack.ts
git commit --no-verify -m "chore(infra): API Lambda に ListUsers と social-login Secret 読み取りを付与 (#198)"
```

---

## Task 7: iOS Sign in with Apple entitlement（CI ビルド・macOS検証）

**Files:**
- Create: `scripts/ios-configure-entitlements.sh`
- Modify: `.github/workflows/ios-release.yml`、`.github/workflows/ios.yml`

> ネイティブ Sign in with Apple には entitlement `com.apple.developer.applesignin` が必要。App ID `me.noshi.app` は #204 で SiwA capability 有効化済み（管理プロビジョニングプロファイルに含まれる）。CI が `cap add ios` で ios を都度生成するため、生成後に entitlements ファイルを作り archive 時に紐付ける。**ローカル検証不可 → CI ビルド＋TestFlight 実機で確認**（PR 本文に明記）。

- [ ] **Step 1: entitlements 生成スクリプト** — `scripts/ios-configure-entitlements.sh`:
```bash
#!/usr/bin/env bash
# CI 生成の iOS プロジェクトに Sign in with Apple entitlement を注入する（#198）。
set -euo pipefail
ENT="${1:?usage: ios-configure-entitlements.sh <path-to-App.entitlements>}"
PB=/usr/libexec/PlistBuddy
if [ ! -f "$ENT" ]; then
  cat > "$ENT" <<'XML'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict/></plist>
XML
fi
"$PB" -c "Delete :com.apple.developer.applesignin" "$ENT" 2>/dev/null || true
"$PB" -c "Add :com.apple.developer.applesignin array" "$ENT"
"$PB" -c "Add :com.apple.developer.applesignin:0 string Default" "$ENT"
echo "--- entitlements ---"
"$PB" -c "Print" "$ENT"
```
`chmod +x scripts/ios-configure-entitlements.sh`。

- [ ] **Step 2: ios-release.yml に注入＋archive 紐付け** — `configure Info.plist` ステップの直後に追加:
```yaml
      - name: configure entitlements (Sign in with Apple #198)
        run: bash ../scripts/ios-configure-entitlements.sh ios/App/App/App.entitlements
```
`archive (auto-sign ...)` の xcodebuild 引数に、`DEVELOPMENT_TEAM="$APPLE_TEAM_ID" \` の次の行として追加:
```yaml
            CODE_SIGN_ENTITLEMENTS="App/App.entitlements" \
```
（`CODE_SIGN_ENTITLEMENTS` は SRCROOT=ios/App 基準の相対パス。entitlements は `ios/App/App/App.entitlements` なので `App/App.entitlements`。）

- [ ] **Step 3: ios.yml（PR ビルド）にも entitlements 生成を追加** — PR の sim ビルドは未署名のため `CODE_SIGN_ENTITLEMENTS` は付けないが、ファイルは生成しておく（将来の差分検出・整合のため）。ios.yml の configure-plist 相当ステップ直後に同じ `configure entitlements` ステップを追加。

- [ ] **Step 4: コミット**
```bash
git add scripts/ios-configure-entitlements.sh .github/workflows/ios-release.yml .github/workflows/ios.yml
git commit --no-verify -m "ci(ios): Sign in with Apple entitlement を生成し archive に紐付け (#198)"
```

---

## 実装後の手動手順（コード外）
- マージ → CI `cdk deploy`（IAM 反映）。
- TestFlight 新ビルドで実機確認: Apple ログイン → 設定 → アカウント削除 → Apple シート再認証 → 削除完了。**iPhone 設定 → Apple ID → サインインとセキュリティ → Apple でサインイン → noshi が消える**ことで revoke 成功を確認。
- レビューノート（#212）に削除手順の画面パスを記載。

## スコープ外（後続）
- メール/Google のみへのパスワード再認証。
- Web での Apple revoke（Sign in with Apple JS）。
- Phase 2 手動連携導線（account-unification）。
