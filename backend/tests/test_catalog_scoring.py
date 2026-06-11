"""足切りゲート・スコア合成・saleNote 生成のテスト。スペック§6に対応。"""

from app.catalog.scoring import (
    bayes_score,
    linear_score,
    passes_gate,
    sale_note,
    sale_score,
    sanitize_name,
    trend_score,
)


def _item(**over):
    base = {
        "item_code": "shop:10001",
        "title": "今治タオル ギフトセット",
        "price": 5400,
        "image_url": "https://thumbnail.image.rakuten.co.jp/x.jpg",
        "shop_name": "テスト店",
        "affiliate_url": "https://hb.afl.rakuten.co.jp/hgc/xxx",
        "rating": 4.5,
        "review_count": 800,
        "point_rate": 1,
        "point_end": "",
        "availability": 1,
        "gift_flag": 1,
    }
    base.update(over)
    return base


# --- 足切り ---


def test_基準を満たす商品はゲートを通る():
    assert passes_gate(_item(), "baby")


def test_レビュー不足や低評価は弾く():
    assert not passes_gate(_item(review_count=19), "baby")
    assert not passes_gate(_item(rating=3.9), "baby")


def test_在庫なしは弾く():
    assert not passes_gate(_item(availability=0), "baby")


def test_アフィリエイトURLが正規ドメイン以外は弾く():
    assert not passes_gate(_item(affiliate_url="https://evil.example.com/x"), "baby")
    assert not passes_gate(_item(affiliate_url="javascript:alert(1)"), "baby")


def test_用途別NGワードで弾く():
    # 香典返しバケツに祝い系商品は混ぜない
    assert not passes_gate(_item(title="出産祝い 紅白まんじゅう"), "koden")
    # 慶事バケツに弔事系商品は混ぜない
    assert not passes_gate(_item(title="香典返し 志 タオル"), "baby")
    # 共通NG
    assert not passes_gate(_item(title="訳あり タオル"), "baby")


def test_商品名サニタイズは制御文字を除去し200字に切る():
    assert sanitize_name("タオル\x00\x1b[31m") == "タオル[31m"
    assert len(sanitize_name("あ" * 300)) == 200


# --- スコア ---


def test_ベイズ平均は件数が多いほど商品評価に寄る():
    # 評価4.8/3件 は全体平均4.2に引っ張られ、評価4.5/800件 より下になる
    few = bayes_score(rating=4.8, count=3, global_mean=4.2)
    many = bayes_score(rating=4.5, count=800, global_mean=4.2)
    assert many > few
    assert 0.0 <= few <= 1.0 and 0.0 <= many <= 1.0


def test_ベイズ平均はレビュー0件でもゼロ除算せず全体平均に一致():
    assert bayes_score(rating=4.5, count=0, global_mean=4.2) == 4.2 / 5.0


def test_トレンドは順位1で最大かつ圏外は0():
    assert trend_score(1) == 1.0
    assert trend_score(2) < 1.0
    assert trend_score(None) == 0.0


def test_総合ランキング使用時はトレンド半減():
    assert trend_score(1, genre_specific=False) == 0.5


def test_セールスコアは10倍or30パーセント引きで満点():
    assert sale_score(point_rate=10, discount=0.0) == 1.0
    assert sale_score(point_rate=1, discount=0.3) == 1.0
    assert sale_score(point_rate=1, discount=0.0) < 0.2
    assert sale_score(point_rate=100, discount=1.0) == 1.0  # クリップ


def test_線形スコアはギフト加点を含む():
    item = _item()
    with_gift = linear_score(item, rank=None, global_mean=4.2, genre_specific=True)
    without = linear_score(_item(gift_flag=0), rank=None, global_mean=4.2, genre_specific=True)
    assert abs((with_gift - without) - 0.05) < 1e-9


# --- saleNote（機械生成。LLMではない。スペック§6） ---


def test_saleNoteはポイント倍率と期限から生成():
    assert (
        sale_note(_item(point_rate=5, point_end="2026-06-15T09:59:00+09:00"))
        == "ポイント5倍 (6/15まで)"
    )
    assert sale_note(_item(point_rate=5, point_end="")) == "ポイント5倍"
    assert sale_note(_item(point_rate=1)) == ""
