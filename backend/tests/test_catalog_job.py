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
            {
                "item_code": c["item_code"],
                "llm_score": 90 - i,
                "reason": "良い品です",
                "fit": {"family": 90 - i, "friend": 50, "work": 30, "other": 60},
            }
            for i, c in enumerate(candidates[:10])
        ]


class FakeStore:
    def __init__(self):
        self.replaced = []
        self.items_by_bucket: dict = {}
        self.manifests: dict = {}

    def replace_bucket(self, slug, band, items, job_run_id, now):
        self.replaced.append((slug, band, [i["item_code"] for i in items]))
        self.items_by_bucket[(slug, band)] = items

    def write_manifest(self, tone, band, categories, now):
        self.manifests[(tone, band)] = list(categories)


def test_全バケツを処理して書き込む():
    store, cur = FakeStore(), FakeCurator()
    summary = run_job(FakeRakuten(), cur, store, now=NOW, deadline=None)
    assert len(store.replaced) == 147  # 9用途×7価格帯 + 12品目×7価格帯
    assert summary["buckets_failed"] == 0
    assert cur.calls == 147


def test_LLM失敗時は線形スコア順とテンプレ文で書き込む():
    store = FakeStore()
    summary = run_job(FakeRakuten(), FakeCurator(fail=True), store, now=NOW, deadline=None)
    assert len(store.replaced) == 147  # 提案は止まらない
    assert summary["llm_fallback"] == 147


def test_LLMが空を返したら線形フォールバック扱いになる():
    store = FakeStore()
    summary = run_job(FakeRakuten(), FakeCurator(empty=True), store, now=NOW, deadline=None)
    assert summary["llm_fallback"] == 147
    # 線形上位が書き込まれている（空バケツにならない）
    assert all(len(codes) > 0 for _, _, codes in store.replaced)


def test_楽天コール上限はジョブ全体を即終了する():
    """RakutenBudgetExceeded はバケツ単位 except で握らず run_job 全体を打ち切る（空上書き防止）。"""
    import pytest
    from app.catalog.rakuten import RakutenBudgetExceeded

    class BudgetRakuten:
        def __init__(self):
            self.calls = 0

        def ranking(self, genre_id):
            return {}

        def search_items(self, keyword, min_price, max_price, page):
            self.calls += 1
            if self.calls > 3:
                raise RakutenBudgetExceeded("上限")
            return [_raw(f"shop:{page}-{i}") for i in range(5)] if page == 1 else []

    store = FakeStore()
    with pytest.raises(RakutenBudgetExceeded):
        run_job(BudgetRakuten(), FakeCurator(), store, now=NOW, deadline=None)
    # 上限到達後は残りバケツを空で上書きしない（途中で打ち切られる）
    assert len(store.replaced) < 147


def test_時間バジェット超過後はLLMを呼ばない():
    cur = FakeCurator()
    store = FakeStore()
    # deadline を過去にする → 全バケツが線形のみ
    summary = run_job(FakeRakuten(), cur, store, now=NOW, deadline=NOW)
    assert cur.calls == 0
    assert len(store.replaced) == 147
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
    assert len(store.replaced) == 140


def test_ランキング取得が例外でも全バケツを処理する():
    class NoRanking(FakeRakuten):
        def ranking(self, genre_id):
            raise RuntimeError("ranking api down")

    store = FakeStore()
    summary = run_job(NoRanking(), FakeCurator(), store, now=NOW, deadline=None)
    # ランキング失敗はトレンド寄与0として続行（バケツ失敗にしない）
    assert summary["buckets_failed"] == 0
    assert len(store.replaced) == 147


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


def test_LLMのfitがstoreまで透過する():
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
    items = store.items_by_bucket[("baby", "5000-9999")]
    assert all("fit" in i and set(i["fit"]) == {"family", "friend", "work", "other"} for i in items)


def test_線形フォールバック品にはfitが無い():
    store = FakeStore()
    run_job(
        FakeRakuten(),
        FakeCurator(fail=True),
        store,
        now=NOW,
        deadline=None,
        categories={"baby": "出産内祝い"},
        bands=[(5000, 9999, "5000-9999")],
    )
    items = store.items_by_bucket[("baby", "5000-9999")]
    assert all("fit" not in i for i in items)  # 書かない → 読み取り補完で中立（スペック§4）


def test_fit退化はサマリに計上される():
    class DegenerateCurator(FakeCurator):
        def curate(self, slug, band, candidates, season_note):
            self.calls += 1
            return [
                {
                    "item_code": c["item_code"],
                    "llm_score": 80,
                    "reason": "良い品です",
                    "fit": {"family": 70, "friend": 70, "work": 70, "other": 70},
                }
                for c in candidates[:10]
            ]

    store = FakeStore()
    summary = run_job(
        FakeRakuten(),
        DegenerateCurator(),
        store,
        now=NOW,
        deadline=None,
        categories={"baby": "出産内祝い"},
        bands=[(5000, 9999, "5000-9999")],
    )
    assert summary["fit_degenerate"] == 1


def test_差別化されたfitは退化に数えない():
    store = FakeStore()
    summary = run_job(
        FakeRakuten(),
        FakeCurator(),
        store,
        now=NOW,
        deadline=None,
        categories={"baby": "出産内祝い"},
        bands=[(5000, 9999, "5000-9999")],
    )
    assert summary["fit_degenerate"] == 0


def test_job_selectionの振り分け():
    from app.catalog.buckets import CATEGORIES, ITEM_CATEGORY_KEYWORDS
    from app.catalog.job import _job_selection

    assert _job_selection("purpose") == (CATEGORIES, "JOBLOCK#purpose")
    assert _job_selection("item") == (ITEM_CATEGORY_KEYWORDS, "JOBLOCK#item")
    assert _job_selection("all") == (None, "JOBLOCK")


def test_品目セットのみ実行すると84バケツとマニフェスト():
    from app.catalog.buckets import ITEM_CATEGORY_KEYWORDS

    store, cur = FakeStore(), FakeCurator()
    run_job(FakeRakuten(), cur, store, now=NOW, deadline=None, categories=ITEM_CATEGORY_KEYWORDS)
    assert len(store.replaced) == 84  # 12品目×7価格帯
    assert store.manifests  # 品目セットはマニフェストを書く


def test_用途セットのみ実行すると63バケツとマニフェストなし():
    from app.catalog.buckets import CATEGORIES

    store, cur = FakeStore(), FakeCurator()
    run_job(FakeRakuten(), cur, store, now=NOW, deadline=None, categories=CATEGORIES)
    assert len(store.replaced) == 63  # 9用途×7価格帯
    assert store.manifests == {}  # 用途セットはマニフェストを書かない


def test_品目バケツも処理してマニフェストを書く():
    store, cur = FakeStore(), FakeCurator()
    run_job(FakeRakuten(), cur, store, now=NOW, deadline=None)

    # 品目バケツが slug="tone#cat" 形式で書かれている
    item_slugs = {slug for slug, _band, _codes in store.replaced if "#" in slug}
    assert "cele#towel" in item_slugs
    assert "mourn#food" in item_slugs

    # (tone, band) ごとにマニフェストが書かれ、慶事は7品目・弔事は5品目（全件在庫ありのフェイク）
    assert store.manifests[("cele", "5000-9999")] == [
        "sweets",
        "gourmet",
        "drink",
        "towel",
        "tableware",
        "sake",
        "catalog",
    ]
    assert store.manifests[("mourn", "5000-9999")] == [
        "drink",
        "food",
        "towel",
        "daily",
        "catalog",
    ]
