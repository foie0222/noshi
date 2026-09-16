"""足切りゲート・スコア合成・saleNote 生成のテスト。スペック§6に対応。"""

import pytest
from app.catalog.text import sanitize_name
from tools.catalog.scoring import (
    bayes_score,
    linear_score,
    passes_gate,
    sale_note,
    sale_score,
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
    assert sale_score(point_rate=100, discount=1.0) == 1.0  # クリップ


def test_非セール品はセールスコアが0():
    # point_rate=1（楽天通常）はセール扱いせず0。sale_note の閾値と一致させる
    assert sale_score(point_rate=1, discount=0.0) == 0.0


def test_セールスコアはpoint_rate2倍からカウント():
    # 2倍が最低セール。0.2 = 2/10
    assert sale_score(point_rate=2, discount=0.0) == pytest.approx(0.2)


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


def test_弔事品目スラッグでは弔事NGワードで弾く():
    from tools.catalog.scoring import passes_gate

    base = {
        "review_count": 100,
        "rating": 4.5,
        "availability": 1,
        "affiliate_url": "https://hb.afl.rakuten.co.jp/x",
    }
    # mourn# 系は koden と同じく祝い向け語を弾く
    assert passes_gate({**base, "title": "出産御祝ギフト"}, "mourn#food") is False
    # 慶事品目では祝い向け語は通り、弔事向け語を弾く
    assert passes_gate({**base, "title": "上質タオルセット"}, "cele#towel") is True
    assert passes_gate({**base, "title": "香典返し 緑茶"}, "cele#towel") is False


# --- 弔事バケツの足切りは「弔事語を含む」の正の条件（#478） ---


def _mourn(title):
    return {
        "review_count": 100,
        "rating": 4.5,
        "availability": 1,
        "affiliate_url": "https://hb.afl.rakuten.co.jp/x",
        "title": title,
    }


def test_弔事バケツは全用途を列挙した商品名でも弔事語があれば通す():
    # 楽天の商品名は「出産内祝い 結婚内祝い 香典返し …」と全用途を並べるのが慣習。
    # 「出産」「結婚」を NG にすると香典返しにも使える汎用ギフトがほぼ全部消える
    title = "内祝い 出産内祝い 結婚内祝い 香典返し 今治タオル ギフトセット"
    assert passes_gate(_mourn(title), "mourn#towel")
    assert passes_gate(_mourn(title), "koden")


def test_弔事バケツは弔事語を含まない商品を落とす():
    # 検索語に「香典返し」を入れているのに商品名に弔事の用途が無い品は、慶事専用の可能性が高い
    assert not passes_gate(_mourn("敬老の日 プレゼント 今治タオル ギフトセット"), "mourn#towel")


def test_弔事語は香典返し以外の表記も通す():
    for word in ("満中陰志", "粗供養", "法要", "法事", "仏事", "御供", "偲び草", "忌明け"):
        assert passes_gate(_mourn(f"{word} 緑茶 詰合せ"), "mourn#drink"), word


def test_単漢字の志は採用条件に使わない():
    # 「志摩」「有志」など無関係な語に部分一致し、弔事と無関係な品が香典返しに混入する。
    # 除外条件（慶事バケツ）で誤爆しても安全側だが、採用条件では逆なので使わない
    for title in ("志摩 海産物 詰合せ", "有志 一同 ギフト", "志賀高原 りんごジュース"):
        assert not passes_gate(_mourn(title), "mourn#food"), title


def test_弔事バケツは品そのものが慶事用の語を落とす():
    # 弔事語があっても、紅白（紅白まんじゅう・紅白饅頭）は香典返しに混ぜない
    assert not passes_gate(_mourn("香典返し 紅白まんじゅう"), "mourn#food")


def test_弔事バケツは用途の列挙を理由に落とさない():
    # 売り手が「香典返し」と明記していれば、誕生日・出産祝いを併記していても香典返しとして売っている品。
    # 用途の列挙で落とすとタオル 30 件中 20 件が消える（実測）
    title = "出産祝い 結婚祝い 誕生日 クリスマス 香典返し 今治タオル ギフトセット"
    assert passes_gate(_mourn(title), "mourn#towel")


def test_慶事バケツの足切りは変えない():
    cele = {**_mourn("上質タオルセット"), "title": "上質タオルセット"}
    assert passes_gate(cele, "cele#towel")
    assert not passes_gate({**cele, "title": "香典返し 緑茶"}, "cele#towel")
