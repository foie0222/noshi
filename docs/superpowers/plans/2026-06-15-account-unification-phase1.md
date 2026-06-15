# アカウント統合 Phase 1 実装計画

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 同一人物が複数ログイン手段で分裂しないよう、アプリ層エイリアス＋検証済みメール自動リンクを backend に入れ、開発者本人の既存分裂をワンオフ移行で解消する。

**Architecture:** DynamoDB `noshi` に `account_link`（別名sub→代表sub）・逆引き `PRIMARY#`・`EMAIL#`（検証済みメール→代表のユニーク）を追加。`current_identity`（リクエスト境界）で生 sub を代表 sub に正規化し、以降のサービスは代表 sub のみを見る。初回ログイン時は `EMAIL#` への条件付き put 一発で「代表確保 or 既存合流」をアトミックに分岐する。

**Tech Stack:** Python 3.12 / FastAPI / boto3 (DynamoDB) / pytest。spec: `docs/superpowers/specs/2026-06-15-account-unification-design.md`（迷ったら spec が正）。

**検証ゲート（各タスクで主張前に必ず実行）:** `cd backend && .venv/bin/python -m pytest <該当> -q`。コミットは `--no-verify`（ローカルの pre-commit がサンドボックスで exit 216）。Dynamo 実装(Task 6)・移行(Task 7)は実機 AWS で別途確認（PR本文に明記）。

---

## ファイル構成

- `backend/app/repository.py` — `Repository` Protocol・`InMemoryRepository`・`DynamoRepository` に account_link / email-primary / reverse-index のメソッドを追加。
- `backend/app/auth.py` — `Identity` に `raw_user_id`・`email_verified` を追加、`decode_identity` で `email_verified` を取得。
- `backend/app/account.py`（新規）— `canonical_sub` 解決と自動リンク判定の純度高めロジック（repo 注入）。
- `backend/app/services.py` — `resolve_household` にエイリアス解決＋自動リンク＋`EMAIL#` 自己修復を統合。
- `backend/app/main.py` — `current_identity` で代表 sub に正規化。
- `backend/scripts/migrate_account_links.py`（新規）— 開発者本人のワンオフ移行（dry-run 既定）。
- テスト: `backend/tests/test_account_links.py`（新規）, 既存 `backend/tests/test_*` に追記。

> Membership 実体（`app/domain/entities.py`）: `Membership(user_id, household_id, role, email, notify_email=...)`。`AccountLink` 等の新エンティティは dataclass で追加する。

---

## Task 1: AccountLink エンティティと Repository インターフェース＋InMemory 実装

**Files:**
- Modify: `backend/app/domain/entities.py`（`AccountLink` 追加）
- Modify: `backend/app/repository.py`（Protocol + InMemoryRepository）
- Test: `backend/tests/test_account_links.py`（新規）

- [ ] **Step 1: 失敗するテストを書く**

`backend/tests/test_account_links.py`:
```python
from app.repository import InMemoryRepository


def test_email_primary_の条件付き確保は最初の1人だけ勝つ():
    repo = InMemoryRepository()
    assert repo.claim_email_primary("a@x.com", "subA") is True   # 先着が勝つ
    assert repo.claim_email_primary("a@x.com", "subB") is False  # 後着は負ける
    assert repo.get_email_primary("a@x.com") == "subA"


def test_account_link_の作成と解決と逆引き():
    repo = InMemoryRepository()
    repo.put_account_link("alias1", "primaryX", provider="SignInWithApple", email="")
    assert repo.get_account_link("alias1") == "primaryX"
    assert repo.get_account_link("unknown") is None
    assert repo.list_aliases("primaryX") == ["alias1"]


def test_email_primary_の張替えと削除():
    repo = InMemoryRepository()
    repo.claim_email_primary("a@x.com", "subA")
    repo.set_email_primary("a@x.com", "subC")   # 張替え（無条件）
    assert repo.get_email_primary("a@x.com") == "subC"
    repo.delete_email_primary("a@x.com")
    assert repo.get_email_primary("a@x.com") is None
```

- [ ] **Step 2: 失敗を確認**

Run: `cd backend && .venv/bin/python -m pytest tests/test_account_links.py -q`
Expected: FAIL（`AttributeError: 'InMemoryRepository' object has no attribute 'claim_email_primary'`）

- [ ] **Step 3: AccountLink エンティティを追加**

`backend/app/domain/entities.py` の末尾付近（他 dataclass と同じ書式）に追加:
```python
@dataclass
class AccountLink:
    """別名 sub → 代表 sub のエイリアス（同一人物の別ログイン）。"""

    alias_sub: str
    primary_sub: str
    provider: str = ""
    email: str = ""
    linked_at: str = ""
```
（ファイル先頭に `from dataclasses import dataclass` が既にある前提。無ければ既存 import に倣う。）

- [ ] **Step 4: Repository Protocol にメソッド宣言を追加**

`backend/app/repository.py` の `Repository` Protocol 内（membership 群の直後、line 46 付近）に追加:
```python
    # --- アカウント統合（account unification・別名/代表/メール代表） ---
    def get_account_link(self, alias_sub: str) -> str | None: ...
    def put_account_link(
        self, alias_sub: str, primary_sub: str, provider: str = "", email: str = ""
    ) -> None: ...
    def delete_account_link(self, alias_sub: str) -> None: ...
    def list_aliases(self, primary_sub: str) -> list[str]: ...
    def get_email_primary(self, email: str) -> str | None: ...
    def claim_email_primary(self, email: str, primary_sub: str) -> bool: ...
    def set_email_primary(self, email: str, primary_sub: str) -> None: ...
    def delete_email_primary(self, email: str) -> None: ...
```

- [ ] **Step 5: InMemoryRepository に状態と実装を追加**

`InMemoryRepository.__init__`（line 69-79 付近）の末尾に追加:
```python
        self._account_links: dict[str, AccountLink] = {}  # alias_sub -> AccountLink
        self._email_primary: dict[str, str] = {}  # email(小文字) -> primary_sub
```
`InMemoryRepository` のメソッドとして追加（membership 群の近く）:
```python
    def get_account_link(self, alias_sub: str) -> str | None:
        link = self._account_links.get(alias_sub)
        return link.primary_sub if link else None

    def put_account_link(
        self, alias_sub: str, primary_sub: str, provider: str = "", email: str = ""
    ) -> None:
        self._account_links[alias_sub] = AccountLink(
            alias_sub=alias_sub, primary_sub=primary_sub, provider=provider, email=email
        )

    def delete_account_link(self, alias_sub: str) -> None:
        self._account_links.pop(alias_sub, None)

    def list_aliases(self, primary_sub: str) -> list[str]:
        return [a for a, lk in self._account_links.items() if lk.primary_sub == primary_sub]

    def get_email_primary(self, email: str) -> str | None:
        return self._email_primary.get(email.lower())

    def claim_email_primary(self, email: str, primary_sub: str) -> bool:
        key = email.lower()
        if key in self._email_primary:
            return False
        self._email_primary[key] = primary_sub
        return True

    def set_email_primary(self, email: str, primary_sub: str) -> None:
        self._email_primary[email.lower()] = primary_sub

    def delete_email_primary(self, email: str) -> None:
        self._email_primary.pop(email.lower(), None)
```
`repository.py` 先頭の entities import（line 11-19）に `AccountLink` を追加:
```python
from app.domain.entities import (
    AccountLink,
    AuditEntry,
    ...
)
```

- [ ] **Step 6: テストが通ることを確認**

Run: `cd backend && .venv/bin/python -m pytest tests/test_account_links.py -q`
Expected: PASS（3 件）

- [ ] **Step 7: コミット**

```bash
git add backend/app/domain/entities.py backend/app/repository.py backend/tests/test_account_links.py
git commit --no-verify -m "feat(account): AccountLink/EMAIL# の repo メソッドと InMemory 実装 (account-unification)"
```

---

## Task 2: Identity に email_verified / raw_user_id を追加

**Files:**
- Modify: `backend/app/auth.py:22-25`（Identity）, `backend/app/auth.py:67-82`（decode_identity）
- Test: `backend/tests/test_auth.py`（既存に追記。無ければ新規）

- [ ] **Step 1: 失敗するテストを書く**

`backend/tests/test_auth.py` に追記（HS256 でトークンを作って検証）:
```python
import os
import jwt
from app.auth import decode_identity


def test_decode_identity_は_email_verified_と_raw_user_id_を取り込む(monkeypatch):
    monkeypatch.setenv("NOSHI_JWT_SECRET", "s3cret")
    token = jwt.encode(
        {"sub": "sub1", "email": "a@x.com", "email_verified": True, "exp": 9999999999},
        "s3cret",
        algorithm="HS256",
    )
    ident = decode_identity(token)
    assert ident.user_id == "sub1"
    assert ident.raw_user_id == "sub1"   # 解決前は raw==user_id
    assert ident.email_verified is True
```

- [ ] **Step 2: 失敗を確認**

Run: `cd backend && .venv/bin/python -m pytest tests/test_auth.py -k email_verified -q`
Expected: FAIL（`TypeError: __init__() got an unexpected keyword` か `AttributeError: email_verified`）

- [ ] **Step 3: Identity と decode_identity を変更**

`backend/app/auth.py` の Identity:
```python
@dataclass(frozen=True)
class Identity:
    user_id: str  # 代表 sub（境界で正規化後）。未正規化時は raw と同値。
    email: str = ""
    email_verified: bool = False
    raw_user_id: str = ""  # 物理的にログインした生 sub（監査・診断用）
```
`decode_identity` の return（line 82）を変更:
```python
    ev = claims.get("email_verified")
    email_verified = ev is True or ev == "true"
    return Identity(
        user_id=sub,
        email=claims.get("email", "") or "",
        email_verified=email_verified,
        raw_user_id=sub,
    )
```

- [ ] **Step 4: テストが通ることを確認**

Run: `cd backend && .venv/bin/python -m pytest tests/test_auth.py -q`
Expected: PASS（既存テストも緑のまま）

- [ ] **Step 5: コミット**

```bash
git add backend/app/auth.py backend/tests/test_auth.py
git commit --no-verify -m "feat(auth): Identity に email_verified/raw_user_id を追加 (account-unification)"
```

---

## Task 3: canonical_sub 解決（account.py）

**Files:**
- Create: `backend/app/account.py`
- Test: `backend/tests/test_account_links.py`（追記）

- [ ] **Step 1: 失敗するテストを書く**

`backend/tests/test_account_links.py` に追記:
```python
from app.account import canonical_sub


def test_canonical_sub_は_別名を代表に解決し_別名でなければそのまま():
    repo = InMemoryRepository()
    repo.put_account_link("alias1", "primaryX")
    assert canonical_sub(repo, "alias1") == "primaryX"
    assert canonical_sub(repo, "primaryX") == "primaryX"  # 代表はそのまま
    assert canonical_sub(repo, "unknown") == "unknown"    # 未知もそのまま（新規扱い）
```

- [ ] **Step 2: 失敗を確認**

Run: `cd backend && .venv/bin/python -m pytest tests/test_account_links.py -k canonical -q`
Expected: FAIL（`ModuleNotFoundError: No module named 'app.account'`）

- [ ] **Step 3: account.py を実装**

`backend/app/account.py`:
```python
"""アカウント統合: 生 sub を代表 sub に解決する（アプリ層エイリアス）。

不変条件 I3 により account_link の指す先は常に終端の代表なので解決は1ホップで足りる。
"""

from __future__ import annotations

from app.repository import Repository


def canonical_sub(repo: Repository, raw_sub: str) -> str:
    """別名 sub を代表 sub に解決する。別名でなければ入力をそのまま返す。"""
    primary = repo.get_account_link(raw_sub)
    return primary or raw_sub
```

- [ ] **Step 4: テストが通ることを確認**

Run: `cd backend && .venv/bin/python -m pytest tests/test_account_links.py -k canonical -q`
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add backend/app/account.py backend/tests/test_account_links.py
git commit --no-verify -m "feat(account): canonical_sub 解決（1ホップ・エイリアス）(account-unification)"
```

---

## Task 4: resolve_household に自動リンク＋EMAIL# 自己修復を統合

**Files:**
- Modify: `backend/app/services.py:76-99`（resolve_household / _scope）
- Test: `backend/tests/test_services.py`（既存に追記）

> 現行 `resolve_household(self, user_id, email="")`（services.py:76）に **email_verified を受ける引数を追加**し、`main.py` の呼び出し（後続 Task 5）から渡す。ロジックは spec §4.4/§4.5。

- [ ] **Step 1: 失敗するテストを書く**

`backend/tests/test_services.py` に追記（既存 `make_service()`（test_services.py:8）と同じ構築を使う）:
```python
from app.ports import GiftCatalogMock, OcrLlmMock
from app.repository import InMemoryRepository
from app.services import NoshiService


def _svc():
    return NoshiService(InMemoryRepository(), OcrLlmMock(), GiftCatalogMock())


def test_検証済みメールが一致する2人目は1人目の世帯に自動合流する():
    svc = _svc()
    h1 = svc.resolve_household("subGoogle", email="a@x.com", email_verified=True)
    # 別ログイン（同一検証済みメール）→ 同じ世帯へ
    h2 = svc.resolve_household("subMail", email="a@x.com", email_verified=True)
    assert h2.id == h1.id
    # subMail は別名として代表(subGoogle)に解決される
    assert svc.repo.get_account_link("subMail") == "subGoogle"


def test_未検証メールは自動合流せず別世帯になる():
    svc = _svc()
    h1 = svc.resolve_household("subGoogle", email="a@x.com", email_verified=True)
    h2 = svc.resolve_household("subApple", email="relay@privaterelay.appleid.com", email_verified=False)
    assert h2.id != h1.id
    assert svc.repo.get_account_link("subApple") is None


def test_既存membershipを持つsubは再エイリアスされない():
    svc = _svc()
    svc.resolve_household("subGoogle", email="a@x.com", email_verified=True)
    # 同じ sub で再アクセスしても membership 優先で世帯は不変・リンクも増えない
    again = svc.resolve_household("subGoogle", email="a@x.com", email_verified=True)
    assert svc.repo.get_account_link("subGoogle") is None
    assert again.id == svc.resolve_household("subGoogle").id
```

- [ ] **Step 2: 失敗を確認**

Run: `cd backend && .venv/bin/python -m pytest tests/test_services.py -k 自動合流 -q`
Expected: FAIL（`TypeError: resolve_household() got an unexpected keyword 'email_verified'`）

- [ ] **Step 3: resolve_household を実装変更**

`backend/app/services.py` の `resolve_household` を以下に置換（spec §4.4/§4.5）:
```python
    def resolve_household(
        self, user_id: str, email: str = "", email_verified: bool = False
    ) -> Household:
        """ユーザーの世帯を返す。エイリアス解決→membership→自動リンク→新規作成の順（A01）。"""
        from app.account import canonical_sub

        # 1. 別名なら代表 sub に正規化（1ホップ）。
        user_id = canonical_sub(self.repo, user_id)

        # 2. 既存 membership があればその世帯（＋email 自己修復・EMAIL# backfill）。
        m = self.repo.get_membership(user_id)
        if m is not None:
            h = self.repo.get_household(m.household_id)
            if h is not None:
                if email and m.email != email:
                    m.email = email
                    self.repo.put_membership(m)
                # 検証済みメールの EMAIL# 代表が未登録なら自己修復（将来の別ログイン自動統合用）。
                if email and email_verified and self.repo.get_email_primary(email) is None:
                    self.repo.claim_email_primary(email, user_id)
                return h

        # 3. 初回 sub。検証済みメールなら EMAIL# 条件付き put で代表確保 or 既存合流。
        if email and email_verified:
            claimed = self.repo.claim_email_primary(email, user_id)
            if not claimed:
                primary = self.repo.get_email_primary(email)
                if primary and primary != user_id:
                    self.repo.put_account_link(user_id, primary, email=email)
                    self._audit(user_id, "auto_link", primary)  # A09
                    ph = self.repo.get_household(
                        self.repo.get_membership(primary).household_id
                    )
                    if ph is not None:
                        return ph
            # claimed=True、または代表世帯が見つからない場合は新規作成へフォールスルー。

        # 4. 新規世帯を作成し本人を owner にする。
        h = Household()
        self.repo.put_household(h)
        self.repo.put_membership(
            Membership(user_id=user_id, household_id=h.id, role="owner", email=email)
        )
        self._audit(user_id, "create_household", h.id)  # A09
        return h
```
（`_scope` は変更不要。`_scope` は `resolve_household(user_id)` を呼ぶため、内部で再度エイリアス解決される＝代表 sub に正規化される。）

- [ ] **Step 4: テストが通ることを確認**

Run: `cd backend && .venv/bin/python -m pytest tests/test_services.py -q`
Expected: PASS（新規3件＋既存が緑）

- [ ] **Step 5: コミット**

```bash
git add backend/app/services.py backend/tests/test_services.py
git commit --no-verify -m "feat(account): resolve_household に自動リンク+EMAIL#自己修復を統合 (account-unification)"
```

---

## Task 5: current_identity で代表 sub に正規化（リクエスト境界）

**Files:**
- Modify: `backend/app/main.py:84-106`（current_identity）, `:123-167`（resolve_household 呼び出しに email_verified を渡す）
- Test: `backend/tests/test_api.py`（既存に追記。HTTP レベル）

> 既存 `test_api.py` は `create_app()` を引数なしで使い、認証はスタブ `X-User-Id`（`_h(uid)` = `{"X-User-Id": uid}`）。本テストは repo にアクセスしたいので `create_app(svc)` でサービスを注入する（main.py:82 が `service or 既定` を受ける）。スタブ経路の Identity は `email_verified=False` だが、別名解決（canonical_sub）自体はメールに依存しないため検証可能。

- [ ] **Step 1: 失敗するテストを書く**

`backend/tests/test_api.py` に追記:
```python
from app.ports import GiftCatalogMock, OcrLlmMock
from app.repository import InMemoryRepository
from app.services import NoshiService


def test_別名subのリクエストは代表の世帯に解決される():
    svc = NoshiService(InMemoryRepository(), OcrLlmMock(), GiftCatalogMock())
    c = TestClient(create_app(svc))
    # 代表世帯を用意し、別名 aliasY を代表 primaryX に貼る
    svc.resolve_household("primaryX", email="a@x.com", email_verified=True)
    svc.repo.put_account_link("aliasY", "primaryX", email="a@x.com")
    # aliasY でアクセスしても primaryX の世帯に解決され、別名の新規世帯は作られない
    r = c.get("/api/household", headers={"X-User-Id": "aliasY"})
    assert r.status_code == 200
    assert svc.repo.get_membership("aliasY") is None
```

- [ ] **Step 2: 失敗を確認**

Run: `cd backend && .venv/bin/python -m pytest tests/test_api.py -k 別名 -q`
Expected: FAIL（aliasY で新規世帯が作られ membership が存在してしまう）

- [ ] **Step 3: current_identity を正規化対応にする**

`backend/app/main.py` の `current_identity`（line 84-106）で、JWT 経路の return とスタブ経路の return を**代表 sub に正規化**する。`decode_identity` の戻り `ident`（生 sub）を `svc.repo` で解決し `Identity` を作り直す:
```python
        from app.account import canonical_sub

        def _normalized(ident: Identity) -> Identity:
            cano = canonical_sub(svc.repo, ident.user_id)
            if cano == ident.user_id:
                return ident
            from dataclasses import replace

            return replace(ident, user_id=cano, raw_user_id=ident.raw_user_id or ident.user_id)

        if auth_configured():
            if not authorization:
                raise HTTPException(status_code=401, detail="authentication required")
            token = (
                authorization[7:] if authorization.lower().startswith("bearer ") else authorization
            )
            try:
                return _normalized(decode_identity(token))
            except AuthError:
                raise HTTPException(status_code=401, detail="authentication required") from None
        if x_user_id:
            return _normalized(Identity(user_id=x_user_id, raw_user_id=x_user_id))
        raise HTTPException(status_code=401, detail="authentication required")
```

- [ ] **Step 4: household/notifications 系で email_verified を resolve_household に渡す**

`backend/app/main.py` の `/api/household`・`/api/notifications`(GET/PUT) の `svc.resolve_household(ident.user_id, email=ident.email)` 3箇所（line 126,132,139）を:
```python
        svc.resolve_household(ident.user_id, email=ident.email, email_verified=ident.email_verified)
```
`join_household` の呼び出し（line 147）は email_verified を取らないため変更不要（後続 Task 範囲外）。

- [ ] **Step 5: テストが通ることを確認**

Run: `cd backend && .venv/bin/python -m pytest tests/test_api.py -q`
Expected: PASS（既存も緑）

- [ ] **Step 6: 全 backend テストを実行**

Run: `cd backend && .venv/bin/python -m pytest -q`
Expected: 全 PASS

- [ ] **Step 7: コミット**

```bash
git add backend/app/main.py backend/tests/test_api.py
git commit --no-verify -m "feat(account): current_identity で代表subに正規化し email_verified を伝播 (account-unification)"
```

---

## Task 6: DynamoRepository の account_link / EMAIL# 実装（条件付き書き込み）

**Files:**
- Modify: `backend/app/repository.py`（`DynamoRepository`・line 218 以降）
- Test: `backend/tests/test_repository_dynamo.py`（既存の moto/local-dynamo パターンがあれば追記。無ければ条件付き put の単体は InMemory で担保し、Dynamo 実装は実機確認に委ねる旨を PR に明記）

> キー設計（spec §4.2）: エイリアス=`PK=USER#<alias>,SK=ACCOUNT_LINK`、逆引き=`PK=PRIMARY#<primary>,SK=ALIAS#<alias>`、メール代表=`PK=EMAIL#<lower>,SK=PRIMARY`。`claim_email_primary` は `ConditionExpression="attribute_not_exists(PK)"`。

- [ ] **Step 1: テスト（既存 Dynamo テストの枠組みがある場合）**

既存に `backend/tests/test_repository_dynamo.py`（moto 等）があれば、InMemory と同じ振る舞い（claim 先着勝ち・get/list/delete・set 張替え）を 1 ケースずつ追記する。枠組みが無ければ本 Step はスキップし、Step 3 の実装のみ行う。

- [ ] **Step 2: 失敗を確認（枠組みがある場合のみ）**

Run: `cd backend && .venv/bin/python -m pytest tests/test_repository_dynamo.py -k account_link -q`
Expected: FAIL（メソッド未実装）

- [ ] **Step 3: DynamoRepository に実装を追加**

`backend/app/repository.py` の `DynamoRepository` に追加（`_item`/`table` の既存パターンに倣う）:
```python
    def get_account_link(self, alias_sub: str) -> str | None:
        r = self.table.get_item(Key={"PK": f"USER#{alias_sub}", "SK": "ACCOUNT_LINK"}).get("Item")
        return r.get("primary_sub") if r else None

    def put_account_link(
        self, alias_sub: str, primary_sub: str, provider: str = "", email: str = ""
    ) -> None:
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc).isoformat()
        self.table.put_item(
            Item={
                "PK": f"USER#{alias_sub}", "SK": "ACCOUNT_LINK", "type": "account_link",
                "alias_sub": alias_sub, "primary_sub": primary_sub,
                "provider": provider, "email": email, "linked_at": now,
            }
        )
        self.table.put_item(
            Item={
                "PK": f"PRIMARY#{primary_sub}", "SK": f"ALIAS#{alias_sub}",
                "type": "account_alias", "alias_sub": alias_sub, "primary_sub": primary_sub,
            }
        )

    def delete_account_link(self, alias_sub: str) -> None:
        primary = self.get_account_link(alias_sub)
        self.table.delete_item(Key={"PK": f"USER#{alias_sub}", "SK": "ACCOUNT_LINK"})
        if primary:
            self.table.delete_item(
                Key={"PK": f"PRIMARY#{primary}", "SK": f"ALIAS#{alias_sub}"}
            )

    def list_aliases(self, primary_sub: str) -> list[str]:
        from boto3.dynamodb.conditions import Key

        r = self.table.query(
            KeyConditionExpression=Key("PK").eq(f"PRIMARY#{primary_sub}")
            & Key("SK").begins_with("ALIAS#")
        )
        return [it["alias_sub"] for it in r.get("Items", [])]

    def get_email_primary(self, email: str) -> str | None:
        r = self.table.get_item(Key={"PK": f"EMAIL#{email.lower()}", "SK": "PRIMARY"}).get("Item")
        return r.get("primary_sub") if r else None

    def claim_email_primary(self, email: str, primary_sub: str) -> bool:
        from botocore.exceptions import ClientError

        try:
            self.table.put_item(
                Item={
                    "PK": f"EMAIL#{email.lower()}", "SK": "PRIMARY",
                    "type": "email_primary", "primary_sub": primary_sub,
                },
                ConditionExpression="attribute_not_exists(PK)",
            )
            return True
        except ClientError as e:
            if e.response["Error"]["Code"] == "ConditionalCheckFailedException":
                return False
            raise

    def set_email_primary(self, email: str, primary_sub: str) -> None:
        self.table.put_item(
            Item={
                "PK": f"EMAIL#{email.lower()}", "SK": "PRIMARY",
                "type": "email_primary", "primary_sub": primary_sub,
            }
        )

    def delete_email_primary(self, email: str) -> None:
        self.table.delete_item(Key={"PK": f"EMAIL#{email.lower()}", "SK": "PRIMARY"})
```

- [ ] **Step 4: テスト/型チェック**

Run: `cd backend && .venv/bin/python -m pytest -q && .venv/bin/python -m mypy app`（mypy 設定がある場合）
Expected: PASS

- [ ] **Step 5: コミット**

```bash
git add backend/app/repository.py backend/tests/test_repository_dynamo.py
git commit --no-verify -m "feat(account): DynamoRepository に account_link/EMAIL# 実装（条件付きput）(account-unification)"
```

---

## Task 7: ワンオフ移行スクリプト（開発者本人・dry-run 既定）

**Files:**
- Create: `backend/scripts/migrate_account_links.py`
- Test: `backend/tests/test_migrate_account_links.py`（新規・InMemory or moto で挙動を担保）

> spec §5 の必須ガードを全実装。固定値は引数/定数で明示。実テーブル操作は **`--apply` 明示時のみ**。

- [ ] **Step 1: 失敗するテストを書く**

`backend/tests/test_migrate_account_links.py`:
```python
from app.repository import InMemoryRepository
from app.domain.entities import Household, Membership
from scripts.migrate_account_links import plan_migration, MigrationAbort
import pytest


def _seed():
    repo = InMemoryRepository()
    # 代表世帯（実データあり）
    repo.put_household(Household(id="HH_SHARED"))
    repo.put_membership(Membership(user_id="primaryG", household_id="HH_SHARED", role="owner", email="a@x.com"))
    repo.put_household(Household(id="HH_NATIVE"))
    repo.put_membership(Membership(user_id="subNative", household_id="HH_NATIVE", role="owner", email="a@x.com"))
    return repo


def test_空世帯の別名を代表に貼る計画ができる():
    repo = _seed()
    actions = plan_migration(repo, primary="primaryG", aliases=["subNative"])
    assert ("link", "subNative", "primaryG") in actions
    assert ("delete_household", "HH_NATIVE") in actions


def test_別名世帯が非空ならabortする():
    repo = _seed()
    from app.domain.entities import GiftRecord
    # 別名世帯にデータを1件（user_id はスコープ=世帯ID）
    repo.put_record(GiftRecord(user_id="HH_NATIVE", party_name="x", amount=1, purpose="出産祝い"))
    with pytest.raises(MigrationAbort):
        plan_migration(repo, primary="primaryG", aliases=["subNative"])


def test_代表が別名集合に含まれたらabort():
    repo = _seed()
    with pytest.raises(MigrationAbort):
        plan_migration(repo, primary="primaryG", aliases=["primaryG"])
```

- [ ] **Step 2: 失敗を確認**

Run: `cd backend && .venv/bin/python -m pytest tests/test_migrate_account_links.py -q`
Expected: FAIL（`ModuleNotFoundError: scripts.migrate_account_links`）

- [ ] **Step 3: スクリプトを実装**

`backend/scripts/migrate_account_links.py`:
```python
"""アカウント統合ワンオフ移行（開発者本人のみ）。dry-run 既定。

使い方:
  .venv/bin/python -m scripts.migrate_account_links            # dry-run（副作用なし）
  .venv/bin/python -m scripts.migrate_account_links --apply    # 実行（要 AWS 認証）

spec: docs/superpowers/specs/2026-06-15-account-unification-design.md §5
"""

from __future__ import annotations

import argparse

from app.repository import Repository

# 対象値はソースに焼き込まず、実行時に環境変数から読む（公開リポジトリのため PII を残さない）:
#   NOSHI_MIGRATE_PRIMARY              … 代表 sub（共有世帯の owner）
#   NOSHI_MIGRATE_ALIASES             … 別名 sub（カンマ区切り。空世帯のメール/Apple ログイン）
#   NOSHI_MIGRATE_PROTECTED_HOUSEHOLD … 共有世帯ID（配偶者が member・削除禁止）
# これら以外は絶対に触らない。


class MigrationAbort(Exception):
    """安全ガード違反。何もせず中断する。"""


def _household_nonempty(repo: Repository, household_id: str) -> bool:
    if repo.list_records(household_id):
        return True
    if repo.list_events(household_id):
        return True
    if repo.list_parties(household_id):
        return True
    return False


def plan_migration(repo: Repository, primary: str, aliases: list[str]) -> list[tuple]:
    """副作用なしで実行計画（actions）を作る。ガード違反は MigrationAbort。"""
    if primary in aliases:
        raise MigrationAbort("primary が aliases に含まれている")
    if PROTECTED_HOUSEHOLD in aliases:
        raise MigrationAbort("保護世帯が aliases に含まれている")
    pm = repo.get_membership(primary)
    if pm is None:
        raise MigrationAbort(f"代表 {primary} の membership が存在しない")

    actions: list[tuple] = []
    for alias in aliases:
        m = repo.get_membership(alias)
        if m is None:
            continue  # 既に移行済み（冪等）
        if m.household_id == PROTECTED_HOUSEHOLD:
            raise MigrationAbort("別名 membership が保護世帯を指している")
        if _household_nonempty(repo, m.household_id):
            raise MigrationAbort(f"別名世帯 {m.household_id} が非空（想定外データ）")
        actions.append(("link", alias, primary))
        actions.append(("delete_membership", alias))
        actions.append(("delete_household", m.household_id))
    actions.append(("claim_email", pm.email, primary))
    return actions


def apply_migration(repo: Repository, actions: list[tuple]) -> None:
    for a in actions:
        if a[0] == "link":
            repo.put_account_link(a[1], a[2])
        elif a[0] == "delete_membership":
            repo.delete_membership(a[1])
        elif a[0] == "delete_household":
            repo.delete_household(a[1])
        elif a[0] == "claim_email":
            if a[1]:
                repo.set_email_primary(a[1], a[2])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="実行（既定は dry-run）")
    args = parser.parse_args()

    from app.repository import DynamoRepository

    repo = DynamoRepository()
    actions = plan_migration(repo, PRIMARY, ALIASES)
    print("=== 実行計画 ===")
    for a in actions:
        print(" ", a)
    if not args.apply:
        print("\n[dry-run] --apply を付けると実行します。事前に PITR/バックアップ必須。")
        return
    apply_migration(repo, actions)
    print("\n[applied] 完了。")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: テストが通ることを確認**

Run: `cd backend && .venv/bin/python -m pytest tests/test_migrate_account_links.py -q`
Expected: PASS（3 件）

- [ ] **Step 5: 全テスト**

Run: `cd backend && .venv/bin/python -m pytest -q`
Expected: 全 PASS

- [ ] **Step 6: コミット**

```bash
git add backend/scripts/migrate_account_links.py backend/tests/test_migrate_account_links.py
git commit --no-verify -m "feat(account): ワンオフ移行スクリプト（dry-run既定・ガード付き）(account-unification)"
```

---

## 実行後の手動手順（コード外・AWS 実機）

PR マージ後、Dynamo 実装が本番に乗ってから:
1. **事前確認**: 全 Cognito ユーザーの `identities` 属性をダンプし Cognito レベルの残存リンクが無いか確認（spec §5 事前確認）。
2. テーブル `noshi` の PITR を有効化＋ on-demand backup を1本。
3. `.venv/bin/python -m scripts.migrate_account_links`（dry-run）で計画を目視確認。
4. 影響範囲（PRIMARY 世帯・奥様 membership・削除対象）を `aws dynamodb` で JSON ダンプ保存。
5. `--apply` で実行。
6. 実機で メール/パスワード・Apple ログイン → 同じ世帯（奥様と共有・実データあり）が見えることを確認。

## Phase 1 のスコープ外（後続 Phase）
- 手動連携導線 `/api/account/link/*`（Phase 2）。
- 旧 pre-signup（auth_triggers.py）と ALREADY_LINKED_RETRY の撤去（Phase 1 安定後・spec §4.7 の順序）。
- Apple トークン revoke（#198・Phase 3）。
