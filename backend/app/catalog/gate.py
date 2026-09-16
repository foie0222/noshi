"""お返し品カタログの足切り条件。生成側（CI）と実行時（Lambda）の両方から使う。

生成時（tools/catalog/scoring.py）にここで落とした品は items.json に入らない。それでも
実行時（app/catalog/products.py）にもう一度同じ条件を通すのは、items.json が差し替えられた
場合や、足切りを変えた後に古い JSON が残っている場合に、条件を満たさない品を画面に
出さないため。週次カタログの PR は人の目を通さず自動マージされる（#488）ので、この
読み込み時の再検証が最後の防御になる。定義が2つあると食い違うので、ここに1か所だけ置く。
"""

from __future__ import annotations

MIN_REVIEWS = 20
MIN_RATING = 4.0

# 弔事バケツは「弔事語を含む」の正の条件で足切りする（#478）。
# 楽天の商品名は「内祝い 出産内祝い 結婚内祝い 香典返し …」と全用途を列挙するのが慣習で、
# 「出産」「結婚」を NG にすると香典返しにも使える汎用ギフトがほぼ全部消えた
# （実測: 洗剤 30件中 29件、タオル 30件中 29件が該当）。検索語に「香典返し」を入れている
# のだから、商品名にも弔事の用途語がある品だけを通せば、汎用ギフトは通り慶事専用品は落ちる。
# 単漢字の「志」は入れない。「志摩」「有志」に部分一致して無関係な品が混入する。除外条件（慶事側の
# NG_CELEBRATION）で誤爆しても安全側だが、採用条件では逆なので 2 文字以上の語に限る。
MOURNING_WORDS = (
    "香典返し",
    "香典",
    "満中陰志",
    "粗供養",
    "法要",
    "法事",
    "仏事",
    "御供",
    "偲び草",
    "忌明け",
    "弔事",
)
# 弔事語があっても混ぜない語。品そのものが慶事用と分かるものだけに絞る。
# 「誕生日」「出産祝い」のような用途の列挙は不問にする。売り手が「香典返し」と明記している品を、
# 他の用途も併記しているという理由で落とすと、タオル 30 件中 20 件が消える（実測）。
NG_KODEN = ("紅白",)
# 「志」はのし表書きの『志』（弔事）対策。『志望』等の誤爆はあるが安全側に倒す
NG_CELEBRATION = ("御供", "仏事", "弔事", "香典", "法要", "志")
NG_COMMON = ("訳あり", "アウトレット", "中古")


def is_mourning_slug(slug: str) -> bool:
    """バケツ slug（"koden" / "mourn#food" / "cele#towel" 等）が弔事か。"""
    return slug == "koden" or slug.startswith("mourn#")


def title_allowed(title: str, is_mourning: bool) -> bool:
    """商品名による足切り。用途に合わない品と、共通 NG（訳あり等）を落とす。"""
    if any(w in title for w in NG_COMMON):
        return False
    if is_mourning:
        if not any(w in title for w in MOURNING_WORDS):
            return False
        return not any(w in title for w in NG_KODEN)
    return not any(w in title for w in NG_CELEBRATION)


def quality_ok(rating: float, reviews: int) -> bool:
    """レビュー数と評価による足切り。"""
    return reviews >= MIN_REVIEWS and rating >= MIN_RATING
