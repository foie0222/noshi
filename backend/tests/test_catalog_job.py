"""バッチオーケストレーションのテスト。全依存をフェイク注入。"""

from datetime import UTC, datetime

from app.catalog.job import run_job

NOW = datetime(2026, 6, 11, 0, 0, tzinfo=UTC)


def _raw(code, **over):
    base = {
        "item_code": code,
        "title": "今治タオル 内祝い",
        "price": 5400,
        "item_url": "https://item.rakuten.co.jp/x/",
        "affiliate_url": "https://hb.afl.rakuten.co.jp/x",
        "image_url": "https://thumbnail.image.rakuten.co.jp/x.jpg",
        "shop_name": "店",
        "rating": 4.5,
        "review_count": 800,
        "point_rate": 5,
        "point_end": "",
        "availability": 1,
        "gift_flag": 1,
    }
    base.update(over)
    return base


class FakeRakuten:
    def __init__(self):
        self.searches = []

    def search_items(self, keyword, min_price, max_price, page):
        self.searches.append((keyword, min_price, max_price, page))
        return [_raw(f"shop:{page}-{i}") for i in range(5)] if page == 1 else []

    def ranking(self, genre_id):
        return {"shop:1-0": 1}


class FakeCurator:
    def __init__(self, fail=False, empty=False):
        self.fail = fail
        self.empty = empty
        self.calls = 0

    def curate(self, slug, band, candidates, season_note):
        self.calls += 1
        if self.fail:
            raise RuntimeError("throttled")
        if self.empty:
            return []
        return [
            {"item_code": c["item_code"], "llm_score": 90 - i, "reason": "良い品です"}
            for i, c in enumerate(candidates[:10])
        ]


class FakeStore:
    def __init__(self):
        self.replaced = []

    def replace_bucket(self, slug, band, items, job_run_id, now):
        self.replaced.append((slug, band, [i["item_code"] for i in items]))


def test_全バケツを処理して書き込む():
    store, cur = FakeStore(), FakeCurator()
    summary = run_job(FakeRakuten(), cur, store, now=NOW, deadline=None)
    assert len(store.replaced) == 63  # 9カテゴリ×7価格帯
    assert summary["buckets_failed"] == 0
    assert cur.calls == 63


def test_LLM失敗時は線形スコア順とテンプレ文で書き込む():
    store = FakeStore()
    summary = run_job(FakeRakuten(), FakeCurator(fail=True), store, now=NOW, deadline=None)
    assert len(store.replaced) == 63  # 提案は止まらない
    assert summary["llm_fallback"] == 63


def test_LLMが空を返したら線形フォールバック扱いになる():
    store = FakeStore()
    summary = run_job(FakeRakuten(), FakeCurator(empty=True), store, now=NOW, deadline=None)
    assert summary["llm_fallback"] == 63
    # 線形上位が書き込まれている（空バケツにならない）
    assert all(len(codes) > 0 for _, _, codes in store.replaced)


def test_時間バジェット超過後はLLMを呼ばない():
    cur = FakeCurator()
    store = FakeStore()
    # deadline を過去にする → 全バケツが線形のみ
    summary = run_job(FakeRakuten(), cur, store, now=NOW, deadline=NOW)
    assert cur.calls == 0
    assert len(store.replaced) == 63
    # 時間切れはLLM失敗ではないので llm_fallback には数えない
    assert summary["llm_fallback"] == 0


def test_検索が例外のバケツはスキップして続行する():
    class Flaky(FakeRakuten):
        def search_items(self, keyword, min_price, max_price, page):
            if keyword == "香典返し":
                raise RuntimeError("api down")
            return super().search_items(keyword, min_price, max_price, page)

    store = FakeStore()
    summary = run_job(Flaky(), FakeCurator(), store, now=NOW, deadline=None)
    assert summary["buckets_failed"] == 7  # koden の7価格帯のみ失敗
    assert len(store.replaced) == 56


def test_ランキング取得が例外でも全バケツを処理する():
    class NoRanking(FakeRakuten):
        def ranking(self, genre_id):
            raise RuntimeError("ranking api down")

    store = FakeStore()
    summary = run_job(NoRanking(), FakeCurator(), store, now=NOW, deadline=None)
    # ランキング失敗はトレンド寄与0として続行（バケツ失敗にしない）
    assert summary["buckets_failed"] == 0
    assert len(store.replaced) == 63


def test_1バケツ指定で絞り込める():
    store, cur = FakeStore(), FakeCurator()
    run_job(
        FakeRakuten(),
        cur,
        store,
        now=NOW,
        deadline=None,
        categories={"baby": "出産内祝い"},
        bands=[(5000, 9999, "5000-9999")],
    )
    assert len(store.replaced) == 1
    assert store.replaced[0][0] == "baby" and store.replaced[0][1] == "5000-9999"
