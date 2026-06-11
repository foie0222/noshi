"""撮影画像（S3・署名付きURL）のテスト（#35）。署名はローカルで行われるため moto 不要。"""

from app.images import ImageStore
from app.main import create_app
from app.ports import GiftCatalogMock, OcrLlmMock
from app.repository import InMemoryRepository
from app.services import NoshiService
from fastapi.testclient import TestClient


def make_service(bucket: str | None = None) -> NoshiService:
    return NoshiService(InMemoryRepository(), OcrLlmMock(), GiftCatalogMock(), ImageStore(bucket))


def test_バケット未設定なら画像機能は無効():
    """NOSHI_IMAGE_BUCKET 相当が空なら enabled() が False になることを検証する。"""
    assert ImageStore("").enabled() is False
    assert ImageStore("noshi-images").enabled() is True


def test_アップロードは世帯スコープのキーとサイズ上限つき署名POSTを返す():
    """image_upload_url が世帯スコープのキーと、content-length-range 条件つきの署名POST(url/fields)を返すことを検証する。"""
    import base64
    import json

    svc = make_service("noshi-images")
    out = svc.image_upload_url("u1", "image/jpeg")
    assert out["key"].endswith(".jpg") and "households/" in out["key"]
    assert out["url"].startswith("https://")
    assert out["fields"]["key"] == out["key"]
    # ポリシーに content-length-range（サイズ上限）が含まれる（サーバ側でサイズを強制）
    policy = json.loads(base64.b64decode(out["fields"]["policy"]))
    assert any(isinstance(c, list) and c[0] == "content-length-range" for c in policy["conditions"])


def test_非対応の画像形式は拒否される():
    """対応外 MIME のアップロードURL要求が ValidationError になることを検証する。"""
    import pytest
    from app.services import ValidationError

    svc = make_service("noshi-images")
    with pytest.raises(ValidationError):
        svc.image_upload_url("u1", "application/pdf")


def test_イベントビューは画像キーがあれば署名GET_URLを含む():
    """記録に image_key があると event_view が署名付き GET URL(image_url) を返すことを検証する。"""
    svc = make_service("noshi-images")
    _, ev = svc.create_record(
        "u1",
        amount=10000,
        purpose="出産祝い",
        party_name="佐藤",
        direction="received",
        image_key="households/h/abc.jpg",
    )
    v = svc.event_view("u1", ev.id)
    assert v["image_url"] and "abc.jpg" in v["image_url"]


def test_画像未設定や画像なしは_image_urlがNone():
    """画像が無い、または S3 無効なら image_url が None であることを検証する（後方互換）。"""
    svc_no_img = make_service("")  # S3 無効
    _, ev = svc_no_img.create_record(
        "u1", amount=10000, purpose="出産祝い", party_name="佐藤", direction="received"
    )
    assert svc_no_img.event_view("u1", ev.id)["image_url"] is None


def test_記録修正で画像を差し替え_削除できる():
    """update_record で image_key を差し替え/削除できることを検証する（#35）。"""
    svc = make_service("noshi-images")
    rec, ev = svc.create_record(
        "u1",
        amount=10000,
        purpose="出産祝い",
        party_name="佐藤",
        direction="received",
        image_key="households/h/old.jpg",
    )
    svc.update_record(
        "u1",
        rec.id,
        amount=10000,
        purpose="出産祝い",
        party_name="佐藤",
        image_key="households/h/new.jpg",
    )
    assert (
        svc.event_view("u1", ev.id)["image_url"]
        and "new.jpg" in svc.event_view("u1", ev.id)["image_url"]
    )
    svc.update_record(
        "u1", rec.id, amount=10000, purpose="出産祝い", party_name="佐藤", image_key=""
    )
    assert svc.event_view("u1", ev.id)["image_url"] is None


def test_API_S3未設定ならアップロードURLは501():
    """S3 未設定のデフォルト環境では POST /api/images/upload-url が 501 を返すことを検証する。"""
    c = TestClient(create_app())  # 既定: NOSHI_IMAGE_BUCKET 未設定
    r = c.post(
        "/api/images/upload-url", headers={"X-User-Id": "u1"}, json={"content_type": "image/jpeg"}
    )
    assert r.status_code == 501


def test_API_S3設定済みならアップロードPOSTを返す():
    """S3 設定済みサービスを注入すると 200 で url/fields/key を返すことを検証する。"""
    app = create_app(service=make_service("noshi-images"))
    c = TestClient(app)
    r = c.post(
        "/api/images/upload-url", headers={"X-User-Id": "u1"}, json={"content_type": "image/jpeg"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["url"].startswith("https://")
    assert body["fields"]["key"] == body["key"]
