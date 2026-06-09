"""サービス層のテスト。中核ループと本人スコープ強制・監査を検証する。"""

import pytest
from app.ports import GiftCatalogMock, OcrLlmMock
from app.repository import InMemoryRepository
from app.services import ForbiddenError, NoshiService, ValidationError


def make_service():
    return NoshiService(InMemoryRepository(), OcrLlmMock(), GiftCatalogMock())


def test_記録を作成すると台帳と受領イベントができる():
    """贈答レコードを作成すると台帳に1件入り、対応する受領イベントが生成されることを検証する。"""
    svc = make_service()
    rec, ev = svc.create_record(
        "u1", amount=30000, purpose="出産祝い", party_name="佐藤", direction="received"
    )
    assert len(svc.list_records("u1")) == 1
    assert ev.record_id == rec.id and ev.status == "received"


def test_不正な入力は検証エラーになる():
    """金額0など不正な入力での記録作成がValidationErrorになることを検証する（BR-VAL）。"""
    svc = make_service()
    with pytest.raises(ValidationError):
        svc.create_record(
            "u1", amount=0, purpose="出産祝い", party_name="佐藤", direction="received"
        )


def test_他人のイベントのステータスは変更できない():
    """他ユーザーのイベントのステータス変更がForbiddenErrorで拒否されることを検証する（A01）。"""
    svc = make_service()
    _, ev = svc.create_record(
        "u1", amount=10000, purpose="香典", party_name="田中", direction="received"
    )
    with pytest.raises(ForbiddenError):
        svc.set_event_status("attacker", ev.id, "done")


def test_レコード削除で監査ログが残る():
    """贈答レコードの削除がAuditEntryとして監査記録されることを検証する（A09, S-13）。"""
    svc = make_service()
    rec, _ = svc.create_record(
        "u1", amount=5000, purpose="お中元", party_name="山田", direction="received"
    )
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
    _, ev = svc.create_record(
        "u1", amount=30000, purpose="出産祝い", party_name="佐藤", direction="received"
    )
    rng = svc.half_return(30000, "出産祝い")
    assert rng.recommended == 15000
    suggestions = svc.suggest_returns("u1", ev.id, rng.recommended, "友人", "出産祝い")
    chosen = suggestions[0]
    svc.select_suggestion("u1", ev.id, chosen)
    letter = svc.generate_letter("u1", ev.id, "出産祝い", "友人", "丁寧")
    updated = svc.get_event("u1", ev.id)
    assert updated.suggestion_id is not None and updated.letter_id == letter.id


def test_あげた贈答はお返し対象に出ない():
    """direction=given のレコードは未完了お返し(pending)に現れないことを検証する（BR-3-GIVEN）。"""
    svc = make_service()
    svc.create_record("u1", amount=50000, purpose="結婚祝い", party_name="田中", direction="given")
    assert svc.list_pending_events("u1") == []
    assert len(svc.list_records("u1")) == 1  # 台帳には残る


def test_お返し不要の用途は未完了に出ない():
    """お中元（お返し不要）は受領でも未完了お返しに出ないことを検証する（BR-3-DUE-2）。"""
    svc = make_service()
    svc.create_record(
        "u1",
        amount=5000,
        purpose="お中元",
        party_name="山田",
        direction="received",
        occurred_at="2026-07-01",
    )
    assert svc.pending_views("u1") == []


def test_未完了ビューは期限と残日数を含む():
    """未完了お返しのビューが期限(due_at)と残日数(days_left)を含むことを検証する（P0-1）。"""
    svc = make_service()
    svc.create_record(
        "u1",
        amount=30000,
        purpose="出産祝い",
        party_name="佐藤",
        direction="received",
        occurred_at="2026-05-01",
    )
    v = svc.pending_views("u1")[0]
    assert v["due_at"] == "2026-05-31"
    assert "days_left" in v


def test_未完了は期限の近い順に並ぶ():
    """未完了お返しが残日数の昇順（期限が近い順）に並ぶことを検証する（BR-3-DUE-5）。"""
    svc = make_service()
    svc.create_record(
        "u1",
        amount=10000,
        purpose="出産祝い",
        party_name="A",
        direction="received",
        occurred_at="2026-05-10",
    )  # 6/9
    svc.create_record(
        "u1",
        amount=10000,
        purpose="香典",
        party_name="B",
        direction="received",
        occurred_at="2026-05-01",
    )  # 6/19
    svc.create_record(
        "u1",
        amount=10000,
        purpose="結婚祝い",
        party_name="C",
        direction="received",
        occurred_at="2026-05-05",
    )  # 6/4
    order = [v["party_name"] for v in svc.pending_views("u1")]
    assert order == ["C", "A", "B"]  # 6/4 < 6/9 < 6/19


def test_未完了ビューは相手と用途と金額を含む():
    """未完了イベントの表示用ビューが、イベントIDではなく相手・用途・金額を含むことを検証する（UX）。"""
    svc = make_service()
    svc.create_record(
        "u1", amount=30000, purpose="出産祝い", party_name="佐藤 花子", direction="received"
    )
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
    _, ev = svc.create_record(
        "u1", amount=5000, purpose="お中元", party_name="山田 一郎", direction="received"
    )
    v = svc.event_view("u1", ev.id)
    assert v["party_name"] == "山田 一郎" and v["amount"] == 5000


def test_記録から対応するイベントを引ける():
    """台帳の記録IDから対応する贈答イベントを取得できることを検証する（ledger→お返しフロー）。"""
    svc = make_service()
    rec, ev = svc.create_record(
        "u1", amount=10000, purpose="香典", party_name="田中", direction="received"
    )
    found = svc.event_for_record("u1", rec.id)
    assert found is not None and found.id == ev.id


def test_他人の台帳は見えない():
    """ある利用者の台帳取得が他人のレコードを含まないことを検証する（A01）。"""
    svc = make_service()
    svc.create_record("u1", amount=1000, purpose="香典", party_name="A", direction="received")
    svc.create_record("u2", amount=2000, purpose="香典", party_name="B", direction="received")
    assert len(svc.list_records("u1")) == 1


def test_記録を修正すると金額と相手が更新され監査が残る():
    """保存済みレコードの金額・相手・用途をupdate_recordで修正でき、監査に残ることを検証する（S-13, A09）。"""
    svc = make_service()
    rec, _ = svc.create_record(
        "u1", amount=10000, purpose="出産祝い", party_name="佐藤", direction="received"
    )
    updated = svc.update_record(
        "u1", rec.id, amount=30000, purpose="結婚祝い", party_name="佐藤花子"
    )
    assert updated.amount == 30000
    assert updated.purpose == "結婚祝い"
    assert updated.party_name == "佐藤花子"
    assert updated.id == rec.id  # 同一レコードを更新（新規ではない）
    assert "update_record" in [a.action for a in svc.repo.audit_entries]


def test_他人の記録は修正できない():
    """他ユーザーのレコード修正がForbiddenErrorで拒否されることを検証する（A01）。"""
    svc = make_service()
    rec, _ = svc.create_record(
        "u1", amount=10000, purpose="香典", party_name="田中", direction="received"
    )
    with pytest.raises(ForbiddenError):
        svc.update_record("attacker", rec.id, amount=20000, purpose="香典", party_name="田中")


def test_不正な値での修正は検証エラーになる():
    """金額0など不正な値でのレコード修正がValidationErrorになることを検証する（BR-VAL）。"""
    svc = make_service()
    rec, _ = svc.create_record(
        "u1", amount=10000, purpose="出産祝い", party_name="佐藤", direction="received"
    )
    with pytest.raises(ValidationError):
        svc.update_record("u1", rec.id, amount=0, purpose="出産祝い", party_name="佐藤")


def test_もらった日を変えると期限が再計算される():
    """occurred_at をupdate_recordで変更すると、イベントビューのお返し期限が再計算されることを検証する（#2）。"""
    svc = make_service()
    rec, ev = svc.create_record(
        "u1",
        amount=10000,
        purpose="出産祝い",
        party_name="佐藤",
        direction="received",
        occurred_at="2026-05-01",
    )
    assert svc.event_view("u1", ev.id)["due_at"] == "2026-05-31"  # +30日
    svc.update_record(
        "u1", rec.id, amount=10000, purpose="出産祝い", party_name="佐藤", occurred_at="2026-06-01"
    )
    assert svc.event_view("u1", ev.id)["due_at"] == "2026-07-01"  # 再計算


def test_お返し期限をデフォルトから上書きできる():
    """set_event_due で期限を手動上書きでき、ビューに due_overridden と既定値も含まれることを検証する（#2）。"""
    svc = make_service()
    _, ev = svc.create_record(
        "u1",
        amount=10000,
        purpose="出産祝い",
        party_name="佐藤",
        direction="received",
        occurred_at="2026-05-01",
    )
    svc.set_event_due("u1", ev.id, "2026-06-15")
    v = svc.event_view("u1", ev.id)
    assert v["due_at"] == "2026-06-15"  # 上書きが効く
    assert v["due_overridden"] is True
    assert v["due_default"] == "2026-05-31"  # 既定は保持して提示


def test_期限上書きをクリアするとデフォルトに戻る():
    """空文字/None で set_event_due すると上書きが消え、既定の自動計算に戻ることを検証する（#2）。"""
    svc = make_service()
    _, ev = svc.create_record(
        "u1",
        amount=10000,
        purpose="出産祝い",
        party_name="佐藤",
        direction="received",
        occurred_at="2026-05-01",
    )
    svc.set_event_due("u1", ev.id, "2026-06-15")
    svc.set_event_due("u1", ev.id, "")  # クリア
    v = svc.event_view("u1", ev.id)
    assert v["due_overridden"] is False
    assert v["due_at"] == "2026-05-31"  # 既定に復帰


def test_不正な期限の上書きは検証エラーになる():
    """YYYY-MM-DD でない期限の上書きが ValidationError になることを検証する（#2, BR-VAL）。"""
    svc = make_service()
    _, ev = svc.create_record(
        "u1", amount=10000, purpose="出産祝い", party_name="佐藤", direction="received"
    )
    with pytest.raises(ValidationError):
        svc.set_event_due("u1", ev.id, "2026/06/15")


def test_他人のイベントの期限は上書きできない():
    """他ユーザーのイベントの期限上書きが ForbiddenError で拒否されることを検証する（A01）。"""
    svc = make_service()
    _, ev = svc.create_record(
        "u1", amount=10000, purpose="出産祝い", party_name="佐藤", direction="received"
    )
    with pytest.raises(ForbiddenError):
        svc.set_event_due("attacker", ev.id, "2026-06-15")


def test_続柄マスタは既定リストを返す():
    """続柄マスタが既定の続柄（親・友人 等）を含むことを検証する（#1）。"""
    svc = make_service()
    m = svc.relationship_master("u1")
    assert "親" in m["options"] and "友人" in m["options"]
    assert m["defaults"] == list(m["options"])  # 追加前は既定のみ


def test_世帯独自の続柄を追加して選択肢に出る():
    """世帯独自の続柄を追加でき、マスタの options 末尾に現れることを検証する（#1）。"""
    svc = make_service()
    m = svc.add_relationship("u1", "ママ友")
    assert "ママ友" in m["options"]
    assert "ママ友" not in m["defaults"]  # 既定ではなく世帯独自


def test_追加した続柄は同じ世帯の家族に共有される():
    """ある世帯メンバーが追加した続柄が、同じ世帯の別メンバーにも見えることを検証する（#1, 世帯スコープ）。"""
    svc = make_service()
    code = svc.household_invite_code("owner")
    svc.join_household("family", code)
    svc.add_relationship("owner", "茶道仲間")
    assert "茶道仲間" in svc.relationship_master("family")["options"]


def test_既定と重複する続柄や空文字は追加されない():
    """既定に既にある続柄・空文字の追加が無視（重複排除）されることを検証する（#1）。"""
    svc = make_service()
    svc.add_relationship("u1", "友人")  # 既定と重複
    svc.add_relationship("u1", "  ")  # 空白のみ
    m = svc.relationship_master("u1")
    assert m["options"].count("友人") == 1
    assert "" not in m["options"] and "  " not in m["options"]


def test_別世帯の続柄は見えない():
    """別世帯で追加した続柄が他世帯のマスタに現れないことを検証する（A01, 世帯分離）。"""
    svc = make_service()
    svc.add_relationship("u1", "山岳会")
    assert "山岳会" not in svc.relationship_master("u2")["options"]


def test_世帯独自の続柄は30件までしか追加できない():
    """世帯独自の続柄が上限（30件）を超えると ValidationError になることを検証する（#1）。"""
    svc = make_service()
    for i in range(30):
        svc.add_relationship("u1", f"続柄{i}")
    assert len([o for o in svc.relationship_master("u1")["options"] if o.startswith("続柄")]) == 30
    with pytest.raises(ValidationError):
        svc.add_relationship("u1", "あふれる")


def test_世帯独自の続柄を削除できる():
    """追加した世帯独自の続柄を削除でき、マスタの options から消えることを検証する（#1）。"""
    svc = make_service()
    svc.add_relationship("u1", "ママ友")
    m = svc.remove_relationship("u1", "ママ友")
    assert "ママ友" not in m["options"]


def test_既定の続柄は削除できない():
    """システム既定の続柄を削除しようとしても既定リストは不変であることを検証する（#1）。"""
    svc = make_service()
    m = svc.remove_relationship("u1", "友人")  # 既定は削除対象外（no-op）
    assert "友人" in m["options"] and "友人" in m["defaults"]


def test_続柄を削除しても過去レコードの値は残る():
    """マスタから続柄を削除しても、その続柄を使う過去レコードの文字列は保持されることを検証する（#1, 後方互換）。"""
    svc = make_service()
    rec, ev = svc.create_record(
        "u1",
        amount=10000,
        purpose="出産祝い",
        party_name="佐藤",
        direction="received",
        relationship="ママ友",
    )
    svc.add_relationship("u1", "ママ友")
    svc.remove_relationship("u1", "ママ友")  # マスタからは消す
    assert svc.list_records("u1")[0].relationship == "ママ友"  # レコードは不変
    assert svc.event_view("u1", ev.id)["relationship"] == "ママ友"


def test_他世帯の続柄は削除できない():
    """別世帯のマスタ項目は削除操作の影響を受けないことを検証する（A01, 世帯分離）。"""
    svc = make_service()
    svc.add_relationship("u1", "山岳会")
    svc.remove_relationship("u2", "山岳会")  # 別世帯からの削除は無関係
    assert "山岳会" in svc.relationship_master("u1")["options"]
