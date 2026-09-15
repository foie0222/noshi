"""お返し品ガイド（オフライン・外部APIなし）のテスト。"""

import pytest
from app.catalog.buckets import ITEM_CATEGORIES, PRICE_BANDS
from app.catalog.guide import GIFT_IDEAS, GiftGuide


@pytest.fixture
def guide() -> GiftGuide:
    return GiftGuide()


def test_提案は必ず1件以上返り必須項目が揃う(guide: GiftGuide) -> None:
    items = guide.suggest(budget=12000, relationship="友人", purpose="出産祝い")
    assert items
    for it in items:
        assert it["title"]
        assert it["summary"]
        assert it["price_band"]
        assert it["category"]
        assert it["category_label"]


def test_提案に外部リンクや価格などの広告項目を含めない(guide: GiftGuide) -> None:
    """楽天アフィリエイト廃止。外部参照・実売価格・計測キーは返さない。"""
    for it in guide.suggest(budget=5000, relationship="友人", purpose="出産祝い"):
        for key in ("external_ref", "price", "image_url", "item_code", "bucket", "rel_group"):
            assert key not in it


def test_弔事の用途では慶事向けの品を出さない(guide: GiftGuide) -> None:
    items = guide.suggest(budget=8000, relationship="友人", purpose="香典")
    mourn_cats = {cat for cat, _label in ITEM_CATEGORIES["mourn"]}
    assert {it["category"] for it in items} <= mourn_cats
    # お酒・食器は弔事の品目に無い（＝慶事専用）
    assert "sake" not in {it["category"] for it in items}


def test_品目カテゴリを指定するとその品目だけが返る(guide: GiftGuide) -> None:
    items = guide.suggest(budget=8000, relationship="友人", purpose="出産祝い", category="towel")
    assert items
    assert {it["category"] for it in items} == {"towel"}


def test_予算に合う品が先に並ぶ(guide: GiftGuide) -> None:
    items = guide.suggest(budget=2000, relationship="友人", purpose="出産祝い")
    # 先頭は 2,000 円が範囲に入る品（＝予算ぴったり）
    head = GIFT_IDEAS_BY_TITLE[items[0]["title"]]
    assert head.low <= 2000 <= (head.high or 10**9)


def test_未知の品目カテゴリでも空にはならない(guide: GiftGuide) -> None:
    """カテゴリ在庫のずれ（古いタブ等）でも画面を空にしない。"""
    items = guide.suggest(budget=5000, relationship="友人", purpose="出産祝い", category="unknown")
    assert items


def test_品目タブはトーン順どおりに返る(guide: GiftGuide) -> None:
    cats = guide.available_categories(budget=5000, purpose="出産祝い")
    assert [c["slug"] for c in cats] == [cat for cat, _l in ITEM_CATEGORIES["cele"]]
    assert cats[0]["label"] == "スイーツ・お菓子"
    mourn = guide.available_categories(budget=5000, purpose="香典")
    assert [c["slug"] for c in mourn] == [cat for cat, _l in ITEM_CATEGORIES["mourn"]]


def test_どの価格帯でも全品目に候補がある() -> None:
    """タブを切り替えて空になる画面を作らない（全帯×全品目に最低1件）。"""
    g = GiftGuide()
    for low, _high, _label in PRICE_BANDS:
        for tone, purpose in (("cele", "出産祝い"), ("mourn", "香典")):
            for cat, _label2 in ITEM_CATEGORIES[tone]:
                assert g.suggest(low, "友人", purpose, cat), f"{low}/{tone}/{cat}"


def test_のしマナーは用途ごとに表書きと水引を返す(guide: GiftGuide) -> None:
    e = guide.etiquette("出産祝い")
    assert e["omotegaki"] == "内祝"
    assert "蝶結び" in e["mizuhiki"]
    assert e["timing"]
    koden = guide.etiquette("香典")
    assert koden["omotegaki"] == "志"
    assert "結び切り" in koden["mizuhiki"]


def test_未知の用途のマナーはトーンで安全側に振り分ける(guide: GiftGuide) -> None:
    assert guide.etiquette("叔父の法要")["omotegaki"] == "志"
    assert guide.etiquette("昇進祝い")["omotegaki"] == "内祝"


def test_同じ入力なら常に同じ並び(guide: GiftGuide) -> None:
    """外部APIもLLMも使わない決定論的な提案であること。"""
    a = guide.suggest(budget=7000, relationship="同僚・仕事", purpose="結婚祝い")
    b = guide.suggest(budget=7000, relationship="同僚・仕事", purpose="結婚祝い")
    assert [x["title"] for x in a] == [x["title"] for x in b]


def test_続柄グループに合う品が優先される(guide: GiftGuide) -> None:
    work = guide.suggest(budget=5000, relationship="同僚・仕事", purpose="出産祝い")
    family = guide.suggest(budget=5000, relationship="親", purpose="出産祝い")
    assert [x["title"] for x in work] != [x["title"] for x in family]


GIFT_IDEAS_BY_TITLE = {i.title: i for i in GIFT_IDEAS}
