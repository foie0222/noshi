"""CI で走る items.json ビルド。楽天APIは注入したクライアントで差し替える。"""

import pytest
from app.catalog.buckets import all_buckets, bucket_key
from tools.catalog.build import build, global_mean, rank_bucket
from tools.catalog.keywords import keyword_for
from tools.catalog.rakuten import RakutenBudgetExceeded


def _item(code="shop:1", title="今治タオル ギフト", rating=4.5, reviews=800, **over):
    base = {
        "item_code": code,
        "title": title,
        "price": 5400,
        "item_url": "https://item.rakuten.co.jp/x",
        "affiliate_url": f"https://hb.afl.rakuten.co.jp/hgc/{code}",
        "image_url": "https://thumbnail.image.rakuten.co.jp/a.jpg",
        "shop_name": "テスト店",
        "rating": rating,
        "review_count": reviews,
        "point_rate": 1,
        "point_end": "",
        "availability": 1,
        "gift_flag": 1,
    }
    base.update(over)
    return base


class _FakeClient:
    """バケツごとに固定の検索結果を返す。呼ばれたキーワードを記録する。"""

    def __init__(self, items=None, fail_on=None, budget_out=False):
        self._items = items if items is not None else [_item()]
        self.calls: list[tuple[str, int, int | None]] = []
        self._fail_on = fail_on or set()
        self._budget_out = budget_out

    def search_items(self, keyword, min_price, max_price, page):
        self.calls.append((keyword, min_price, max_price))
        if self._budget_out:
            raise RakutenBudgetExceeded("上限")
        if keyword in self._fail_on:
            raise RuntimeError("楽天APIエラー")
        return list(self._items)


# --- ランク付け ---


def test_ゲートを通らない商品は入らない():
    items = [_item(code="ok"), _item(code="ng", reviews=3)]
    got = rank_bucket(items, "cele#towel", ranking={}, mean=4.2, limit=10)
    assert [p["title"] for p in got] == ["今治タオル ギフト"]
    assert len(got) == 1


def test_スコアの高い順に並ぶ():
    low = _item(code="low", title="タオルA", rating=4.1, reviews=25)
    high = _item(code="high", title="タオルB", rating=4.9, reviews=3000)
    got = rank_bucket([low, high], "cele#towel", ranking={}, mean=4.2, limit=10)
    assert [p["title"] for p in got] == ["タオルB", "タオルA"]


def test_上位は指定件数で打ち切る():
    items = [_item(code=f"s:{i}", title=f"タオル{i}", reviews=100 + i) for i in range(30)]
    assert len(rank_bucket(items, "cele#towel", ranking={}, mean=4.2, limit=10)) == 10


def test_ランキング上位の商品はトレンド加点で上がる():
    a = _item(code="a", title="タオルA")
    b = _item(code="b", title="タオルB")
    flat = rank_bucket([a, b], "cele#towel", ranking={}, mean=4.2, limit=10)
    boosted = rank_bucket([a, b], "cele#towel", ranking={"b": 1}, mean=4.2, limit=10)
    assert [p["title"] for p in flat] == ["タオルA", "タオルB"]  # 同点は item_code 順で安定
    assert boosted[0]["title"] == "タオルB"


def test_出力に価格を含めない():
    # 楽天の24時間ルールを避けるため、実売価格は保存しない
    got = rank_bucket([_item()], "cele#towel", ranking={}, mean=4.2, limit=10)
    assert "price" not in got[0]


def test_出力に期限付きのセール表記を含めない():
    # 週次生成なので、ポイント倍率の期限は表示時点で切れている可能性がある
    got = rank_bucket([_item(point_rate=5)], "cele#towel", ranking={}, mean=4.2, limit=10)
    assert "note" not in got[0] and "sale_note" not in got[0]


def test_商品名は制御文字を除いて保存する():
    got = rank_bucket([_item(title="タオル\x1b[31m ギフト")], "cele#towel", {}, 4.2, 10)
    assert got[0]["title"] == "タオル[31m ギフト"


def test_弔事バケツに祝い向け商品は入らない():
    items = [_item(code="a", title="出産祝い 紅白まんじゅう"), _item(code="b", title="緑茶 詰合せ")]
    got = rank_bucket(items, "mourn#food", ranking={}, mean=4.2, limit=10)
    assert [p["title"] for p in got] == ["緑茶 詰合せ"]


# --- 全体平均 ---


def test_全体平均はゲート通過品の評価の平均():
    assert global_mean([_item(rating=4.0), _item(rating=5.0)]) == pytest.approx(4.5)


def test_商品が無いときの全体平均は既定値():
    assert global_mean([]) == pytest.approx(4.2)


# --- ビルド全体 ---


def test_全84バケツを検索する():
    client = _FakeClient()
    build(client, ranking={}, generated_at="2026-09-15")
    assert len(client.calls) == len(all_buckets()) == 84


def test_価格帯ごとに検索の価格範囲を変える():
    client = _FakeClient()
    build(client, ranking={}, generated_at="2026-09-15")
    ranges = {(lo, hi) for _kw, lo, hi in client.calls}
    assert (1000, 2999) in ranges
    assert (50000, None) in ranges


def test_生成物は生成日とバケツを持つ():
    out = build(_FakeClient(), ranking={}, generated_at="2026-09-15")
    assert out["generated_at"] == "2026-09-15"
    assert out["buckets"][bucket_key("cele", "sweets", "5000-9999")]


def test_商品が集まらなかったバケツはキーごと省く():
    out = build(_FakeClient(items=[]), ranking={}, generated_at="2026-09-15")
    assert out["buckets"] == {}


def test_一部のバケツが失敗しても残りは生成する():
    client = _FakeClient(fail_on={keyword_for("cele", "sweets")})
    out = build(client, ranking={}, generated_at="2026-09-15")
    assert bucket_key("cele", "sweets", "5000-9999") not in out["buckets"]
    assert out["buckets"][bucket_key("cele", "towel", "5000-9999")]


def test_APIコール上限に達したらビルドを中断する():
    # 握り潰して部分的な JSON をコミットすると、消えた商品の理由が追えなくなる
    with pytest.raises(RakutenBudgetExceeded):
        build(_FakeClient(budget_out=True), ranking={}, generated_at="2026-09-15")


# --- 起動時のチェックと、ランキング取得の失敗 ---


def test_必須の環境変数が無ければ生成せずに終わる(monkeypatch, tmp_path):
    # 未設定のまま走らせると84バケツ全部が403で失敗してから落ちる。原因が分かるよう先に弾く
    from tools.catalog.build import main

    for name in ("RAKUTEN_APP_ID", "RAKUTEN_AFFILIATE_ID", "RAKUTEN_ACCESS_KEY"):
        monkeypatch.setenv("RAKUTEN_APP_ID", "app")
        monkeypatch.setenv("RAKUTEN_AFFILIATE_ID", "aff")
        monkeypatch.setenv("RAKUTEN_ACCESS_KEY", "key")
        monkeypatch.delenv(name)
        out = tmp_path / "items.json"
        assert main(["--out", str(out)]) == 2
        assert not out.exists()


def test_ランキングが取れなくてもビルドは続く():
    # トレンドは加点要素にすぎず（圏外は0点）、週次ビルド全体を落とす理由にはならない
    from tools.catalog.build import ranking_or_empty

    class _Boom:
        def ranking(self, genre_id):
            raise RuntimeError("楽天APIエラー")

    assert ranking_or_empty(_Boom()) == {}


def test_ランキングが取れたらそのまま使う():
    from tools.catalog.build import ranking_or_empty

    class _Ok:
        def ranking(self, genre_id):
            return {"shop:1": 3}

    assert ranking_or_empty(_Ok()) == {"shop:1": 3}
