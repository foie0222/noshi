"""続柄→グループ写像のテスト。スペック§2に対応。"""

from app.catalog.relationships import GROUPS, group_of
from app.domain import rules


def test_グループは4つ():
    assert GROUPS == ("family", "friend", "work", "other")


def test_既定続柄は表引きで写像される():
    assert group_of("親") == "family"
    assert group_of("子") == "family"
    assert group_of("兄弟姉妹") == "family"
    assert group_of("祖父母") == "family"
    assert group_of("叔父・叔母") == "family"
    assert group_of("いとこ") == "family"
    assert group_of("配偶者の親族") == "family"
    assert group_of("友人") == "friend"
    assert group_of("同僚・仕事") == "work"
    assert group_of("近所") == "other"
    assert group_of("その他") == "other"


def test_既定続柄の全値が表に存在する():
    """rules.RELATIONSHIP_DEFAULTS とのパリティ（マスタ追加時の漏れ検知）。"""
    from app.catalog.relationships import _DEFAULT_MAP

    assert set(_DEFAULT_MAP) == set(rules.RELATIONSHIP_DEFAULTS)


def test_カスタム続柄はキーワードで振り分ける():
    assert group_of("会社の先輩") == "work"  # work が family/friend より優先
    assert group_of("職場の友人") == "work"
    assert group_of("義母") == "family"
    assert group_of("甥っ子") == "family"
    assert group_of("ママ友") == "friend"


def test_義務などの誤マッチはしない():
    # 単独の「義」はキーワードにしない（義父/義母…の2文字パターンのみ）
    assert group_of("義務さん") == "other"


def test_未知と空文字はother():
    assert group_of("ご近所の方") == "other"
    assert group_of("") == "other"
