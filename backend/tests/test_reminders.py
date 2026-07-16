"""お返し期限リマインド（#178）のテスト。

期限の近いイベントの抽出、メンバーのオプトアウト尊重、重複送信しない冪等性を検証する。
SES 送信は差し替え可能な send コールバックで分離し、AWS なしで純粋に検証する。
"""

import datetime

from app.ports import GiftCatalogMock, OcrLlmMock
from app.reminders import collect_household_due, run_reminders
from app.repository import InMemoryRepository
from app.services import NoshiService

TODAY = datetime.date(2026, 6, 13)


def _seed(svc: NoshiService, repo: InMemoryRepository, user="u1", email="a@example.com"):
    """user の世帯を作り、メンバーのメールを設定して世帯IDを返す。"""
    h = svc.resolve_household(user, email=email)
    m = repo.get_membership(user)
    assert m is not None
    m.email = email
    repo.put_membership(m)
    return h.id


def _due_event(svc, user, scope, *, party, due_offset, direction="received", status="received"):
    """お返し期限が today+due_offset 日のイベントを作る。期限は手動上書きで確定させる。

    given（あげた）は BR-3-GIVEN によりイベントを作らない＝リマインド対象外。
    """
    _, ev = svc.create_record(
        user, amount=10000, purpose="出産祝い", party_name=party, direction=direction
    )
    if ev is None:  # given はイベントなし。レコードだけ残してそのまま返す。
        return None
    due = (TODAY + datetime.timedelta(days=due_offset)).isoformat()
    svc.set_event_due(user, ev.id, due)
    if status != "received":
        svc.set_event_status(user, ev.id, status)
    return ev


def test_期限1週間前と当日のイベントだけを抽出する():
    repo = InMemoryRepository()
    svc = NoshiService(repo, OcrLlmMock(), GiftCatalogMock())
    scope = _seed(svc, repo)
    _due_event(svc, "u1", scope, party="1週間前さん", due_offset=7)
    _due_event(svc, "u1", scope, party="当日さん", due_offset=0)
    _due_event(svc, "u1", scope, party="3日前さん", due_offset=3)  # 対象外（7でも0でもない）
    _due_event(svc, "u1", scope, party="まだ先さん", due_offset=10)
    _due_event(svc, "u1", scope, party="超過さん", due_offset=-2)

    dues = collect_household_due(repo, scope, TODAY)
    names = sorted(d.party_name for d in dues)
    assert names == ["1週間前さん", "当日さん"]


def test_完了済みと贈った側は対象外():
    repo = InMemoryRepository()
    svc = NoshiService(repo, OcrLlmMock(), GiftCatalogMock())
    scope = _seed(svc, repo)
    _due_event(svc, "u1", scope, party="完了さん", due_offset=0, status="done")
    _due_event(svc, "u1", scope, party="あげたさん", due_offset=0, direction="given")
    assert collect_household_due(repo, scope, TODAY) == []


def test_対象メンバーへ1通送り重複送信しない():
    repo = InMemoryRepository()
    svc = NoshiService(repo, OcrLlmMock(), GiftCatalogMock())
    _seed(svc, repo, email="a@example.com")
    _due_event(svc, "u1", repo.get_membership("u1").household_id, party="田中", due_offset=7)

    sent: list[dict] = []
    n = run_reminders(repo, TODAY, lambda to, subject, html: sent.append({"to": to}))
    assert n == 1
    assert sent[0]["to"] == "a@example.com"

    # 同日に再実行しても、送信済みは重複しない（冪等）
    sent.clear()
    assert run_reminders(repo, TODAY, lambda to, subject, html: sent.append({"to": to})) == 0
    assert sent == []


def test_通知設定は既定オンで切替できる():
    repo = InMemoryRepository()
    svc = NoshiService(repo, OcrLlmMock(), GiftCatalogMock())
    svc.resolve_household("u1", email="a@example.com")
    # メール/プッシュとも既定オン（push は #205 で追加）。
    assert svc.notification_prefs("u1") == {"email": True, "push": True}
    # email のみ切替（push_on 省略時はプッシュ設定は据え置き）。
    assert svc.set_notification_prefs("u1", email_on=False) == {"email": False, "push": True}
    assert svc.notification_prefs("u1") == {"email": False, "push": True}
    assert repo.get_membership("u1").notify_email is False


def test_通知オフのメンバーには送らない():
    repo = InMemoryRepository()
    svc = NoshiService(repo, OcrLlmMock(), GiftCatalogMock())
    _seed(svc, repo, email="a@example.com")
    m = repo.get_membership("u1")
    m.notify_email = False
    repo.put_membership(m)
    _due_event(svc, "u1", m.household_id, party="田中", due_offset=0)

    sent: list[str] = []
    assert run_reminders(repo, TODAY, lambda to, subject, html: sent.append(to)) == 0
    assert sent == []
