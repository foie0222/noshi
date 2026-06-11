"""楽天APIクライアントのテスト。fetch 注入でネットワーク不要。"""

import json
from pathlib import Path

from app.catalog.rakuten import RakutenClient

FIXTURES = Path(__file__).parent / "fixtures"


def _client(payload: dict) -> tuple["RakutenClient", list[str]]:
    calls: list[str] = []

    def fake_fetch(url: str) -> dict:
        calls.append(url)
        return payload

    c = RakutenClient(app_id="APP", affiliate_id="AFF", fetch=fake_fetch, sleep=lambda s: None)
    return c, calls


def test_検索結果を正規化して返す():
    payload = json.loads((FIXTURES / "rakuten_search.json").read_text())
    c, calls = _client(payload)
    items = c.search_items("出産内祝い", 5000, 9999, page=1)
    assert len(items) == 2
    a = items[0]
    assert a["item_code"] == "shopA:10001"
    assert a["title"] == "今治タオル ギフトセット 内祝い"
    assert a["price"] == 5400
    assert a["rating"] == 4.62
    assert a["review_count"] == 812
    assert a["point_rate"] == 5
    assert a["point_end"] == "2026-06-15T09:59:00+09:00"  # JST として ISO 化
    assert a["affiliate_url"].startswith("https://hb.afl.rakuten.co.jp/")
    assert a["image_url"].startswith("https://thumbnail.image.rakuten.co.jp/")
    assert a["availability"] == 1 and a["gift_flag"] == 1
    # クエリに必須パラメータが乗る
    assert "applicationId=APP" in calls[0] and "affiliateId=AFF" in calls[0]
    assert "minPrice=5000" in calls[0] and "maxPrice=9999" in calls[0]


def test_画像なしでも壊れない():
    payload = json.loads((FIXTURES / "rakuten_search.json").read_text())
    c, _ = _client(payload)
    assert c.search_items("x", 1000, 2999, page=1)[1]["image_url"] == ""


def test_ランキングはitemCodeから順位の辞書を返す():
    payload = json.loads((FIXTURES / "rakuten_ranking.json").read_text())
    c, _ = _client(payload)
    ranks = c.ranking("208813")
    assert ranks == {"shopA:10001": 3, "shopC:30003": 1}


def test_リクエスト間に1秒スリープする():
    payload = json.loads((FIXTURES / "rakuten_search.json").read_text())
    slept: list[float] = []
    c = RakutenClient(
        app_id="A",
        affiliate_id="F",
        fetch=lambda url: payload,
        sleep=slept.append,
    )
    c.search_items("x", 1000, 2999, page=1)
    c.search_items("x", 1000, 2999, page=2)
    assert slept == [1.0]  # 2回目の前に1秒（初回はスリープなし）


def test_失敗時は2秒待って1回だけリトライする():
    payload = json.loads((FIXTURES / "rakuten_search.json").read_text())
    attempts: list[int] = []

    def flaky(url: str) -> dict:
        attempts.append(1)
        if len(attempts) == 1:
            raise OSError("503")
        return payload

    slept: list[float] = []
    c = RakutenClient(app_id="A", affiliate_id="F", fetch=flaky, sleep=slept.append)
    assert len(c.search_items("x", 1000, 2999, page=1)) == 2
    assert len(attempts) == 2 and 2.0 in slept


def test_日次上限を超えるとRuntimeError():
    import pytest

    payload = json.loads((FIXTURES / "rakuten_search.json").read_text())
    c = RakutenClient(
        app_id="A",
        affiliate_id="F",
        fetch=lambda url: payload,
        sleep=lambda s: None,
        max_calls=2,
    )
    c.search_items("x", 1000, 2999, page=1)
    c.search_items("x", 1000, 2999, page=2)
    with pytest.raises(RuntimeError):
        c.search_items("x", 1000, 2999, page=3)
