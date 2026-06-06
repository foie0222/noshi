"""API（BFF/FastAPI）のテスト。主要エンドポイントと本人スコープを検証する。"""
import pytest
from fastapi.testclient import TestClient
from app.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


def _h(uid="u1"):
    return {"X-User-Id": uid}


def test_認証なしは拒否される():
    """X-User-Idヘッダなしのリクエストが401で拒否されることを検証する（A07/A01）。"""
    c = TestClient(create_app())
    assert c.get("/api/ledger").status_code == 401


def test_記録作成して台帳に出る():
    """POST /api/records で記録を作成し、GET /api/ledger に反映されることを検証する。"""
    c = TestClient(create_app())
    r = c.post("/api/records", headers=_h(), json={
        "amount": 30000, "purpose": "出産祝い", "party_name": "佐藤", "direction": "received"})
    assert r.status_code == 200
    ledger = c.get("/api/ledger", headers=_h()).json()
    assert len(ledger["records"]) == 1


def test_不正入力は422になる():
    """金額0の記録作成がバリデーションで422になることを検証する（BR-VAL/A03）。"""
    c = TestClient(create_app())
    r = c.post("/api/records", headers=_h(), json={
        "amount": 0, "purpose": "出産祝い", "party_name": "佐藤", "direction": "received"})
    assert r.status_code == 422


def test_半返しエンドポイント():
    """GET /api/returns/half-return が推奨額と根拠を返すことを検証する（S-5）。"""
    c = TestClient(create_app())
    r = c.get("/api/returns/half-return", headers=_h(), params={"amount": 10000, "purpose": "香典"})
    assert r.status_code == 200
    body = r.json()
    assert body["recommended"] == 5000 and body["rationale"]


def test_他人のイベントには触れない():
    """別ユーザーのイベントへのステータス更新が403で拒否されることを検証する（A01）。"""
    c = TestClient(create_app())
    rec = c.post("/api/records", headers=_h("owner"), json={
        "amount": 10000, "purpose": "香典", "party_name": "田中", "direction": "received"}).json()
    eid = rec["event"]["id"]
    r = c.patch(f"/api/events/{eid}", headers=_h("attacker"), json={"status": "done"})
    assert r.status_code == 403


def test_汎用エラーは内部情報を漏らさない():
    """403応答が内部情報（スタックトレース等）を含まない汎用メッセージであることを検証する（A03）。"""
    c = TestClient(create_app())
    r = c.patch("/api/events/nonexistent", headers=_h(), json={"status": "done"})
    assert r.status_code == 403
    assert "Traceback" not in r.text
