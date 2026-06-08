"""データ層（InMemoryRepository）のテスト。本人スコープと CRUD を検証する。"""

from app.domain.entities import GiftEvent, GiftRecord
from app.repository import InMemoryRepository


def test_レコードを保存して本人が取得できる():
    """保存した贈答レコードを所有者本人が取得できることを検証する。"""
    repo = InMemoryRepository()
    rec = GiftRecord(user_id="u1", party_name="佐藤", amount=30000, purpose="出産祝い")
    repo.put_record(rec)
    got = repo.get_record("u1", rec.id)
    assert got is not None and got.amount == 30000


def test_他人のレコードは取得できない():
    """他ユーザーは他人の贈答レコードを取得できないことを検証する（A01 本人スコープ）。"""
    repo = InMemoryRepository()
    rec = GiftRecord(user_id="u1", party_name="佐藤", amount=30000, purpose="出産祝い")
    repo.put_record(rec)
    assert repo.get_record("u2", rec.id) is None


def test_一覧は本人のレコードだけを返す():
    """レコード一覧が要求した本人のものだけを返すことを検証する（A01）。"""
    repo = InMemoryRepository()
    repo.put_record(GiftRecord(user_id="u1", party_name="A", amount=1000, purpose="香典"))
    repo.put_record(GiftRecord(user_id="u2", party_name="B", amount=2000, purpose="香典"))
    assert len(repo.list_records("u1")) == 1


def test_未完了イベントはdoneを除外する():
    """未完了イベント一覧が status=done のイベントを除外することを検証する（BR-EVT-2）。"""
    repo = InMemoryRepository()
    e1 = GiftEvent(user_id="u1", record_id="r1", status="considering")
    e2 = GiftEvent(user_id="u1", record_id="r2", status="done")
    repo.put_event(e1)
    repo.put_event(e2)
    pending = repo.list_pending_events("u1")
    assert [e.id for e in pending] == [e1.id]
