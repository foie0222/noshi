"""家族共有（世帯スコープ）のテスト。

データは「本人」ではなく「世帯」に属し、同じ世帯のメンバーは台帳・お返しを共有する。
別世帯には見えない。初回アクセスで世帯が自動作成され、招待コードで参加できる。
"""
from app.repository import InMemoryRepository
from app.ports import OcrLlmMock, GiftCatalogMock
from app.services import NoshiService


def make():
    return NoshiService(InMemoryRepository(), OcrLlmMock(), GiftCatalogMock())


def test_初回アクセスで世帯が自動作成され本人が管理者():
    """初めて使うユーザーには世帯が自動作成され、本人が owner として登録されることを検証する。"""
    svc = make()
    h = svc.resolve_household("u1", email="taro@example.jp")
    assert h.id
    members = svc.household_members("u1")
    assert len(members) == 1 and members[0]["role"] == "owner"


def test_同じ世帯のメンバーは台帳を共有する():
    """招待コードで参加した家族が、相手の登録した贈答記録を見られることを検証する（世帯共有）。"""
    svc = make()
    svc.create_record("u1", amount=30000, purpose="出産祝い", party_name="佐藤", direction="received")
    code = svc.household_invite_code("u1")
    svc.join_household("u2", code)
    assert len(svc.list_records("u2")) == 1


def test_別世帯のメンバーには見えない():
    """同じ世帯に属さないユーザーには、その世帯の記録が見えないことを検証する（A01 世帯境界）。"""
    svc = make()
    svc.create_record("u1", amount=30000, purpose="出産祝い", party_name="佐藤", direction="received")
    assert len(svc.list_records("u3")) == 0


def test_家族はお互いのお返しイベントを操作できる():
    """同じ世帯の家族が、相手の作ったお返しイベントの状態を変更できることを検証する（共有の本質）。"""
    svc = make()
    _, ev = svc.create_record("u1", amount=10000, purpose="香典", party_name="田中", direction="received")
    svc.join_household("u2", svc.household_invite_code("u1"))
    svc.set_event_status("u2", ev.id, "done")
    assert svc.get_event("u2", ev.id).status == "done"


def test_招待コードで参加すると世帯メンバーに加わる():
    """招待コードで参加したユーザーが世帯メンバー一覧に加わることを検証する。"""
    svc = make()
    code = svc.household_invite_code("u1")
    svc.join_household("u2", code)
    ids = {m["user_id"] for m in svc.household_members("u1")}
    assert ids == {"u1", "u2"}


def test_不正な招待コードは拒否される():
    """存在しない招待コードでの参加が拒否されることを検証する。"""
    import pytest
    from app.services import ValidationError
    svc = make()
    with pytest.raises(ValidationError):
        svc.join_household("u2", "BADCODE")


def test_脱退すると世帯から外れデータは家族に残る():
    """脱退したメンバーには台帳が見えなくなり、データは残る家族側に保持されることを検証する。"""
    svc = make()
    svc.create_record("u1", amount=30000, purpose="出産祝い", party_name="佐藤", direction="received")
    svc.join_household("u2", svc.household_invite_code("u1"))
    assert len(svc.list_records("u2")) == 1   # 参加中は見える
    svc.leave_household("u2")
    assert len(svc.list_records("u2")) == 0   # 脱退後は見えない（新しい空の世帯）
    assert len(svc.list_records("u1")) == 1   # データは家族側に残る


def test_管理者が抜けると残ったメンバーが管理者を引き継ぐ():
    """owner が脱退し他メンバーが残る場合、残ったメンバーが owner を引き継ぐことを検証する。"""
    svc = make()
    svc.create_record("u1", amount=10000, purpose="出産祝い", party_name="佐藤", direction="received")
    svc.join_household("u2", svc.household_invite_code("u1"))
    svc.leave_household("u1")
    members = {m["user_id"]: m["role"] for m in svc.household_members("u2")}
    assert members == {"u2": "owner"}


def test_管理者はメンバーを外せる():
    """owner が家族メンバーを世帯から外せ、外された人には台帳が見えなくなることを検証する。"""
    svc = make()
    svc.create_record("u1", amount=10000, purpose="出産祝い", party_name="佐藤", direction="received")
    svc.join_household("u2", svc.household_invite_code("u1"))
    svc.remove_member("u1", "u2")
    assert {m["user_id"] for m in svc.household_members("u1")} == {"u1"}
    assert len(svc.list_records("u2")) == 0


def test_管理者以外はメンバーを外せない():
    """owner でないメンバーが他人を外そうとすると拒否されることを検証する（A01）。"""
    import pytest
    from app.services import ForbiddenError
    svc = make()
    svc.join_household("u2", svc.household_invite_code("u1"))
    with pytest.raises(ForbiddenError):
        svc.remove_member("u2", "u1")


def test_世帯外の人は外せない():
    """同じ世帯に属さないユーザーを外そうとすると拒否されることを検証する。"""
    import pytest
    from app.services import ValidationError
    svc = make()
    svc.resolve_household("u1")
    svc.resolve_household("stranger")  # 別世帯
    with pytest.raises(ValidationError):
        svc.remove_member("u1", "stranger")
