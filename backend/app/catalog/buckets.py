"""バケツ定義（スペック§5）。バケツ = 用途カテゴリ(9) × 価格帯(7) = 63個。

キーは ASCII スラッグ固定（表示名の変更がキー変更にならないように）。
"""

from __future__ import annotations

from app.domain.tone import tone_of

# slug -> 楽天検索キーワード
CATEGORIES: dict[str, str] = {
    "baby": "出産内祝い",
    "wedding": "結婚内祝い",
    "school": "入学内祝い",
    "housewarming": "新築内祝い",
    "kaiki": "快気内祝い",
    "koden": "香典返し",
    "ochugen": "お中元",
    "oseibo": "お歳暮",
    "general": "内祝い ギフト",
}

# 既定用途 -> slug（rules.PURPOSE_DEFAULTS に対応。ここに無い用途はトーンで振り分け）
_PURPOSE_TO_SLUG: dict[str, str] = {
    "出産祝い": "baby",
    "結婚祝い": "wedding",
    "入学祝い": "school",
    "新築祝い": "housewarming",
    "快気祝い": "kaiki",
    "香典": "koden",
    "お中元": "ochugen",
    "お歳暮": "oseibo",
}

# slug -> 楽天ランキングAPIのジャンルID。None は総合ランキング（トレンド寄与は半減）。
# 実装後に Genre Search API で確定して埋める（計画 Task 13 参照）。
RAKUTEN_GENRE_BY_CATEGORY: dict[str, str | None] = {slug: None for slug in CATEGORIES}

# (下限, 上限(含む)。None は上端なし, ラベル)
PRICE_BANDS: list[tuple[int, int | None, str]] = [
    (1000, 2999, "1000-2999"),
    (3000, 4999, "3000-4999"),
    (5000, 9999, "5000-9999"),
    (10000, 14999, "10000-14999"),
    (15000, 24999, "15000-24999"),
    (25000, 49999, "25000-49999"),
    (50000, None, "50000-"),
]


def slug_of(purpose: str) -> str:
    """用途 → カテゴリslug。未知（カスタム）用途はトーンで安全側に振り分ける。"""
    known = _PURPOSE_TO_SLUG.get(purpose)
    if known:
        return known
    return "koden" if tone_of(purpose) == "mourning" else "general"


def band_of(budget: int) -> str:
    """お返し予算（半返し換算済み）→ 価格帯ラベル。1000円未満は最下帯に丸める。"""
    for _low, high, label in PRICE_BANDS:
        if high is None or budget <= high:
            return label
    return PRICE_BANDS[-1][2]


def band_neighbors(band: str) -> list[str]:
    """隣接価格帯を下側優先で返す（±1帯のみ。スペック§9の補完規則）。"""
    labels = [label for _, _, label in PRICE_BANDS]
    i = labels.index(band)
    out: list[str] = []
    if i - 1 >= 0:
        out.append(labels[i - 1])
    if i + 1 < len(labels):
        out.append(labels[i + 1])
    return out


def bucket_pk(slug: str, band: str) -> str:
    """バケツの DynamoDB PK を返す。"""
    return f"BUCKET#{slug}#{band}"
