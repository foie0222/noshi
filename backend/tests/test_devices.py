"""デバイストークン（iOS プッシュ通知の宛先）のテスト（#205）。

APNs デバイストークンの登録/一覧/削除と本人スコープ、通知設定の push トグル、
アカウント削除時のトークン削除を検証する。プッシュ送信処理自体は本Issueの対象外
（送信方式 SNS/直APNs は未決のため）。
"""

from app.domain.entities import DeviceToken
from app.main import create_app
from app.ports import GiftCatalogMock, OcrLlmMock
from app.repository import InMemoryRepository
from app.services import NoshiService
from fastapi.testclient import TestClient


def make() -> NoshiService:
    return NoshiService(InMemoryRepository(), OcrLlmMock(), GiftCatalogMock())


def _h(uid: str = "u1") -> dict[str, str]:
    return {"X-User-Id": uid}


# --- repository（本人スコープ・CRUD・upsert）---
def test_デバイストークンを保存して本人が一覧できる() -> None:
    """保存したデバイストークンを所有者本人が一覧取得できることを検証する。"""
    repo = InMemoryRepository()
    repo.put_device_token(DeviceToken(user_id="u1", token="abc"))
    assert [t.token for t in repo.list_device_tokens("u1")] == ["abc"]


def test_他人のデバイストークンは一覧に出ない() -> None:
    """他ユーザーのトークンは本人の一覧に混ざらないことを検証する（本人スコープ）。"""
    repo = InMemoryRepository()
    repo.put_device_token(DeviceToken(user_id="u1", token="abc"))
    assert repo.list_device_tokens("u2") == []


def test_同じトークンの再登録は重複せず更新される() -> None:
    """OS によるトークン再発行に追従して upsert され重複しないことを検証する。"""
    repo = InMemoryRepository()
    repo.put_device_token(DeviceToken(user_id="u1", token="abc", env="sandbox"))
    repo.put_device_token(DeviceToken(user_id="u1", token="abc", env="prod"))
    tokens = repo.list_device_tokens("u1")
    assert len(tokens) == 1 and tokens[0].env == "prod"


def test_デバイストークンを個別削除できる() -> None:
    """無効トークン（410/Unregistered）の削除に使う個別削除を検証する。"""
    repo = InMemoryRepository()
    repo.put_device_token(DeviceToken(user_id="u1", token="abc"))
    repo.put_device_token(DeviceToken(user_id="u1", token="def"))
    assert repo.delete_device_token("u1", "abc") is True
    assert [t.token for t in repo.list_device_tokens("u1")] == ["def"]


def test_本人の全デバイストークンを一括削除できる() -> None:
    """アカウント削除時に本人の全トークンを消すための一括削除を検証する。"""
    repo = InMemoryRepository()
    repo.put_device_token(DeviceToken(user_id="u1", token="abc"))
    repo.put_device_token(DeviceToken(user_id="u1", token="def"))
    assert repo.delete_device_tokens("u1") == 2
    assert repo.list_device_tokens("u1") == []


# --- service ---
def test_サービス経由でトークン登録と一覧() -> None:
    """サービス層でトークンを登録し本人分を一覧できることを検証する。"""
    svc = make()
    svc.register_device_token("u1", "abc")
    assert [t.token for t in svc.list_device_tokens("u1")] == ["abc"]


def test_アカウント削除でデバイストークンも消える() -> None:
    """アカウント削除でトークンが削除され、以後の宛先に残らないことを検証する（#198接続）。"""
    svc = make()
    svc.resolve_household("u1")
    svc.register_device_token("u1", "abc")
    svc.delete_account("u1")
    assert svc.list_device_tokens("u1") == []


def test_プッシュ通知設定は既定オンで切り替えできる() -> None:
    """push 設定が既定オンで、email を据え置いたまま push のみ切り替えられることを検証する。"""
    svc = make()
    svc.resolve_household("u1")
    prefs = svc.notification_prefs("u1")
    assert prefs["push"] is True and prefs["email"] is True
    svc.set_notification_prefs("u1", email_on=True, push_on=False)
    after = svc.notification_prefs("u1")
    assert after["push"] is False and after["email"] is True


# --- API ---
def test_APIでデバイストークンを登録できる() -> None:
    """POST /api/devices でトークンを登録できることを検証する。"""
    c = TestClient(create_app())
    r = c.post(
        "/api/devices", headers=_h(), json={"token": "abc", "platform": "ios", "env": "prod"}
    )
    assert r.status_code == 200 and r.json()["ok"] is True


def test_認証なしのトークン登録は拒否される() -> None:
    """認証ヘッダなしのトークン登録が 401 で拒否されることを検証する（A07）。"""
    c = TestClient(create_app())
    assert c.post("/api/devices", json={"token": "abc"}).status_code == 401


def test_APIでデバイストークンを削除できる() -> None:
    """DELETE /api/devices/{token} でログアウト時等にトークンを削除できることを検証する。"""
    c = TestClient(create_app())
    c.post("/api/devices", headers=_h(), json={"token": "abc"})
    r = c.request("DELETE", "/api/devices/abc", headers=_h())
    assert r.status_code == 200 and r.json()["ok"] is True


def test_APIでプッシュ通知をオフにできる() -> None:
    """PUT /api/notifications で push をオフにでき、email が維持されることを検証する。"""
    c = TestClient(create_app())
    r = c.put("/api/notifications", headers=_h(), json={"email": True, "push": False})
    assert r.status_code == 200
    body = r.json()
    assert body["push"] is False and body["email"] is True
