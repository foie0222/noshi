"""API（BFF/FastAPI）のテスト。主要エンドポイントと本人スコープを検証する。"""

import pytest
from app.main import create_app
from app.ports import GiftCatalogMock, OcrLlmMock
from app.repository import InMemoryRepository
from app.services import NoshiService
from fastapi.testclient import TestClient


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
    r = c.post(
        "/api/records",
        headers=_h(),
        json={
            "amount": 30000,
            "purpose": "出産祝い",
            "party_name": "佐藤",
            "direction": "received",
        },
    )
    assert r.status_code == 200
    ledger = c.get("/api/ledger", headers=_h()).json()
    assert len(ledger["records"]) == 1


def test_あげた贈答を記録できイベントは作られない():
    """direction=given の記録作成が200で成功し、お返しイベントが作られない(null)ことを検証する（FR-8-1）。"""
    c = TestClient(create_app())
    r = c.post(
        "/api/records",
        headers=_h(),
        json={
            "amount": 5000,
            "purpose": "入学祝い",
            "party_name": "姪",
            "direction": "given",
            "occurred_at": "2026-04-01",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["event"] is None
    # 台帳には出るが pending には出ない
    assert len(c.get("/api/ledger", headers=_h()).json()["records"]) == 1
    assert c.get("/api/home", headers=_h()).json()["pending"] == []


def test_不正入力は422になる():
    """金額0の記録作成がバリデーションで422になることを検証する（BR-VAL/A03）。"""
    c = TestClient(create_app())
    r = c.post(
        "/api/records",
        headers=_h(),
        json={"amount": 0, "purpose": "出産祝い", "party_name": "佐藤", "direction": "received"},
    )
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
    c.post(
        "/api/records",
        headers=_h(),
        json={
            "amount": 50000,
            "purpose": "結婚祝い",
            "party_name": "いとこ",
            "direction": "received",
            "occurred_at": "2025-01-01",
        },
    )
    rows = c.get("/api/relationships", headers=_h()).json()["relationships"]
    row = next(r for r in rows if r["party_name"] == "いとこ")
    assert row["received"] == 50000 and row["status"] == "owe"
    assert row["attention"] is True  # 1年以上前


def test_贈与税サマリを返す():
    """GET /api/gift-tax が本人の対象合計・残額・超過を返すことを検証する（P1-3）。"""
    c = TestClient(create_app())
    import datetime

    y = datetime.date.today().year
    c.post(
        "/api/records",
        headers=_h(),
        json={
            "amount": 800000,
            "purpose": "新築祝い",
            "party_name": "親",
            "direction": "received",
            "occurred_at": f"{y}-03-01",
        },
    )
    c.post(
        "/api/records",
        headers=_h(),
        json={
            "amount": 300000,
            "purpose": "香典",
            "party_name": "知人",
            "direction": "received",
            "occurred_at": f"{y}-04-01",
        },
    )  # 除外
    body = c.get("/api/gift-tax", headers=_h()).json()
    assert body["total"] == 800000
    assert body["remaining"] == 300000 and body["over"] is False


def test_他人のイベントには触れない():
    """別ユーザーのイベントへのステータス更新が403で拒否されることを検証する（A01）。"""
    c = TestClient(create_app())
    rec = c.post(
        "/api/records",
        headers=_h("owner"),
        json={"amount": 10000, "purpose": "香典", "party_name": "田中", "direction": "received"},
    ).json()
    eid = rec["event"]["id"]
    r = c.patch(f"/api/events/{eid}", headers=_h("attacker"), json={"status": "done"})
    assert r.status_code == 403


def test_お返し期限をPUTで上書きし解除できる():
    """PUT /api/events/{id}/due で期限を上書きでき、null で既定に戻ることを検証する（#2）。"""
    c = TestClient(create_app())
    rec = c.post(
        "/api/records",
        headers=_h(),
        json={
            "amount": 10000,
            "purpose": "出産祝い",
            "party_name": "佐藤",
            "direction": "received",
            "occurred_at": "2026-05-01",
        },
    ).json()
    eid = rec["event"]["id"]
    # 上書き
    r = c.put(f"/api/events/{eid}/due", headers=_h(), json={"due_at": "2026-06-20"})
    assert r.status_code == 200
    ev = r.json()["event"]
    assert ev["due_at"] == "2026-06-20" and ev["due_overridden"] is True
    assert ev["due_default"] == "2026-05-31"
    # 解除（null で既定へ復帰）
    ev2 = c.put(f"/api/events/{eid}/due", headers=_h(), json={"due_at": None}).json()["event"]
    assert ev2["due_overridden"] is False and ev2["due_at"] == "2026-05-31"


def test_不正な期限のPUTは422になる():
    """YYYY-MM-DD でない期限の上書きが422で拒否されることを検証する（#2, BR-VAL/A03）。"""
    c = TestClient(create_app())
    rec = c.post(
        "/api/records",
        headers=_h(),
        json={
            "amount": 10000,
            "purpose": "出産祝い",
            "party_name": "佐藤",
            "direction": "received",
        },
    ).json()
    eid = rec["event"]["id"]
    r = c.put(f"/api/events/{eid}/due", headers=_h(), json={"due_at": "2026/06/20"})
    assert r.status_code == 422


def test_続柄マスタの取得と世帯独自の追加():
    """GET /api/relationship-master が既定を返し、POST で世帯独自の続柄を追加できることを検証する（#1）。"""
    c = TestClient(create_app())
    m = c.get("/api/relationship-master", headers=_h()).json()
    assert "親" in m["options"] and "友人" in m["options"]
    added = c.post("/api/relationship-master", headers=_h(), json={"name": "ママ友"}).json()
    assert "ママ友" in added["options"] and "ママ友" not in added["defaults"]


def test_続柄の追加は同じ世帯で共有され別世帯には見えない():
    """追加した続柄が同世帯の家族に共有され、別ユーザー（別世帯）には見えないことを検証する（#1, A01）。"""
    c = TestClient(create_app())
    code = c.get("/api/household", headers=_h("owner")).json()["household"]["invite_code"]
    c.post("/api/household/join", headers=_h("family"), json={"code": code})
    c.post("/api/relationship-master", headers=_h("owner"), json={"name": "茶道仲間"})
    assert "茶道仲間" in c.get("/api/relationship-master", headers=_h("family")).json()["options"]
    assert (
        "茶道仲間"
        not in c.get("/api/relationship-master", headers=_h("stranger")).json()["options"]
    )


def test_続柄の削除と上限():
    """DELETE で世帯独自の続柄を削除でき、上限(30)超過の追加が422になることを検証する（#1）。"""
    c = TestClient(create_app())
    c.post("/api/relationship-master", headers=_h(), json={"name": "ママ友"})
    after = c.delete("/api/relationship-master/ママ友", headers=_h()).json()
    assert "ママ友" not in after["options"]
    # 上限: 30件まで→31件目は422
    for i in range(30):
        c.post("/api/relationship-master", headers=_h(), json={"name": f"続柄{i}"})
    r = c.post("/api/relationship-master", headers=_h(), json={"name": "あふれる"})
    assert r.status_code == 422


def test_汎用エラーは内部情報を漏らさない():
    """403応答が内部情報（スタックトレース等）を含まない汎用メッセージであることを検証する（A03）。"""
    c = TestClient(create_app())
    r = c.patch("/api/events/nonexistent", headers=_h(), json={"status": "done"})
    assert r.status_code == 403
    assert "Traceback" not in r.text


def test_記録をPATCHで修正できる():
    """PATCH /api/records/{id} で金額・用途・相手(party_id)を修正でき、台帳に反映されることを検証する（#47）。"""
    c = TestClient(create_app())
    p2 = c.post("/api/parties", headers=_h(), json={"name": "佐藤花子"}).json()["party"]
    rid = c.post(
        "/api/records",
        headers=_h(),
        json={
            "amount": 10000,
            "purpose": "出産祝い",
            "party_name": "佐藤",
            "direction": "received",
        },
    ).json()["record"]["id"]
    r = c.patch(
        f"/api/records/{rid}",
        headers=_h(),
        json={"amount": 30000, "purpose": "結婚祝い", "party_id": p2["id"]},
    )
    assert r.status_code == 200
    assert r.json()["record"]["amount"] == 30000
    ledger = c.get("/api/ledger", headers=_h()).json()["records"]
    assert ledger[0]["amount"] == 30000 and ledger[0]["party_name"] == "佐藤花子"


def test_他人の記録はPATCHで修正できない():
    """他ユーザーのレコードへのPATCHが403で拒否されることを検証する（A01）。"""
    c = TestClient(create_app())
    rid = c.post(
        "/api/records",
        headers=_h("owner"),
        json={"amount": 10000, "purpose": "香典", "party_name": "田中", "direction": "received"},
    ).json()["record"]["id"]
    r = c.patch(
        f"/api/records/{rid}",
        headers=_h("attacker"),
        json={"amount": 1, "purpose": "香典", "party_name": "田中"},
    )
    assert r.status_code == 403


def test_年間振り返りを取得できる():
    """GET /api/annual が本人の指定年の受領件数・合計を返すことを検証する。"""
    c = TestClient(create_app())
    c.post(
        "/api/records",
        headers=_h(),
        json={
            "amount": 30000,
            "purpose": "出産祝い",
            "party_name": "佐藤",
            "direction": "received",
            "occurred_at": "2026-01-10",
        },
    )
    s = c.get("/api/annual?year=2026", headers=_h()).json()
    assert s["received_count"] == 1 and s["received_total"] == 30000


def test_記録修正で日付が消えない():
    """金額のみのPATCH修正で occurred_at が空に上書きされず保持されることを検証する（回帰）。"""
    c = TestClient(create_app())
    rid = c.post(
        "/api/records",
        headers=_h(),
        json={
            "amount": 50000,
            "purpose": "結婚祝い",
            "party_name": "高橋",
            "direction": "received",
            "occurred_at": "2026-04-10",
        },
    ).json()["record"]["id"]
    c.patch(
        f"/api/records/{rid}",
        headers=_h(),
        json={"amount": 55000, "purpose": "結婚祝い", "party_name": "高橋"},
    )
    rec = c.get("/api/ledger", headers=_h()).json()["records"][0]
    assert rec["amount"] == 55000
    assert rec["occurred_at"] == "2026-04-10"  # 日付は保持される


def test_世帯APIで招待コードを取得し家族が参加して共有できる():
    """X-User-Id 認証で、招待コードを取得→別ユーザーが参加→台帳を共有できることをHTTPで検証する。"""
    c = TestClient(create_app())
    # 太郎が記録 → 世帯が自動作成
    c.post(
        "/api/records",
        headers=_h("taro"),
        json={
            "amount": 30000,
            "purpose": "出産祝い",
            "party_name": "佐藤",
            "direction": "received",
        },
    )
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
    c.post(
        "/api/records",
        headers=_h("taro"),
        json={
            "amount": 30000,
            "purpose": "出産祝い",
            "party_name": "佐藤",
            "direction": "received",
        },
    )
    assert c.get("/api/ledger", headers=_h("stranger")).json()["records"] == []


def test_JWT構成時はBearerトークンで認証する(monkeypatch):
    """NOSHI_JWT_SECRET 構成時、Bearer の HS256 トークンで認証できることを検証する。"""
    import time

    import jwt

    secret = "test-secret-at-least-32-bytes-long-xxxx"
    monkeypatch.setenv("NOSHI_JWT_SECRET", secret)
    c = TestClient(create_app())
    tok = jwt.encode(
        {"sub": "user-xyz", "email": "z@x.jp", "exp": int(time.time()) + 3600},
        secret,
        algorithm="HS256",
    )
    r = c.get("/api/household", headers={"Authorization": f"Bearer {tok}"})
    assert r.status_code == 200
    # email がメンバーに反映される
    assert r.json()["household"]["members"][0]["email"] == "z@x.jp"


def test_脱退とメンバー削除のHTTP():
    """HTTPで、参加→管理者がメンバー削除→相手が脱退の流れと世帯境界を検証する。"""
    c = TestClient(create_app())
    c.post(
        "/api/records",
        headers=_h("taro"),
        json={
            "amount": 30000,
            "purpose": "出産祝い",
            "party_name": "佐藤",
            "direction": "received",
        },
    )
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


def test_用途マスタの取得追加削除():
    """GET/POST/DELETE /api/purpose-master が機能することを検証する（#37）。"""
    c = TestClient(create_app())
    m = c.get("/api/purpose-master", headers=_h()).json()
    assert "出産祝い" in m["options"]
    added = c.post("/api/purpose-master", headers=_h(), json={"name": "発表会祝い"}).json()
    assert "発表会祝い" in added["options"] and "発表会祝い" not in added["defaults"]
    after = c.delete("/api/purpose-master/発表会祝い", headers=_h()).json()
    assert "発表会祝い" not in after["options"]


def test_あげた記録もタップで詳細が取れる():
    """GET /api/records/{id}/event が given 記録でも 200 で詳細を返すことを検証する（#48）。"""
    c = TestClient(create_app())
    rid = c.post(
        "/api/records",
        headers=_h(),
        json={"amount": 5000, "purpose": "入学祝い", "party_name": "姪", "direction": "given"},
    ).json()["record"]["id"]
    r = c.get(f"/api/records/{rid}/event", headers=_h())
    assert r.status_code == 200
    ev = r.json()["event"]
    assert ev["direction"] == "given" and ev["id"] == "" and ev["record_id"] == rid


def test_クリック計測は204を返す(client):
    r = client.post(
        "/api/suggestions/click",
        json={"item_code": "shop:1", "bucket": "BUCKET#baby#5000-9999", "position": 1},
        headers={"X-User-Id": "demo-user"},
    )
    assert r.status_code == 204


def test_クリック計測は不正なバケツ形式を拒否する(client):
    r = client.post(
        "/api/suggestions/click",
        json={"item_code": "shop:1", "bucket": "DROP TABLE", "position": 1},
        headers={"X-User-Id": "demo-user"},
    )
    assert r.status_code == 422


def test_クリック計測は未認証を拒否する(client):
    r = client.post(
        "/api/suggestions/click",
        json={"item_code": "shop:1", "bucket": "BUCKET#baby#5000-9999", "position": 1},
    )
    assert r.status_code == 401


def test_クリック計測はカタログの失敗でも204を返す():
    """計測の失敗がUXをブロックしない（log_click が例外でも 204）ことを検証する。"""
    from app.ports import GiftCatalogMock, OcrLlmMock
    from app.repository import InMemoryRepository
    from app.services import NoshiService

    class FailingCatalog(GiftCatalogMock):
        def log_click(self, item_code: str, bucket: str, position: int, rel_group: str) -> None:
            raise RuntimeError("boom")

    svc = NoshiService(InMemoryRepository(), OcrLlmMock(), FailingCatalog())
    c = TestClient(create_app(service=svc))
    r = c.post(
        "/api/suggestions/click",
        json={"item_code": "shop:1", "bucket": "BUCKET#baby#5000-9999", "position": 1},
        headers=_h(),
    )
    assert r.status_code == 204


def test_クリック計測はrel_groupつきで204を返す(client):
    r = client.post(
        "/api/suggestions/click",
        json={
            "item_code": "shop:1",
            "bucket": "BUCKET#baby#5000-9999",
            "position": 1,
            "rel_group": "family",
        },
        headers={"X-User-Id": "demo-user"},
    )
    assert r.status_code == 204


def test_クリック計測は不正なrel_groupを拒否する(client):
    r = client.post(
        "/api/suggestions/click",
        json={
            "item_code": "shop:1",
            "bucket": "BUCKET#baby#5000-9999",
            "position": 1,
            "rel_group": "boss",
        },
        headers={"X-User-Id": "demo-user"},
    )
    assert r.status_code == 422


def test_相手APIで同名でも別人を作り集計が分離する():
    """POST /api/parties で同名の別人を作り、記録を紐付けるとおつきあいが別エントリになることを検証する（#47）。"""
    c = TestClient(create_app())
    a = c.post("/api/parties", headers=_h(), json={"name": "田中", "relationship": "友人"}).json()[
        "party"
    ]
    b = c.post("/api/parties", headers=_h(), json={"name": "田中", "relationship": "会社"}).json()[
        "party"
    ]
    assert a["id"] != b["id"]
    for pid in (a["id"], b["id"]):
        c.post(
            "/api/records",
            headers=_h(),
            json={
                "amount": 10000,
                "purpose": "出産祝い",
                "party_id": pid,
                "direction": "received",
                "occurred_at": "2026-03-01",
            },
        )
    rels = c.get("/api/relationships", headers=_h()).json()["relationships"]
    assert len([r for r in rels if r["party_name"] == "田中"]) == 2
    assert len(c.get("/api/parties", headers=_h()).json()["parties"]) == 2


def test_別名subのリクエストは代表の世帯に解決される():
    svc = NoshiService(InMemoryRepository(), OcrLlmMock(), GiftCatalogMock())
    c = TestClient(create_app(svc))
    svc.resolve_household("primaryX", email="a@x.com", email_verified=True)
    svc.repo.put_account_link("aliasY", "primaryX", email="a@x.com")
    r = c.get("/api/household", headers={"X-User-Id": "aliasY"})
    assert r.status_code == 200
    assert svc.repo.get_membership("aliasY") is None


def test_別名subの通知設定変更が代表の設定に反映される():
    svc = NoshiService(InMemoryRepository(), OcrLlmMock(), GiftCatalogMock())
    c = TestClient(create_app(svc))
    svc.resolve_household("primaryX", email="a@x.com", email_verified=True)
    svc.set_notification_prefs("primaryX", False)
    svc.repo.put_account_link("aliasY", "primaryX", email="a@x.com")
    r = c.put("/api/notifications", json={"email": True}, headers={"X-User-Id": "aliasY"})
    assert r.status_code == 200
    assert svc.repo.get_membership("aliasY") is None
    primary_m = svc.repo.get_membership("primaryX")
    assert primary_m is not None and primary_m.notify_email is True


def test_delete_info_はapple連携有無を返す(monkeypatch):
    import app.auth as auth
    import app.cognito_admin as ca

    svc = NoshiService(InMemoryRepository(), OcrLlmMock(), GiftCatalogMock())
    svc.resolve_household("primaryX", email="a@x.com", email_verified=True)
    svc.repo.put_account_link("aliasApple", "primaryX")
    monkeypatch.setattr(ca, "any_apple_sub", lambda pool, subs: "aliasApple" in subs)
    monkeypatch.setattr(auth, "auth_configured", lambda: False)  # X-User-Id スタブを維持
    monkeypatch.setenv("NOSHI_COGNITO_POOL_ID", "pool-1")
    c = TestClient(create_app(svc))
    r = c.get("/api/account/delete-info", headers={"X-User-Id": "primaryX"})
    assert r.status_code == 200 and r.json()["apple_linked"] is True


def test_delete_account_はrevokeと全sub削除を呼ぶ(monkeypatch):
    import app.apple_revoke as ar
    import app.auth as auth
    import app.cognito_admin as ca

    calls = {"revoke": None, "deleted": None}
    monkeypatch.setattr(
        ar, "revoke_apple_for_code", lambda code: calls.__setitem__("revoke", code) or True
    )
    monkeypatch.setattr(
        ca, "delete_users_by_subs", lambda pool, subs: calls.__setitem__("deleted", list(subs))
    )
    monkeypatch.setattr(auth, "auth_configured", lambda: False)  # X-User-Id スタブを維持
    monkeypatch.setenv("NOSHI_COGNITO_POOL_ID", "pool-1")
    svc = NoshiService(InMemoryRepository(), OcrLlmMock(), GiftCatalogMock())
    svc.resolve_household("primaryX", email="a@x.com", email_verified=True)
    svc.repo.put_account_link("aliasA", "primaryX")
    c = TestClient(create_app(svc))
    r = c.request(
        "DELETE",
        "/api/account",
        json={"apple_authorization_code": "code-xyz"},
        headers={"X-User-Id": "primaryX"},
    )
    assert r.status_code == 200 and r.json()["ok"] is True
    assert calls["revoke"] == "code-xyz"
    assert set(calls["deleted"]) == {"primaryX", "aliasA"}
