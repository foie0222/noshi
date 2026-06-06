"""サービス層のテスト。中核ループと本人スコープ強制・監査を検証する。"""
import pytest
from app.repository import InMemoryRepository
from app.ports import OcrLlmMock, GiftCatalogMock
from app.services import NoshiService, ForbiddenError, ValidationError


def make_service():
    return NoshiService(InMemoryRepository(), OcrLlmMock(), GiftCatalogMock())


def test_記録を作成すると台帳と受領イベントができる():
    """贈答レコードを作成すると台帳に1件入り、対応する受領イベントが生成されることを検証する。"""
    svc = make_service()
    rec, ev = svc.create_record("u1", amount=30000, purpose="出産祝い", party_name="佐藤", direction="received")
    assert len(svc.list_records("u1")) == 1
    assert ev.record_id == rec.id and ev.status == "received"


def test_不正な入力は検証エラーになる():
    """金額0など不正な入力での記録作成がValidationErrorになることを検証する（BR-VAL）。"""
    svc = make_service()
    with pytest.raises(ValidationError):
        svc.create_record("u1", amount=0, purpose="出産祝い", party_name="佐藤", direction="received")


def test_他人のイベントのステータスは変更できない():
    """他ユーザーのイベントのステータス変更がForbiddenErrorで拒否されることを検証する（A01）。"""
    svc = make_service()
    _, ev = svc.create_record("u1", amount=10000, purpose="香典", party_name="田中", direction="received")
    with pytest.raises(ForbiddenError):
        svc.set_event_status("attacker", ev.id, "done")


def test_レコード削除で監査ログが残る():
    """贈答レコードの削除がAuditEntryとして監査記録されることを検証する（A09, S-13）。"""
    svc = make_service()
    rec, _ = svc.create_record("u1", amount=5000, purpose="お中元", party_name="山田", direction="received")
    svc.delete_record("u1", rec.id)
    actions = [a.action for a in svc.repo.audit_entries]
    assert "delete_record" in actions


def test_抽出ジョブは候補と要確認フラグを返す():
    """抽出ジョブが候補を返し、低信頼のため要確認(needs_review)になることを検証する（BR-EX-2）。"""
    svc = make_service()
    job = svc.submit_extraction("u1", ["img.jpg"])
    assert job.candidates and job.confidence < 0.7
    assert svc.extraction_needs_review(job) is True


def test_お返しフローで半返しと提案と礼状が紐づく():
    """半返し算出→提案選択→礼状生成までがイベントに紐づくことを検証する（S-5,6,7）。"""
    svc = make_service()
    _, ev = svc.create_record("u1", amount=30000, purpose="出産祝い", party_name="佐藤", direction="received")
    rng = svc.half_return(30000, "出産祝い")
    assert rng.recommended == 15000
    suggestions = svc.suggest_returns("u1", ev.id, rng.recommended, "友人", "出産祝い")
    chosen = suggestions[0]
    svc.select_suggestion("u1", ev.id, chosen)
    letter = svc.generate_letter("u1", ev.id, "出産祝い", "友人", "丁寧")
    updated = svc.get_event("u1", ev.id)
    assert updated.suggestion_id is not None and updated.letter_id == letter.id


def test_未完了ビューは相手と用途と金額を含む():
    """未完了イベントの表示用ビューが、イベントIDではなく相手・用途・金額を含むことを検証する（UX）。"""
    svc = make_service()
    svc.create_record("u1", amount=30000, purpose="出産祝い", party_name="佐藤 花子", direction="received")
    views = svc.pending_views("u1")
    assert len(views) == 1
    v = views[0]
    assert v["party_name"] == "佐藤 花子"
    assert v["purpose"] == "出産祝い"
    assert v["amount"] == 30000
    assert "status" in v


def test_イベントビューは記録情報で表示できる():
    """単一イベントの表示用ビューが紐づく記録の相手・用途・金額を含むことを検証する（UX）。"""
    svc = make_service()
    _, ev = svc.create_record("u1", amount=5000, purpose="お中元", party_name="山田 一郎", direction="received")
    v = svc.event_view("u1", ev.id)
    assert v["party_name"] == "山田 一郎" and v["amount"] == 5000


def test_記録から対応するイベントを引ける():
    """台帳の記録IDから対応する贈答イベントを取得できることを検証する（ledger→お返しフロー）。"""
    svc = make_service()
    rec, ev = svc.create_record("u1", amount=10000, purpose="香典", party_name="田中", direction="received")
    found = svc.event_for_record("u1", rec.id)
    assert found is not None and found.id == ev.id


def test_他人の台帳は見えない():
    """ある利用者の台帳取得が他人のレコードを含まないことを検証する（A01）。"""
    svc = make_service()
    svc.create_record("u1", amount=1000, purpose="香典", party_name="A", direction="received")
    svc.create_record("u2", amount=2000, purpose="香典", party_name="B", direction="received")
    assert len(svc.list_records("u1")) == 1
