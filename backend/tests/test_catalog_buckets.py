"""バケツ定義（カテゴリslug・価格帯・写像）のテスト。スペック§5に対応。"""

from app.catalog.buckets import (
    CATEGORIES,
    PRICE_BANDS,
    RAKUTEN_GENRE_BY_CATEGORY,
    band_neighbors,
    band_of,
    bucket_pk,
    slug_of,
)


def test_カテゴリは9個でASCIIスラッグ():
    assert len(CATEGORIES) == 9
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
    # ジャンルID表のキーはカテゴリと常に一致させる
    assert set(RAKUTEN_GENRE_BY_CATEGORY) == set(CATEGORIES)


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


def test_隣接帯は下側優先で返る():
    assert band_neighbors("5000-9999") == ["3000-4999", "10000-14999"]
    assert band_neighbors("1000-2999") == ["3000-4999"]  # 下端: 上のみ
    assert band_neighbors("50000-") == ["25000-49999"]  # 上端: 下のみ


def test_バケツPKの形式():
    assert bucket_pk("baby", "5000-9999") == "BUCKET#baby#5000-9999"


def test_品目タクソノミの派生テーブルがトーン別に揃う():
    from app.catalog.buckets import (
        ITEM_CATEGORIES,
        ITEM_CATEGORY_KEYWORDS,
        ITEM_CATEGORY_LABELS,
    )

    assert [c for c, _l, _k in ITEM_CATEGORIES["cele"]] == [
        "sweets",
        "gourmet",
        "drink",
        "towel",
        "tableware",
        "sake",
        "catalog",
    ]
    assert [c for c, _l, _k in ITEM_CATEGORIES["mourn"]] == [
        "drink",
        "food",
        "towel",
        "daily",
        "catalog",
    ]
    # 派生テーブルは "tone#cat" をキーにする
    assert ITEM_CATEGORY_KEYWORDS["cele#towel"] == "内祝い タオル ギフト"
    assert ITEM_CATEGORY_LABELS["mourn#daily"] == "洗剤・日用品"
    assert len(ITEM_CATEGORY_KEYWORDS) == 12
    # 広げたキーワードが反映されている（スペック2026-06-18 検索ヒット改善）
    assert ITEM_CATEGORY_KEYWORDS["cele#drink"] == "内祝い コーヒー ギフト"
    assert ITEM_CATEGORY_KEYWORDS["mourn#drink"] == "香典返し お茶 ギフト"
    assert ITEM_CATEGORY_KEYWORDS["mourn#food"] == "香典返し グルメ"
    assert ITEM_CATEGORY_KEYWORDS["mourn#daily"] == "香典返し 洗剤"


def test_tone_slug_と_item_bucket_slug():
    from app.catalog.buckets import item_bucket_slug, tone_slug

    assert tone_slug("出産祝い") == "cele"
    assert tone_slug("香典") == "mourn"
    assert item_bucket_slug("cele", "towel") == "cele#towel"
