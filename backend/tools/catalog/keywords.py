"""バケツ（トーン×品目）→ 楽天検索キーワード。CI のビルド専用。

用途語（「内祝い」「香典返し」）を必ず含めることで、検索の時点で贈答用の
売り場に寄せる。ここで外しきれない混入は scoring.passes_gate の NG ワードで落とす。
"""

from __future__ import annotations

# (tone, cat) -> 検索キーワード
_KEYWORDS: dict[tuple[str, str], str] = {
    ("cele", "sweets"): "内祝い 焼き菓子 詰め合わせ",
    ("cele", "gourmet"): "内祝い グルメ ギフト 詰め合わせ",
    ("cele", "drink"): "内祝い ジュース ギフト 詰め合わせ",
    ("cele", "towel"): "内祝い タオル ギフト",
    ("cele", "tableware"): "内祝い 食器 ギフト",
    ("cele", "sake"): "内祝い 日本酒 ギフト",
    ("cele", "catalog"): "内祝い カタログギフト",
    ("mourn", "drink"): "香典返し 緑茶 ギフト",
    ("mourn", "food"): "香典返し 食品 詰め合わせ",
    ("mourn", "towel"): "香典返し タオル ギフト",
    ("mourn", "daily"): "香典返し 洗剤 ギフト",
    ("mourn", "catalog"): "香典返し カタログギフト",
}


def keyword_for(tone: str, cat: str) -> str:
    """検索キーワード。未定義の組み合わせは KeyError（バケツ定義とのずれを黙認しない）。"""
    return _KEYWORDS[(tone, cat)]
