"""DynamoCatalogAdapter（配信）のテスト。スペック§8の鮮度マスクと§9の補完規則。"""

from datetime import UTC, datetime, timedelta

from app.catalog.adapter import DynamoCatalogAdapter
from app.ports import GiftCatalogMock

NOW = datetime(2026, 6, 11, 12, 0, tzinfo=UTC)


def _row(code="shop:1", fetched=None, sale="ポイント5倍", sale_ends=""):
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
        "bucket": "BUCKET#baby#5000-9999",
        "rank": "RANK#01",
    }


class FakeStore:
    def __init__(self, buckets):
        self.buckets = buckets  # {(slug, band): [rows]}
        self.clicks = []

    def read_bucket(self, slug, band, now):
        return self.buckets.get((slug, band), [])

    def put_click(self, item_code, bucket, position, now):
        self.clicks.append((item_code, bucket, position))


def _adapter(buckets):
    return DynamoCatalogAdapter(
        store=FakeStore(buckets), fallback=GiftCatalogMock(), now=lambda: NOW
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
    a.log_click("shop:1", "BUCKET#baby#5000-9999", 2)
    assert store.clicks == [("shop:1", "BUCKET#baby#5000-9999", 2)]
