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


def test_あげた贈答を記録できイベントは作られない():
    """direction=given の記録作成が200で成功し、お返しイベントが作られない(null)ことを検証する（FR-8-1）。"""
    c = TestClient(create_app())
    r = c.post("/api/records", headers=_h(), json={
        "amount": 5000, "purpose": "入学祝い", "party_name": "姪", "direction": "given",
        "occurred_at": "2026-04-01"})
    assert r.status_code == 200
    body = r.json()
    assert body["event"] is None
    # 台帳には出るが pending には出ない
    assert len(c.get("/api/ledger", headers=_h()).json()["records"]) == 1
    assert c.get("/api/home", headers=_h()).json()["pending"] == []


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


def test_おつきあいバランスを返す():
    """GET /api/relationships が相手別の差分と気になる関係フラグを返すことを検証する（N1）。"""
    c = TestClient(create_app())
    c.post("/api/records", headers=_h(), json={
        "amount": 50000, "purpose": "結婚祝い", "party_name": "いとこ", "direction": "received",
        "occurred_at": "2025-01-01"})
    rows = c.get("/api/relationships", headers=_h()).json()["relationships"]
    row = next(r for r in rows if r["party_name"] == "いとこ")
    assert row["received"] == 50000 and row["status"] == "owe"
    assert row["attention"] is True  # 1年以上前


def test_贈与税サマリを返す():
    """GET /api/gift-tax が本人の対象合計・残額・超過を返すことを検証する（P1-3）。"""
    c = TestClient(create_app())
    import datetime
    y = datetime.date.today().year
    c.post("/api/records", headers=_h(), json={
        "amount": 800000, "purpose": "新築祝い", "party_name": "親", "direction": "received",
        "occurred_at": f"{y}-03-01"})
    c.post("/api/records", headers=_h(), json={
        "amount": 300000, "purpose": "香典", "party_name": "知人", "direction": "received",
        "occurred_at": f"{y}-04-01"})  # 除外
    body = c.get("/api/gift-tax", headers=_h()).json()
    assert body["total"] == 800000
    assert body["remaining"] == 300000 and body["over"] is False


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


def test_記録をPATCHで修正できる():
    """PATCH /api/records/{id} で金額・相手を修正でき、台帳に反映されることを検証する。"""
    c = TestClient(create_app())
    rid = c.post("/api/records", headers=_h(), json={
        "amount": 10000, "purpose": "出産祝い", "party_name": "佐藤", "direction": "received"}).json()["record"]["id"]
    r = c.patch(f"/api/records/{rid}", headers=_h(), json={
        "amount": 30000, "purpose": "結婚祝い", "party_name": "佐藤花子"})
    assert r.status_code == 200
    assert r.json()["record"]["amount"] == 30000
    ledger = c.get("/api/ledger", headers=_h()).json()["records"]
    assert ledger[0]["amount"] == 30000 and ledger[0]["party_name"] == "佐藤花子"


def test_他人の記録はPATCHで修正できない():
    """他ユーザーのレコードへのPATCHが403で拒否されることを検証する（A01）。"""
    c = TestClient(create_app())
    rid = c.post("/api/records", headers=_h("owner"), json={
        "amount": 10000, "purpose": "香典", "party_name": "田中", "direction": "received"}).json()["record"]["id"]
    r = c.patch(f"/api/records/{rid}", headers=_h("attacker"), json={
        "amount": 1, "purpose": "香典", "party_name": "田中"})
    assert r.status_code == 403


def test_年間振り返りを取得できる():
    """GET /api/annual が本人の指定年の受領件数・合計を返すことを検証する。"""
    c = TestClient(create_app())
    c.post("/api/records", headers=_h(), json={
        "amount": 30000, "purpose": "出産祝い", "party_name": "佐藤",
        "direction": "received", "occurred_at": "2026-01-10"})
    s = c.get("/api/annual?year=2026", headers=_h()).json()
    assert s["received_count"] == 1 and s["received_total"] == 30000


def test_記録修正で日付が消えない():
    """金額のみのPATCH修正で occurred_at が空に上書きされず保持されることを検証する（回帰）。"""
    c = TestClient(create_app())
    rid = c.post("/api/records", headers=_h(), json={
        "amount": 50000, "purpose": "結婚祝い", "party_name": "高橋",
        "direction": "received", "occurred_at": "2026-04-10"}).json()["record"]["id"]
    c.patch(f"/api/records/{rid}", headers=_h(), json={
        "amount": 55000, "purpose": "結婚祝い", "party_name": "高橋"})
    rec = c.get("/api/ledger", headers=_h()).json()["records"][0]
    assert rec["amount"] == 55000
    assert rec["occurred_at"] == "2026-04-10"  # 日付は保持される


def test_世帯APIで招待コードを取得し家族が参加して共有できる():
    """X-User-Id 認証で、招待コードを取得→別ユーザーが参加→台帳を共有できることをHTTPで検証する。"""
    c = TestClient(create_app())
    # 太郎が記録 → 世帯が自動作成
    c.post("/api/records", headers=_h("taro"), json={
        "amount": 30000, "purpose": "出産祝い", "party_name": "佐藤", "direction": "received"})
    code = c.get("/api/household", headers=_h("taro")).json()["household"]["invite_code"]
    # 花子が招待コードで参加
    r = c.post("/api/household/join", headers=_h("hanako"), json={"code": code})
    assert r.status_code == 200
    # 花子からも太郎の記録が見える（共有）
    ledger = c.get("/api/ledger", headers=_h("hanako")).json()["records"]
    assert len(ledger) == 1 and ledger[0]["party_name"] == "佐藤"
    # メンバーが2人
    members = c.get("/api/household", headers=_h("taro")).json()["household"]["members"]
    assert {m["user_id"] for m in members} == {"taro", "hanako"}


def test_別世帯のユーザーには台帳が見えない():
    """同じ世帯に参加していないユーザーには台帳が見えないことを検証する（世帯境界）。"""
    c = TestClient(create_app())
    c.post("/api/records", headers=_h("taro"), json={
        "amount": 30000, "purpose": "出産祝い", "party_name": "佐藤", "direction": "received"})
    assert c.get("/api/ledger", headers=_h("stranger")).json()["records"] == []


def test_JWT構成時はBearerトークンで認証する(monkeypatch):
    """NOSHI_JWT_SECRET 構成時、Bearer の HS256 トークンで認証できることを検証する。"""
    import time, jwt
    secret = "test-secret-at-least-32-bytes-long-xxxx"
    monkeypatch.setenv("NOSHI_JWT_SECRET", secret)
    c = TestClient(create_app())
    tok = jwt.encode({"sub": "user-xyz", "email": "z@x.jp", "exp": int(time.time()) + 3600},
                     secret, algorithm="HS256")
    r = c.get("/api/household", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    # email がメンバーに反映される
    assert r.json()["household"]["members"][0]["email"] == "z@x.jp"


def test_脱退とメンバー削除のHTTP():
    """HTTPで、参加→管理者がメンバー削除→相手が脱退の流れと世帯境界を検証する。"""
    c = TestClient(create_app())
    c.post("/api/records", headers=_h("taro"), json={
        "amount": 30000, "purpose": "出産祝い", "party_name": "佐藤", "direction": "received"})
    code = c.get("/api/household", headers=_h("taro")).json()["household"]["invite_code"]
    c.post("/api/household/join", headers=_h("hanako"), json={"code": code})
    assert len(c.get("/api/ledger", headers=_h("hanako")).json()["records"]) == 1
    # 管理者(taro)が hanako を外す
    r = c.delete("/api/household/members/hanako", headers=_h("taro"))
    assert r.status_code == 200
    assert {m["user_id"] for m in r.json()["household"]["members"]} == {"taro"}
    assert c.get("/api/ledger", headers=_h("hanako")).json()["records"] == []
    # 管理者以外は他人を外せない（jiro が参加して taro を外そうとする）
    c.post("/api/household/join", headers=_h("jiro"), json={"code": code})
    assert c.delete("/api/household/members/taro", headers=_h("jiro")).status_code == 403
    # jiro 自身が脱退 → taro の台帳が見えなくなる
    c.post("/api/household/leave", headers=_h("jiro"))
    assert c.get("/api/ledger", headers=_h("jiro")).json()["records"] == []
