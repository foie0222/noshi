"""DynamoCatalogAdapter（配信）のテスト。スペック§8の鮮度マスクと§9の補完規則。"""

from datetime import UTC, datetime, timedelta

from app.catalog.adapter import DynamoCatalogAdapter
from app.ports import GiftCatalogMock

NOW = datetime(2026, 6, 11, 12, 0, tzinfo=UTC)


def _row(
    code="shop:1",
    fetched=None,
    sale="ポイント5倍",
    sale_ends="",
    bucket="BUCKET#baby#5000-9999",
    fit=None,
):
    return {
        "item_code": code,
        "title": "今治タオル",
        "price": 5400,
        "price_fetched_at": (fetched or NOW).isoformat(),
        "image_url": "https://x.jpg",
        "shop_name": "店",
        "affiliate_url": "https://hb.afl.rakuten.co.jp/x",
        "reason": "上質で人気の定番です",
        "sale_note": sale,
        "sale_ends_at": sale_ends,
        "rating": 4.5,
        "review_count": 800,
        "bucket": bucket,
        "rank": "RANK#01",
        "fit": fit or {"family": 50, "friend": 50, "work": 50, "other": 50},
    }


class FakeStore:
    def __init__(self, buckets, manifests=None):
        self.buckets = buckets  # {(slug, band): [rows]}
        self.manifests = manifests or {}  # {(tone, band): [cat, ...]}
        self.clicks = []

    def read_bucket(self, slug, band, now):
        return self.buckets.get((slug, band), [])

    def read_manifest(self, tone, band, now):
        return self.manifests.get((tone, band), [])

    def put_click(self, item_code, bucket, position, rel_group, now):
        self.clicks.append((item_code, bucket, position, rel_group))


def _adapter(buckets, manifests=None):
    return DynamoCatalogAdapter(
        store=FakeStore(buckets, manifests), fallback=GiftCatalogMock(), now=lambda: NOW
    )


def test_ヒット時は拡張フィールドつきで返す():
    a = _adapter({("baby", "5000-9999"): [_row()]})
    out = a.suggest(budget=7000, relationship="友人", purpose="出産祝い")
    s = out[0]
    assert s["title"] == "今治タオル"
    assert s["summary"] == "上質で人気の定番です"
    assert s["external_ref"].startswith("https://hb.afl.rakuten.co.jp/")
    assert s["price"] == 5400 and s["sale_note"] == "ポイント5倍"
    assert s["item_code"] == "shop:1" and s["position"] == 1
    assert s["price_band"] == "〜¥9,999"


def test_23時間を超えた価格とセールはマスクされる():
    old = NOW - timedelta(hours=23, minutes=1)
    a = _adapter({("baby", "5000-9999"): [_row(fetched=old)]})
    s = a.suggest(7000, "友人", "出産祝い")[0]
    assert "price" not in s and "price_fetched_at" not in s and "sale_note" not in s
    assert s["title"] == "今治タオル"  # 商品情報は3ヶ月枠なので出る


def test_22時間台はマスクされない():
    ok = NOW - timedelta(hours=22, minutes=59)
    a = _adapter({("baby", "5000-9999"): [_row(fetched=ok)]})
    assert a.suggest(7000, "友人", "出産祝い")[0]["price"] == 5400


def test_セール期限切れはsale_noteだけ落ちる():
    a = _adapter({("baby", "5000-9999"): [_row(sale_ends=(NOW - timedelta(hours=1)).isoformat())]})
    s = a.suggest(7000, "友人", "出産祝い")[0]
    assert "sale_note" not in s and s["price"] == 5400


def test_tzなしのprice_fetched_atは安全側でマスクされる():
    naive = datetime(2026, 6, 11, 12, 0)  # noqa: DTZ001 -- tz-naive を意図的に検証
    a = _adapter({("baby", "5000-9999"): [_row(fetched=naive)]})
    s = a.suggest(7000, "友人", "出産祝い")[0]
    assert "price" not in s and "price_fetched_at" not in s and "sale_note" not in s
    assert s["title"] == "今治タオル"


def test_tzなしのsale_ends_atはsale_noteだけ落ちる():
    a = _adapter({("baby", "5000-9999"): [_row(sale_ends="2026-06-11T00:00:00")]})
    s = a.suggest(7000, "友人", "出産祝い")[0]
    assert "sale_note" not in s and s["price"] == 5400


def test_3件未満なら隣接帯から下側優先で補完する():
    a = _adapter(
        {
            ("baby", "5000-9999"): [_row("shop:1")],
            ("baby", "3000-4999"): [_row("shop:2")],
            ("baby", "10000-14999"): [_row("shop:3")],
        }
    )
    out = a.suggest(7000, "友人", "出産祝い")
    assert [s["item_code"] for s in out] == ["shop:1", "shop:2", "shop:3"]


def test_隣接帯補完で同一商品は重複しない():
    a = _adapter(
        {
            ("baby", "5000-9999"): [_row("shop:1")],
            ("baby", "3000-4999"): [_row("shop:1"), _row("shop:2")],
        }
    )
    out = a.suggest(7000, "友人", "出産祝い")
    assert [s["item_code"] for s in out] == ["shop:1", "shop:2"]


def test_補完商品の価格帯ラベルは商品自身の帯になる():
    a = _adapter(
        {
            ("baby", "5000-9999"): [_row("shop:1")],
            ("baby", "10000-14999"): [_row("shop:3", bucket="BUCKET#baby#10000-14999")],
        }
    )
    out = a.suggest(7000, "友人", "出産祝い")
    assert out[0]["price_band"] == "〜¥9,999"  # 自バケツ品はリクエスト帯のまま
    assert out[1]["price_band"] == "〜¥14,999"  # 補完品は自身の帯で表示


def test_3件以上あれば補完しない():
    rows = [_row(f"shop:{i}") for i in range(3)]
    a = _adapter({("baby", "5000-9999"): rows, ("baby", "3000-4999"): [_row("shop:9")]})
    assert len(a.suggest(7000, "友人", "出産祝い")) == 3


def test_全空なら金額目安フォールバック():
    a = _adapter({})
    out = a.suggest(7000, "友人", "出産祝い")
    assert len(out) >= 1  # GiftCatalogMock の固定候補
    assert "item_code" not in out[0]  # フォールバックは計測対象外


def test_log_clickはストアに委譲する():
    store = FakeStore({})
    a = DynamoCatalogAdapter(store=store, fallback=GiftCatalogMock(), now=lambda: NOW)
    a.log_click("shop:1", "BUCKET#baby#5000-9999", 2, "")
    assert store.clicks == [("shop:1", "BUCKET#baby#5000-9999", 2, "")]


# ── fit ソート・rel_group テスト ─────────────────────────────────────────────


def _fit(family=50, friend=50, work=50, other=50):
    return {"family": family, "friend": friend, "work": work, "other": other}


def test_続柄グループによって並び順が変わる():
    rows = [
        _row("shop:1", fit=_fit(family=90, work=30)),
        _row("shop:2", fit=_fit(family=30, work=90)),
        _row("shop:3", fit=_fit(family=60, work=60)),
    ]
    a = _adapter({("baby", "5000-9999"): rows})
    fam = [s["item_code"] for s in a.suggest(7000, "親", "出産祝い")]
    work = [s["item_code"] for s in a.suggest(7000, "同僚・仕事", "出産祝い")]
    assert fam == ["shop:1", "shop:3", "shop:2"]
    assert work == ["shop:2", "shop:3", "shop:1"]


def test_fitの差9点以内はRANK順を維持する():
    # 量子化（//10）: 61 と 69 は同じ帯 → 元の順序（RANK順）を維持
    rows = [_row("shop:1", fit=_fit(family=61)), _row("shop:2", fit=_fit(family=69))]
    a = _adapter({("baby", "5000-9999"): rows})
    assert [s["item_code"] for s in a.suggest(7000, "親", "出産祝い")] == ["shop:1", "shop:2"]


def test_fitが10点帯を跨げば逆転する():
    rows = [_row("shop:1", fit=_fit(family=69)), _row("shop:2", fit=_fit(family=70))]
    a = _adapter({("baby", "5000-9999"): rows})
    assert [s["item_code"] for s in a.suggest(7000, "親", "出産祝い")] == ["shop:2", "shop:1"]


def test_補完分は高fitでも自バケツの後ろ():
    a = _adapter(
        {
            ("baby", "5000-9999"): [_row("shop:1", fit=_fit(family=10))],
            ("baby", "3000-4999"): [
                _row("shop:2", bucket="BUCKET#baby#3000-4999", fit=_fit(family=95)),
            ],
        }
    )
    out = a.suggest(7000, "親", "出産祝い")
    assert [s["item_code"] for s in out] == ["shop:1", "shop:2"]  # 価格帯適合 > 続柄適合


def test_fitが無い旧データ行は順序不変():
    # store の補完を経ない fit キー欠損行でもソートキー0で中立（RANK順維持）
    rows = [_row("shop:1"), _row("shop:2"), _row("shop:3")]
    for r in rows:
        del r["fit"]
    a = _adapter({("baby", "5000-9999"): rows})
    out = [s["item_code"] for s in a.suggest(7000, "親", "出産祝い")]
    assert out == ["shop:1", "shop:2", "shop:3"]


def test_レスポンスにrel_groupが付く():
    a = _adapter({("baby", "5000-9999"): [_row()]})
    assert a.suggest(7000, "親", "出産祝い")[0]["rel_group"] == "family"
    assert a.suggest(7000, "", "出産祝い")[0]["rel_group"] == "other"


def test_log_clickはrel_groupをストアへ透過する():
    store = FakeStore({})
    a = DynamoCatalogAdapter(store=store, fallback=GiftCatalogMock(), now=lambda: NOW)
    a.log_click("shop:1", "BUCKET#baby#5000-9999", 2, "work")
    assert store.clicks == [("shop:1", "BUCKET#baby#5000-9999", 2, "work")]


def test_category指定で品目バケツを引く():
    row = _row(code="shop:t1", bucket="BUCKET#cele#towel#5000-9999")
    a = _adapter({("cele#towel", "5000-9999"): [row]})
    out = a.suggest(budget=7000, relationship="友人", purpose="出産祝い", category="towel")
    assert out[0]["item_code"] == "shop:t1"
    # 4セグメントのバケツPKでも価格帯ラベルが正しく出る
    assert out[0]["price_band"] == "〜¥9,999"


def test_category無指定は従来の用途バケツ():
    a = _adapter({("baby", "5000-9999"): [_row()]})
    out = a.suggest(budget=7000, relationship="友人", purpose="出産祝い")
    assert out[0]["item_code"] == "shop:1"


def test_available_categoriesはマニフェスト順に表示名つきで返す():
    a = _adapter(
        {},
        manifests={("cele", "5000-9999"): ["towel", "catalog"]},
    )
    cats = a.available_categories(budget=7000, purpose="出産祝い")
    assert cats == [
        {"slug": "towel", "label": "タオル・寝具"},
        {"slug": "catalog", "label": "カタログギフト"},
    ]


def test_available_categoriesはマニフェスト未登録なら空():
    a = _adapter({})
    assert a.available_categories(budget=7000, purpose="香典") == []
