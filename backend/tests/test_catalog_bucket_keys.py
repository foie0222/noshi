"""商品バケツのキーと範囲。build（CI）と実行時（Lambda）で同じ関数を使う。"""

import pytest
from app.catalog.buckets import PRICE_BANDS, all_buckets, band_range, bucket_key


def test_バケツキーは品目キーと価格帯を連結する():
    assert bucket_key("cele", "sweets", "5000-9999") == "cele#sweets@5000-9999"
    assert bucket_key("mourn", "food", "50000-") == "mourn#food@50000-"


def test_全バケツは品目12かける価格帯7で84個():
    buckets = all_buckets()
    assert len(buckets) == 84
    assert len({bucket_key(t, c, b) for t, c, b in buckets}) == 84


def test_全バケツは慶事7品目と弔事5品目を含む():
    cele = {c for t, c, _b in all_buckets() if t == "cele"}
    mourn = {c for t, c, _b in all_buckets() if t == "mourn"}
    assert len(cele) == 7 and len(mourn) == 5
    assert "sweets" in cele and "daily" in mourn


def test_価格帯は下限と上限の組に戻せる():
    assert band_range("5000-9999") == (5000, 9999)
    assert band_range("1000-2999") == (1000, 2999)


def test_最上帯は上限なしを表すNoneを返す():
    assert band_range("50000-") == (50000, None)


def test_価格帯の範囲はPRICE_BANDSの定義と一致する():
    for low, high, label in PRICE_BANDS:
        assert band_range(label) == (low, high)


def test_未知の価格帯は例外にする():
    # 綴り間違いを黙って最下帯に丸めると、誤った価格の商品を集めてしまう
    with pytest.raises(KeyError):
        band_range("9999-99999")
