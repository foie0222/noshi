"""DynamoRepository のテスト（moto でDynamoDBをモック）。

永続化バックエンドが InMemory と同じ契約（本人スコープ・CRUD）を満たし、
DynamoDB の型（Decimal）を跨いでも金額が int として復元され、float を含む
ジョブも保存できることを検証する。
"""

import pytest
from app.domain.entities import ExtractionJob, GiftEvent, GiftRecord
from app.repository import DynamoRepository, create_table
from moto import mock_aws


@pytest.fixture
def table_name():
    with mock_aws():
        create_table("noshi-test", endpoint_url=None)
        yield "noshi-test"


def test_レコードを保存して本人がintで取得できる(table_name):
    """DynamoDB往復後も金額が int 型で復元されることを検証する（Decimal対策）。"""
    repo = DynamoRepository(table_name=table_name)
    rec = GiftRecord(user_id="u1", party_name="佐藤", amount=30000, purpose="出産祝い")
    repo.put_record(rec)
    got = repo.get_record("u1", rec.id)
    assert got is not None
    assert got.amount == 30000 and isinstance(got.amount, int)


def test_他人のレコードは取得できない(table_name):
    """他ユーザーは他人のレコードを取得できないことを検証する（A01 キー設計でスコープ強制）。"""
    repo = DynamoRepository(table_name=table_name)
    rec = GiftRecord(user_id="u1", party_name="佐藤", amount=30000, purpose="出産祝い")
    repo.put_record(rec)
    assert repo.get_record("u2", rec.id) is None


def test_一覧は本人のレコードだけを返す(table_name):
    """一覧が要求した本人のレコードだけを返すことを検証する（A01）。"""
    repo = DynamoRepository(table_name=table_name)
    repo.put_record(GiftRecord(user_id="u1", party_name="A", amount=1000, purpose="香典"))
    repo.put_record(GiftRecord(user_id="u2", party_name="B", amount=2000, purpose="香典"))
    assert len(repo.list_records("u1")) == 1


def test_別インスタンスから保存済みデータが読める(table_name):
    """別の Repository インスタンス（=別プロセス相当）が先の書き込みを読めることを検証する（永続化）。"""
    DynamoRepository(table_name=table_name).put_record(
        GiftRecord(user_id="u1", party_name="叔母", amount=5000, purpose="お年賀")
    )
    fresh = DynamoRepository(table_name=table_name)
    assert len(fresh.list_records("u1")) == 1


def test_float信頼度を含むジョブを保存できる(table_name):
    """float の信頼度を持つ ExtractionJob を保存・取得できることを検証する（Decimal変換）。"""
    repo = DynamoRepository(table_name=table_name)
    job = ExtractionJob(
        user_id="u1", confidence=0.82, field_confidence={"amount": 0.9, "purpose": 0.6}
    )
    repo.put_job(job)
    got = repo.get_job("u1", job.id)
    assert got is not None
    assert abs(got.confidence - 0.82) < 1e-9


def test_未完了イベントはdoneを除外する(table_name):
    """未完了イベント一覧が status=done を除外することを検証する（BR-EVT-2）。"""
    repo = DynamoRepository(table_name=table_name)
    e1 = GiftEvent(user_id="u1", record_id="r1", status="considering")
    e2 = GiftEvent(user_id="u1", record_id="r2", status="done")
    repo.put_event(e1)
    repo.put_event(e2)
    assert [e.id for e in repo.list_pending_events("u1")] == [e1.id]


def test_イベントを削除できる(table_name):
    """イベントを保存し、delete_event で削除できることを検証する（#36）。"""
    repo = DynamoRepository(table_name=table_name)
    e = GiftEvent(user_id="u1", record_id="r1")
    repo.put_event(e)
    assert repo.delete_event("u1", e.id) is True
    assert repo.get_event("u1", e.id) is None
    assert repo.delete_event("u1", e.id) is False  # 二重削除は False


def test_世帯と招待コードで往復できる(table_name):
    """世帯を保存し、招待コードから逆引きで同じ世帯を取得できることを検証する（家族共有）。"""
    from app.domain.entities import Household

    repo = DynamoRepository(table_name=table_name)
    h = Household(name="井上家")
    repo.put_household(h)
    assert repo.get_household(h.id).name == "井上家"
    assert repo.get_household_by_invite(h.invite_code).id == h.id


def test_メンバーシップと世帯メンバー一覧(table_name):
    """メンバーシップを保存し、ユーザー引き・世帯メンバー一覧引きの両方ができることを検証する。"""
    from app.domain.entities import Membership

    repo = DynamoRepository(table_name=table_name)
    repo.put_membership(Membership(user_id="u1", household_id="H", role="owner"))
    repo.put_membership(Membership(user_id="u2", household_id="H", role="member"))
    assert repo.get_membership("u1").role == "owner"
    assert {m.user_id for m in repo.list_members("H")} == {"u1", "u2"}


def test_世帯独自の続柄を保存し追加順で読める(table_name):
    """世帯独自の続柄を保存し、追加順で一覧でき、同名は重複しないことを検証する（#1）。"""
    repo = DynamoRepository(table_name=table_name)
    repo.add_household_relationship("H", "ママ友")
    repo.add_household_relationship("H", "茶道仲間")
    repo.add_household_relationship("H", "ママ友")  # 重複 upsert
    assert repo.list_household_relationships("H") == ["ママ友", "茶道仲間"]
    assert repo.list_household_relationships("OTHER") == []  # 別世帯には出ない
    repo.remove_household_relationship("H", "ママ友")
    assert repo.list_household_relationships("H") == ["茶道仲間"]  # 削除が効く


def test_世帯独自の用途を保存し追加順で読める(table_name):
    """世帯独自の用途を保存し、追加順で一覧でき、削除できることを検証する（#37）。"""
    repo = DynamoRepository(table_name=table_name)
    repo.add_household_purpose("H", "町内会")
    repo.add_household_purpose("H", "発表会祝い")
    assert repo.list_household_purposes("H") == ["町内会", "発表会祝い"]
    repo.remove_household_purpose("H", "町内会")
    assert repo.list_household_purposes("H") == ["発表会祝い"]
    assert repo.list_household_purposes("OTHER") == []
