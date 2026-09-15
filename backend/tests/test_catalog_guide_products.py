"""編集コンテンツ（提案カード）に、CI 生成の実商品をぶら下げる。"""

import json

from app.catalog.guide import GiftGuide
from app.catalog.products import ProductCatalog


def _product(title, code="a"):
    return {
        "title": title,
        "shop": "テスト店",
        "url": f"https://hb.afl.rakuten.co.jp/hgc/{code}",
        "image": "https://thumbnail.image.rakuten.co.jp/a.jpg",
        "rating": 4.5,
        "reviews": 800,
    }


def _catalog(tmp_path, buckets, generated_at="2026-09-15"):
    p = tmp_path / "items.json"
    p.write_text(
        json.dumps({"generated_at": generated_at, "buckets": buckets}, ensure_ascii=False),
        encoding="utf-8",
    )
    return ProductCatalog(p)


def test_提案カードに同じ品目の実商品が付く(tmp_path):
    guide = GiftGuide(
        _catalog(tmp_path, {"cele#catalog@15000-24999": [_product("カタログギフト A")]})
    )
    got = guide.suggest(budget=15000, relationship="友人", purpose="出産祝い", category="catalog")
    assert got[0]["products"][0]["title"] == "カタログギフト A"


def test_商品が無い品目でも提案は返る(tmp_path):
    # 初回ビルド前・その帯に売れ筋が無い場合でも、編集コンテンツだけで成立させる
    guide = GiftGuide(_catalog(tmp_path, {}))
    got = guide.suggest(budget=15000, relationship="友人", purpose="出産祝い")
    assert got and all(s["products"] == [] for s in got)


def test_カタログを渡さなくても動く():
    # 既定の items.json が未生成でも API を落とさない
    got = GiftGuide().suggest(budget=15000, relationship="友人", purpose="出産祝い")
    assert got and "products" in got[0]


def test_同じ商品が複数のカードに重複して出ない(tmp_path):
    # 同じ品目の提案が複数並ぶとき、同じ商品を並べると選ぶ意味が無くなる
    rows = [_product(f"タオル{i}", code=str(i)) for i in range(6)]
    guide = GiftGuide(_catalog(tmp_path, {"cele#towel@5000-9999": rows}))
    got = guide.suggest(budget=5000, relationship="友人", purpose="出産祝い", category="towel")
    urls = [p["url"] for s in got for p in s["products"]]
    assert len(urls) == len(set(urls))


def test_1カードあたりの商品は3件まで(tmp_path):
    rows = [_product(f"タオル{i}", code=str(i)) for i in range(10)]
    guide = GiftGuide(_catalog(tmp_path, {"cele#towel@5000-9999": rows}))
    got = guide.suggest(budget=5000, relationship="友人", purpose="出産祝い", category="towel")
    assert all(len(s["products"]) <= 3 for s in got)


def test_弔事の予算帯のバケツを引く(tmp_path):
    guide = GiftGuide(_catalog(tmp_path, {"mourn#drink@3000-4999": [_product("緑茶詰合せ")]}))
    got = guide.suggest(budget=3000, relationship="親族", purpose="香典", category="drink")
    assert got[0]["products"][0]["title"] == "緑茶詰合せ"


def test_生成日を返す(tmp_path):
    guide = GiftGuide(_catalog(tmp_path, {}, generated_at="2026-09-15"))
    assert guide.catalog_generated_at() == "2026-09-15"
