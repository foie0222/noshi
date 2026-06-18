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
# 2026-06-11 確定: 各カテゴリの検索上位30件の最頻ジャンルを採取し、
# Ranking API が応答することを実機確認済み（計画 Task 13）。
RAKUTEN_GENRE_BY_CATEGORY: dict[str, str | None] = {
    "baby": "566732",
    "wedding": "566732",
    "school": "205222",
    "housewarming": "205222",
    "kaiki": "203226",
    "koden": "566732",
    "ochugen": "566732",
    "oseibo": "110411",
    "general": "566732",
}

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
    # budget < 1000 は最初の high=2999 チェックで最下帯に丸まる
    for _, high, label in PRICE_BANDS:
        if high is None or budget <= high:
            return label
    return PRICE_BANDS[-1][2]


def band_neighbors(band: str) -> list[str]:
    """隣接価格帯を下側優先で返す（±1帯のみ。スペック§9の補完規則）。

    band は band_of の返り値か PRICE_BANDS のラベルであること（未知値は ValueError）。
    """
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


# --- 品目カテゴリ（スペック 2026-06-17）。slug は f"{tone}#{cat}"、tone は cele/mourn ---
# tone -> [(cat_slug, 表示名, 楽天検索キーワード), ...]（リスト順がタブ表示順）
ITEM_CATEGORIES: dict[str, list[tuple[str, str, str]]] = {
    "cele": [
        ("sweets", "スイーツ・お菓子", "内祝い 洋菓子 焼き菓子"),
        ("gourmet", "グルメ・食品", "内祝い グルメ 食品"),
        ("drink", "飲料", "内祝い コーヒー ギフト"),
        ("towel", "タオル・寝具", "内祝い タオル ギフト"),
        ("tableware", "食器・キッチン", "内祝い 食器 ギフト"),
        ("sake", "お酒", "内祝い 酒 ギフト"),
        ("catalog", "カタログギフト", "内祝い カタログギフト"),
    ],
    "mourn": [
        ("drink", "飲料", "香典返し お茶 ギフト"),
        ("food", "食品", "香典返し グルメ"),
        ("towel", "タオル・寝具", "香典返し タオル"),
        ("daily", "洗剤・日用品", "香典返し 洗剤"),
        ("catalog", "カタログギフト", "香典返し カタログギフト"),
    ],
}

# 配信・バッチ用の派生テーブル（slug = "tone#cat"）
ITEM_CATEGORY_KEYWORDS: dict[str, str] = {
    f"{tone}#{cat}": kw for tone, rows in ITEM_CATEGORIES.items() for cat, _label, kw in rows
}
ITEM_CATEGORY_LABELS: dict[str, str] = {
    f"{tone}#{cat}": label for tone, rows in ITEM_CATEGORIES.items() for cat, label, _kw in rows
}
# 品目バケツの楽天ランキングAPIジャンルID。当面は総合ランキング（None=トレンド寄与半減）。
# 実機でカテゴリ上位の最頻ジャンルを採取でき次第、個別IDに差し替える。
RAKUTEN_GENRE_BY_ITEM_CATEGORY: dict[str, str | None] = dict.fromkeys(ITEM_CATEGORY_KEYWORDS, None)


def tone_slug(purpose: str) -> str:
    """用途 → 品目バケツのトーン接頭辞（cele=慶事 / mourn=弔事）。"""
    return "mourn" if tone_of(purpose) == "mourning" else "cele"


def item_bucket_slug(tone: str, cat: str) -> str:
    """品目バケツの slug（store/adapter の slug 引数として使う）。"""
    return f"{tone}#{cat}"
