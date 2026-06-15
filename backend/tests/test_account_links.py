from app.account import canonical_sub
from app.repository import InMemoryRepository


def test_email_primary_の条件付き確保は最初の1人だけ勝つ():
    repo = InMemoryRepository()
    assert repo.claim_email_primary("a@x.com", "subA") is True  # 先着が勝つ
    assert repo.claim_email_primary("a@x.com", "subB") is False  # 後着は負ける
    assert repo.get_email_primary("a@x.com") == "subA"


def test_account_link_の作成と解決と逆引き():
    repo = InMemoryRepository()
    repo.put_account_link("alias1", "primaryX", provider="SignInWithApple", email="")
    assert repo.get_account_link("alias1") == "primaryX"
    assert repo.get_account_link("unknown") is None
    assert repo.list_aliases("primaryX") == ["alias1"]
    assert repo._account_links["alias1"].linked_at != ""


def test_email_primary_の張替えと削除():
    repo = InMemoryRepository()
    repo.claim_email_primary("a@x.com", "subA")
    repo.set_email_primary("a@x.com", "subC")  # 張替え（無条件）
    assert repo.get_email_primary("a@x.com") == "subC"
    repo.delete_email_primary("a@x.com")
    assert repo.get_email_primary("a@x.com") is None


def test_canonical_sub_は_別名を代表に解決し_別名でなければそのまま():
    repo = InMemoryRepository()
    repo.put_account_link("alias1", "primaryX")
    assert canonical_sub(repo, "alias1") == "primaryX"
    assert canonical_sub(repo, "primaryX") == "primaryX"  # 代表はそのまま
    assert canonical_sub(repo, "unknown") == "unknown"  # 未知もそのまま（新規扱い）
