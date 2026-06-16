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


def test_おつきあいと台帳に相手の続き柄が補正される():
    """続き柄は人の現在の属性。おつきあい集計と台帳レコードに反映されることを検証する。"""
    svc = make_service()
    party = svc.add_party("u1", "叔母 佳子", "親族")
    svc.create_record(
        "u1", amount=30000, purpose="出産祝い", direction="received", party_id=party["id"]
    )
    rels = svc.relationships("u1")
    assert any(r["party_name"] == "叔母 佳子" and r["relationship"] == "親族" for r in rels)
    recs = svc.ledger_records("u1")
    assert recs and all(r["relationship"] == "親族" for r in recs)


def test_party_idなしの古いレコードも相手名で続き柄が補正される():
    """party_id 導入前の古いレコード（party_id 空）も、相手名で続き柄を補正できることを検証する。"""
    from app.domain.entities import GiftRecord

    svc = make_service()
    svc.add_party("u1", "叔母 佳子", "親族")
    scope = svc._scope("u1")
    # party_id を持たない旧データ相当のレコードを直接投入する。
    svc.repo.put_record(
        GiftRecord(
            user_id=scope,
            party_name="叔母 佳子",
            amount=10000,
            purpose="出産祝い",
            direction="received",
            occurred_at="2026-05-01",
        )
    )
    rels = svc.relationships("u1")
    assert any(r["party_name"] == "叔母 佳子" and r["relationship"] == "親族" for r in rels)
    recs = svc.ledger_records("u1")
    assert any(r["relationship"] == "親族" for r in recs)


def test_品物を記録して詳細で取得できる():
    """もらった物の品名（例: メガネ/現金）を保存し、記録詳細で取得できることを検証する。"""
    svc = make_service()
    rec, _ = svc.create_record(
        "u1",
        amount=20000,
        purpose="お祝い",
        party_name="佐藤",
        direction="received",
        item="メガネ",
    )
    detail = svc.record_detail("u1", rec.id)
    assert detail["item"] == "メガネ"


def test_品物は記録修正で変更できる():
    """記録修正で品名を変更でき、変更後の値が詳細に反映されることを検証する。"""
    svc = make_service()
    rec, _ = svc.create_record(
        "u1", amount=5000, purpose="お祝い", party_name="佐藤", direction="received", item="現金"
    )
    svc.update_record("u1", rec.id, amount=5000, purpose="お祝い", item="商品券")
    assert svc.record_detail("u1", rec.id)["item"] == "商品券"


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


def test_記録を削除すると紐づくお返しイベントも消える():
    """記録を削除すると、対応する GiftEvent も削除され孤立しないことを検証する（#36）。"""
    svc = make_service()
    rec, ev = svc.create_record(
        "u1", amount=30000, purpose="出産祝い", party_name="佐藤", direction="received"
    )
    assert svc.event_for_record("u1", rec.id) is not None
    svc.delete_record("u1", rec.id)
    assert svc.event_for_record("u1", rec.id) is None  # イベントも消える
    assert svc.list_pending_events("u1") == []  # ホームの予定にも出ない
    assert svc.repo.get_event("u1", ev.id) is None


def test_抽出ジョブは候補と要確認フラグを返す():
    """抽出ジョブが候補を返し、低信頼のため要確認(needs_review)になることを検証する（BR-EX-2）。"""
    svc = make_service()
    job = svc.submit_extraction("u1", ["img.jpg"])
    assert job.candidates and job.confidence < 0.7
    assert svc.extraction_needs_review(job) is True


def test_お返しフローで半返しと提案が紐づく():
    """半返し算出→提案選択までがイベントに紐づくことを検証する（S-5,6）。"""
    svc = make_service()
    _, ev = svc.create_record(
        "u1", amount=30000, purpose="出産祝い", party_name="佐藤", direction="received"
    )
    rng = svc.half_return(30000, "出産祝い")
    assert rng.recommended == 15000
    suggestions = svc.suggest_returns("u1", ev.id, rng.recommended, "友人", "出産祝い")
    chosen = suggestions[0]
    svc.select_suggestion("u1", ev.id, chosen)
    updated = svc.get_event("u1", ev.id)
    assert updated.suggestion_id is not None


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


def test_続柄を削除しても相手の続柄は残る():
    """マスタから続柄を削除しても、その続柄を持つ相手(Party)の値は保持されることを検証する（#1/#47, 後方互換）。"""
    svc = make_service()
    svc.add_relationship("u1", "ママ友")
    party = svc.add_party("u1", "佐藤", "ママ友")
    _, ev = svc.create_record(
        "u1", amount=10000, purpose="出産祝い", direction="received", party_id=party["id"]
    )
    svc.remove_relationship("u1", "ママ友")  # マスタからは消す
    assert svc.parties("u1")[0]["relationship"] == "ママ友"  # 相手は不変
    assert svc.event_view("u1", ev.id)["relationship"] == "ママ友"  # 続柄は相手から


def test_他世帯の続柄は削除できない():
    """別世帯のマスタ項目は削除操作の影響を受けないことを検証する（A01, 世帯分離）。"""
    svc = make_service()
    svc.add_relationship("u1", "山岳会")
    svc.remove_relationship("u2", "山岳会")  # 別世帯からの削除は無関係
    assert "山岳会" in svc.relationship_master("u1")["options"]


def test_用途マスタは既定リストを返す():
    """用途マスタが既定の用途（出産祝い・香典 等）を含むことを検証する（#37）。"""
    svc = make_service()
    m = svc.purpose_master("u1")
    assert "出産祝い" in m["options"] and "香典" in m["options"]
    assert m["defaults"] == list(m["options"])  # 追加前は既定のみ


def test_世帯独自の用途を追加削除でき家族に共有される():
    """世帯独自の用途を追加・削除でき、同じ世帯の家族にも共有されることを検証する（#37）。"""
    svc = make_service()
    code = svc.household_invite_code("owner")
    svc.join_household("family", code)
    svc.add_purpose("owner", "発表会祝い")
    assert "発表会祝い" in svc.purpose_master("family")["options"]
    svc.remove_purpose("owner", "発表会祝い")
    assert "発表会祝い" not in svc.purpose_master("family")["options"]


def test_用途は既定重複や空文字を追加せず別世帯にも出ない():
    """既定重複・空文字は追加されず、別世帯の用途は見えないことを検証する（#37, A01）。"""
    svc = make_service()
    svc.add_purpose("u1", "香典")  # 既定と重複
    svc.add_purpose("u1", "  ")  # 空白
    svc.add_purpose("u1", "町内会")
    m = svc.purpose_master("u1")
    assert m["options"].count("香典") == 1 and "" not in m["options"]
    assert "町内会" not in svc.purpose_master("u2")["options"]


def test_用途は30件までしか追加できない():
    """世帯独自の用途が上限（30件）を超えると ValidationError になることを検証する（#37）。"""
    svc = make_service()
    for i in range(30):
        svc.add_purpose("u1", f"用途{i}")
    with pytest.raises(ValidationError):
        svc.add_purpose("u1", "あふれる")


def test_あげた記録も詳細ビューを取得できる():
    """given 記録は event を持たないが、record_detail で詳細ビューを取得できることを検証する（#48）。"""
    svc = make_service()
    rec, ev = svc.create_record(
        "u1", amount=50000, purpose="結婚祝い", party_name="姪", direction="given"
    )
    assert ev is None  # given はイベントなし
    v = svc.record_detail("u1", rec.id)
    assert v["record_id"] == rec.id
    assert v["direction"] == "given" and v["party_name"] == "姪"
    assert v["id"] == ""  # イベントIDなし（ステータス等は出さない）


def test_もらった記録の詳細はイベントビューと一致する():
    """received 記録の record_detail は対応イベントの event_view と同等であることを検証する（#48）。"""
    svc = make_service()
    rec, ev = svc.create_record(
        "u1", amount=30000, purpose="出産祝い", party_name="佐藤", direction="received"
    )
    v = svc.record_detail("u1", rec.id)
    assert v["id"] == ev.id and v["status"] == "received"


def test_他人の記録の詳細は取得できない():
    """他世帯の記録の record_detail が ForbiddenError になることを検証する（A01）。"""
    import pytest

    svc = make_service()
    rec, _ = svc.create_record(
        "owner", amount=10000, purpose="香典", party_name="田中", direction="received"
    )
    with pytest.raises(ForbiddenError):
        svc.record_detail("attacker", rec.id)


def test_同名でも別人として区別して集計される():
    """同名の別人(party_id 違い)が、おつきあいで別エントリ・年間人数で別カウントになることを検証する（#47）。"""
    svc = make_service()
    a = svc.add_party("u1", "田中", "友人")
    b = svc.add_party("u1", "田中", "会社")
    svc.create_record(
        "u1",
        amount=10000,
        purpose="出産祝い",
        direction="received",
        party_id=a["id"],
        occurred_at="2026-01-10",
    )
    svc.create_record(
        "u1",
        amount=50000,
        purpose="結婚祝い",
        direction="given",
        party_id=b["id"],
        occurred_at="2026-02-10",
    )
    rels = svc.relationships("u1")
    tanaka = [r for r in rels if r["party_name"] == "田中"]
    assert len(tanaka) == 2  # 同名でも別人＝別エントリ
    assert svc.annual_summary("u1", 2026)["party_count"] == 2  # 人数も2


def test_相手の続柄を更新すると記録の表示名も追従する():
    """update_party で名前を変えると、その相手の記録の party_name スナップショットも同期することを検証する（#47）。"""
    svc = make_service()
    p = svc.add_party("u1", "たなか", "友人")
    _, ev = svc.create_record(
        "u1", amount=10000, purpose="出産祝い", direction="received", party_id=p["id"]
    )
    svc.update_party("u1", p["id"], "田中 太郎", "友人")
    assert svc.event_view("u1", ev.id)["party_name"] == "田中 太郎"
    assert svc.list_records("u1")[0].party_name == "田中 太郎"


def test_存在しない相手IDでの記録作成は検証エラー():
    """未知の party_id での記録作成が ValidationError になることを検証する（#47）。"""
    import pytest

    svc = make_service()
    with pytest.raises(ValidationError):
        svc.create_record(
            "u1", amount=10000, purpose="出産祝い", direction="received", party_id="nope"
        )


def test_検証済みメールが一致する2人目は1人目の世帯に自動合流する():
    svc = make_service()
    h1 = svc.resolve_household("subGoogle", email="a@x.com", email_verified=True)
    h2 = svc.resolve_household("subMail", email="a@x.com", email_verified=True)
    assert h2.id == h1.id
    assert svc.repo.get_account_link("subMail") == "subGoogle"


def test_未検証メールは自動合流せず別世帯になる():
    svc = make_service()
    h1 = svc.resolve_household("subGoogle", email="a@x.com", email_verified=True)
    h2 = svc.resolve_household(
        "subApple", email="relay@privaterelay.appleid.com", email_verified=False
    )
    assert h2.id != h1.id
    assert svc.repo.get_account_link("subApple") is None


def test_既存membershipを持つsubは再エイリアスされない():
    svc = make_service()
    first = svc.resolve_household("subGoogle", email="a@x.com", email_verified=True)
    again = svc.resolve_household("subGoogle", email="a@x.com", email_verified=True)
    assert svc.repo.get_account_link("subGoogle") is None
    assert again.id == first.id


def test_既存世帯のsubは検証済みメールでEMAIL代表がbackfillされる():
    svc = make_service()
    svc.resolve_household(
        "subGoogle", email="a@x.com", email_verified=False
    )  # 先に未検証で世帯作成
    assert svc.repo.get_email_primary("a@x.com") is None
    svc.resolve_household("subGoogle", email="a@x.com", email_verified=True)  # 後から検証済み
    assert svc.repo.get_email_primary("a@x.com") == "subGoogle"


def test_合流先代表が世帯を失っていれば別名を張らず新世帯になる():
    svc = make_service()
    svc.resolve_household("primaryX", email="a@x.com", email_verified=True)
    svc.repo.delete_membership("primaryX")  # 代表が世帯を失った状態を再現
    h = svc.resolve_household("subNew", email="a@x.com", email_verified=True)
    assert svc.repo.get_account_link("subNew") is None
    m = svc.repo.get_membership("subNew")
    assert m is not None and m.household_id == h.id


def test_合流先世帯が無い場合は新subがそのメールの新代表になる():
    svc = make_service()
    svc.resolve_household("primaryX", email="a@x.com", email_verified=True)
    svc.repo.delete_membership("primaryX")  # 代表が世帯を失う
    svc.resolve_household("subNew", email="a@x.com", email_verified=True)
    assert svc.repo.get_email_primary("a@x.com") == "subNew"  # 新subが代表を引き継ぐ
    # さらに後続の別sub は subNew に合流する
    h3 = svc.resolve_household("subThird", email="a@x.com", email_verified=True)
    assert svc.repo.get_account_link("subThird") == "subNew"
    assert h3.id == svc.resolve_household("subNew").id


def test_delete_accountは別名とEMAIL代表を掃除し全subを返す():
    svc = make_service()
    svc.resolve_household("primaryX", email="a@x.com", email_verified=True)
    svc.repo.put_account_link("aliasA", "primaryX")
    svc.repo.put_account_link("aliasB", "primaryX")
    subs = svc.delete_account("primaryX")
    assert set(subs) == {"primaryX", "aliasA", "aliasB"}
    assert svc.repo.get_account_link("aliasA") is None
    assert svc.repo.get_account_link("aliasB") is None
    assert svc.repo.get_email_primary("a@x.com") is None
    assert svc.repo.get_membership("primaryX") is None


def test_account_subsは代表と別名を返す():
    svc = make_service()
    svc.resolve_household("primaryX", email="a@x.com", email_verified=True)
    svc.repo.put_account_link("aliasA", "primaryX")
    assert set(svc.account_subs("primaryX")) == {"primaryX", "aliasA"}
