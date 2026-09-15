"""CI が生成した静的 JSON の読み出し。実行時はネットワークも LLM も使わない。"""

import json

from app.catalog.products import ProductCatalog

_SAMPLE = {
    "generated_at": "2026-09-15",
    "buckets": {
        "cele#sweets@5000-9999": [
            {
                "title": "焼き菓子詰め合わせ",
                "shop": "テスト洋菓子店",
                "url": "https://hb.afl.rakuten.co.jp/hgc/aaa",
                "image": "https://thumbnail.image.rakuten.co.jp/a.jpg",
                "rating": 4.6,
                "reviews": 812,
            }
        ]
    },
}


def _write(tmp_path, data):
    p = tmp_path / "items.json"
    p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
    return p


def test_バケツに対応する商品を返す(tmp_path):
    cat = ProductCatalog(_write(tmp_path, _SAMPLE))
    got = cat.for_bucket("cele", "sweets", "5000-9999")
    assert [p["title"] for p in got] == ["焼き菓子詰め合わせ"]


def test_該当バケツが無ければ空リストを返す(tmp_path):
    cat = ProductCatalog(_write(tmp_path, _SAMPLE))
    assert cat.for_bucket("mourn", "daily", "1000-2999") == []


def test_JSONが無くても空で動く(tmp_path):
    # 初回ビルド前・生成失敗時でも提案画面を落とさない（編集コンテンツだけで成立する）
    cat = ProductCatalog(tmp_path / "missing.json")
    assert cat.for_bucket("cele", "sweets", "5000-9999") == []
    assert cat.generated_at == ""


def test_壊れたJSONでも空で動く(tmp_path):
    p = tmp_path / "items.json"
    p.write_text("{ broken", encoding="utf-8")
    assert ProductCatalog(p).for_bucket("cele", "sweets", "5000-9999") == []


def test_生成日を返す(tmp_path):
    assert ProductCatalog(_write(tmp_path, _SAMPLE)).generated_at == "2026-09-15"


def test_アフィリエイト以外のURLを持つ商品は読み込み時に捨てる(tmp_path):
    # JSON は CI が書くが、差し替えられた場合に外部サイトへ誘導しないための二重防御
    data = {
        "generated_at": "2026-09-15",
        "buckets": {
            "cele#sweets@5000-9999": [
                {**_SAMPLE["buckets"]["cele#sweets@5000-9999"][0], "url": "https://evil.example/x"},
                _SAMPLE["buckets"]["cele#sweets@5000-9999"][0],
            ]
        },
    }
    got = ProductCatalog(_write(tmp_path, data)).for_bucket("cele", "sweets", "5000-9999")
    assert len(got) == 1
    assert got[0]["url"].startswith("https://hb.afl.rakuten.co.jp/")


def test_画像が楽天のサムネイル以外なら読み込み時に捨てる(tmp_path):
    # CSP で許可するドメインと一致させる（許可外は表示できず画像欠けになる）
    item = {**_SAMPLE["buckets"]["cele#sweets@5000-9999"][0], "image": "https://evil.example/a.jpg"}
    data = {"generated_at": "x", "buckets": {"cele#sweets@5000-9999": [item]}}
    got = ProductCatalog(_write(tmp_path, data)).for_bucket("cele", "sweets", "5000-9999")
    assert got == []


def test_価格は保存しないので商品に含まれない(tmp_path):
    # 楽天の24時間ルール回避。相場は編集コンテンツの price_hint が担う
    got = ProductCatalog(_write(tmp_path, _SAMPLE)).for_bucket("cele", "sweets", "5000-9999")
    assert "price" not in got[0]
