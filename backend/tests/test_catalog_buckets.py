"""分類軸（用途カテゴリslug・価格帯・品目カテゴリ）のテスト。"""

from app.catalog.buckets import (
    CATEGORIES,
    ITEM_CATEGORIES,
    ITEM_CATEGORY_LABELS,
    PRICE_BANDS,
    band_label,
    band_of,
    item_category_key,
    slug_of,
    tone_slug,
)


def test_カテゴリは9個でASCIIスラッグ():
    assert set(CATEGORIES) == {
        "baby",
        "wedding",
        "school",
        "housewarming",
        "kaiki",
        "koden",
        "ochugen",
        "oseibo",
        "general",
    }


def test_既定用途はスラッグに写像される():
    assert slug_of("出産祝い") == "baby"
    assert slug_of("結婚祝い") == "wedding"
    assert slug_of("入学祝い") == "school"
    assert slug_of("新築祝い") == "housewarming"
    assert slug_of("快気祝い") == "kaiki"
    assert slug_of("香典") == "koden"
    assert slug_of("お中元") == "ochugen"
    assert slug_of("お歳暮") == "oseibo"
    assert slug_of("お年賀") == "general"
    assert slug_of("その他") == "general"


def test_カスタム用途はトーンで振り分ける():
    assert slug_of("叔父の法要") == "koden"  # mourning → koden
    assert slug_of("引っ越し祝いのお礼") == "general"  # celebration → general


def test_価格帯は7個で境界が正しい():
    assert len(PRICE_BANDS) == 7
    assert band_of(1000) == "1000-2999"
    assert band_of(2999) == "1000-2999"
    assert band_of(3000) == "3000-4999"
    assert band_of(9999) == "5000-9999"
    assert band_of(10000) == "10000-14999"
    assert band_of(14999) == "10000-14999"
    assert band_of(15000) == "15000-24999"
    assert band_of(24999) == "15000-24999"
    assert band_of(25000) == "25000-49999"
    assert band_of(49999) == "25000-49999"
    assert band_of(50000) == "50000-"
    assert band_of(999999) == "50000-"


def test_1000円未満は最下帯に丸める():
    assert band_of(0) == "1000-2999"
    assert band_of(999) == "1000-2999"


def test_価格帯ラベルは上限と下限で表記が変わる():
    assert band_label("5000-9999") == "〜¥9,999"
    assert band_label("50000-") == "¥50,000〜"


def test_品目カテゴリはトーン別にタブ表示順で並ぶ():
    assert [c for c, _l in ITEM_CATEGORIES["cele"]] == [
        "sweets",
        "gourmet",
        "drink",
        "towel",
        "tableware",
        "sake",
        "catalog",
    ]
    assert [c for c, _l in ITEM_CATEGORIES["mourn"]] == [
        "drink",
        "food",
        "towel",
        "daily",
        "catalog",
    ]
    # 表示名の逆引きは "tone#cat" をキーにする
    assert ITEM_CATEGORY_LABELS["mourn#daily"] == "洗剤・日用品"
    assert len(ITEM_CATEGORY_LABELS) == 12


def test_tone_slug_と_item_category_key():
    assert tone_slug("出産祝い") == "cele"
    assert tone_slug("香典") == "mourn"
    assert item_category_key("cele", "towel") == "cele#towel"
