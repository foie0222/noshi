import pytest
from app.domain.entities import GiftRecord, Household, Membership
from app.repository import InMemoryRepository
from scripts.migrate_account_links import MigrationAbort, plan_migration


def _seed():
    repo = InMemoryRepository()
    repo.put_household(Household(id="HH_SHARED"))
    repo.put_membership(
        Membership(user_id="primaryG", household_id="HH_SHARED", role="owner", email="a@x.com")
    )
    repo.put_household(Household(id="HH_NATIVE"))
    repo.put_membership(
        Membership(user_id="subNative", household_id="HH_NATIVE", role="owner", email="a@x.com")
    )
    return repo


def test_空世帯の別名を代表に貼る計画ができる():
    repo = _seed()
    actions = plan_migration(
        repo, primary="primaryG", aliases=["subNative"], protected_household="HH_SHARED"
    )
    assert ("link", "subNative", "primaryG") in actions
    assert ("delete_household", "HH_NATIVE") in actions


def test_別名世帯が非空ならabortする():
    repo = _seed()
    repo.put_record(GiftRecord(user_id="HH_NATIVE", party_name="x", amount=1, purpose="出産祝い"))
    with pytest.raises(MigrationAbort):
        plan_migration(
            repo, primary="primaryG", aliases=["subNative"], protected_household="HH_SHARED"
        )


def test_別名世帯が続柄だけ持っても非空でabortする():
    repo = _seed()
    repo.add_household_relationship("HH_NATIVE", "兄")
    with pytest.raises(MigrationAbort):
        plan_migration(
            repo, primary="primaryG", aliases=["subNative"], protected_household="HH_SHARED"
        )


def test_代表が別名集合に含まれたらabort():
    repo = _seed()
    with pytest.raises(MigrationAbort):
        plan_migration(
            repo, primary="primaryG", aliases=["primaryG"], protected_household="HH_SHARED"
        )


def test_別名membershipが保護世帯を指したらabort():
    repo = _seed()
    repo.put_membership(
        Membership(user_id="subNative", household_id="HH_SHARED", role="owner", email="a@x.com")
    )
    with pytest.raises(MigrationAbort):
        plan_migration(
            repo, primary="primaryG", aliases=["subNative"], protected_household="HH_SHARED"
        )


def test_代表membershipが存在しなければabort():
    repo = _seed()
    with pytest.raises(MigrationAbort):
        plan_migration(
            repo, primary="missingPrimary", aliases=["subNative"], protected_household="HH_SHARED"
        )


def test_代表が既に別名ならabort():
    repo = _seed()
    repo.put_account_link("primaryG", "someoneElse")
    with pytest.raises(MigrationAbort):
        plan_migration(
            repo, primary="primaryG", aliases=["subNative"], protected_household="HH_SHARED"
        )


def test_代表世帯が想定外ならabort():
    repo = _seed()
    with pytest.raises(MigrationAbort):
        plan_migration(
            repo, primary="primaryG", aliases=["subNative"], protected_household="DIFFERENT"
        )


def test_apply_migrationで別名リンクと空世帯削除とメール代表設定が反映される():
    repo = _seed()
    from scripts.migrate_account_links import apply_migration

    actions = plan_migration(
        repo, primary="primaryG", aliases=["subNative"], protected_household="HH_SHARED"
    )
    apply_migration(repo, actions)
    assert repo.get_account_link("subNative") == "primaryG"
    assert repo.get_membership("subNative") is None
    assert repo.get_household("HH_NATIVE") is None
    assert repo.get_email_primary("a@x.com") == "primaryG"
