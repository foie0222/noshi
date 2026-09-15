"""お返しガイドの分類軸。用途カテゴリ(9) × 価格帯(7) と、品目カテゴリ（トーン別）。

キーは ASCII スラッグ固定（表示名の変更がキー変更にならないように）。
外部カタログ API に依存しない純粋な分類定義で、ネットワークも料金も発生しない。
"""

from __future__ import annotations

from app.domain.tone import tone_of

# 用途カテゴリ slug -> 表示名（のし・マナー案内の見出しに使う）
CATEGORIES: dict[str, str] = {
    "baby": "出産内祝い",
    "wedding": "結婚内祝い",
    "school": "入学内祝い",
    "housewarming": "新築内祝い",
    "kaiki": "快気内祝い",
    "koden": "香典返し",
    "ochugen": "お中元のお礼",
    "oseibo": "お歳暮のお礼",
    "general": "内祝い",
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


def band_label(band: str) -> str:
    """価格帯ラベル → 表示用（"5000-9999" → "〜¥9,999"、"50000-" → "¥50,000〜"）。"""
    low, _, high = band.partition("-")
    if not high:
        return f"¥{int(low):,}〜"
    return f"〜¥{int(high):,}"


# --- 品目カテゴリ。slug は tone（cele=慶事 / mourn=弔事）ごとに独立 ---
# tone -> [(cat_slug, 表示名), ...]（リスト順がタブ表示順）
ITEM_CATEGORIES: dict[str, list[tuple[str, str]]] = {
    "cele": [
        ("sweets", "スイーツ・お菓子"),
        ("gourmet", "グルメ・食品"),
        ("drink", "飲料"),
        ("towel", "タオル・寝具"),
        ("tableware", "食器・キッチン"),
        ("sake", "お酒"),
        ("catalog", "カタログギフト"),
    ],
    "mourn": [
        ("drink", "飲料"),
        ("food", "食品"),
        ("towel", "タオル・寝具"),
        ("daily", "洗剤・日用品"),
        ("catalog", "カタログギフト"),
    ],
}

# 表示名の逆引き（slug = "tone#cat"）
ITEM_CATEGORY_LABELS: dict[str, str] = {
    f"{tone}#{cat}": label for tone, rows in ITEM_CATEGORIES.items() for cat, label in rows
}


def tone_slug(purpose: str) -> str:
    """用途 → 品目カテゴリのトーン接頭辞（cele=慶事 / mourn=弔事）。"""
    return "mourn" if tone_of(purpose) == "mourning" else "cele"


def item_category_key(tone: str, cat: str) -> str:
    """品目カテゴリの内部キー（ITEM_CATEGORY_LABELS の引き先）。"""
    return f"{tone}#{cat}"


# --- 商品バケツ（品目 × 価格帯）。CI の build と実行時の読み出しで同じ関数を使う ---


def bucket_key(tone: str, cat: str, band: str) -> str:
    """商品バケツの内部キー（"cele#sweets@5000-9999"）。

    build（CI）が書き、実行時（Lambda）が引く。両者でずれないよう1か所に置く。
    """
    return f"{item_category_key(tone, cat)}@{band}"


def all_buckets() -> list[tuple[str, str, str]]:
    """(tone, cat, band) の全組み合わせ。品目12 × 価格帯7 = 84。"""
    return [
        (tone, cat, band)
        for tone, rows in ITEM_CATEGORIES.items()
        for cat, _label in rows
        for _low, _high, band in PRICE_BANDS
    ]


def band_range(band: str) -> tuple[int, int | None]:
    """価格帯ラベル → (下限, 上限(含む))。上限なしは None。

    未知のラベルは KeyError。綴り違いを黙って丸めると、意図と違う価格の商品を
    集めたまま気づけないため。
    """
    for low, high, label in PRICE_BANDS:
        if label == band:
            return (low, high)
    raise KeyError(band)
