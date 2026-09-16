"""足切りゲート・線形スコア・saleNote 生成（スペック§6）。すべて純粋関数。

商品名の整形は app.catalog.text.sanitize_name（実行時の読み込み側と共用）。
"""

from __future__ import annotations

import math
import os
from datetime import datetime
from typing import Any

_AFFILIATE_PREFIX = "https://hb.afl.rakuten.co.jp/"
_MIN_REVIEWS = 20
_MIN_RATING = 4.0

# 弔事バケツは「弔事語を含む」の正の条件で足切りする（#478）。
# 楽天の商品名は「内祝い 出産内祝い 結婚内祝い 香典返し …」と全用途を列挙するのが慣習で、
# 「出産」「結婚」を NG にすると香典返しにも使える汎用ギフトがほぼ全部消えた
# （実測: 洗剤 30件中 29件、タオル 30件中 29件が該当）。検索語に「香典返し」を入れている
# のだから、商品名にも弔事の用途語がある品だけを通せば、汎用ギフトは通り慶事専用品は落ちる。
_MOURNING_WORDS = ("香典返し", "香典", "満中陰志", "志", "法要", "仏事", "御供", "偲び草", "弔事")
# 弔事語があっても混ぜない語。品そのものが慶事用と分かるものだけに絞る。
# 「誕生日」「出産祝い」のような用途の列挙は不問にする。売り手が「香典返し」と明記している品を、
# 他の用途も併記しているという理由で落とすと、タオル 30 件中 20 件が消える（実測）。
_NG_KODEN = ("紅白",)
# 「志」はのし表書きの『志』（弔事）対策。『志望』等の誤爆はあるが安全側に倒す
_NG_CELEBRATION = ("御供", "仏事", "弔事", "香典", "法要", "志")
_NG_COMMON = ("訳あり", "アウトレット", "中古")


def _weight(name: str, default: float) -> float:
    """環境変数による重み調整（NOSHI_CATALOG_W_REVIEW 等）。"""
    try:
        return float(os.environ.get(name, ""))
    except ValueError:
        return default


def passes_gate(item: dict[str, Any], slug: str) -> bool:
    """足切りゲート（スペック§6①）。"""
    if item.get("review_count", 0) < _MIN_REVIEWS:
        return False
    if item.get("rating", 0.0) < _MIN_RATING:
        return False
    if item.get("availability", 0) != 1:
        return False
    if not str(item.get("affiliate_url", "")).startswith(_AFFILIATE_PREFIX):
        return False
    title = item.get("title", "")
    if any(w in title for w in _NG_COMMON):
        return False
    is_mourning = slug == "koden" or slug.startswith("mourn#")
    if is_mourning:
        if not any(w in title for w in _MOURNING_WORDS):
            return False
        return not any(w in title for w in _NG_KODEN)
    return not any(w in title for w in _NG_CELEBRATION)


def bayes_score(rating: float, count: int, global_mean: float, m: int = 20) -> float:
    """ベイズ平均（0-1）。m は信頼の重み（足切り閾値と同値の20）。"""
    r = (count / (count + m)) * rating + (m / (count + m)) * global_mean
    return max(0.0, min(1.0, r / 5.0))


def trend_score(rank: int | None, genre_specific: bool = True) -> float:
    """ランキング順位 → 0-1。圏外は0。総合ランキング使用時は寄与半減（スペック§5）。"""
    if rank is None or rank < 1:
        return 0.0
    base = 1.0 / math.log2(rank + 1)
    return base if genre_specific else base * 0.5


def sale_score(point_rate: int, discount: float) -> float:
    """セールスコア: 倍率10倍 or 30%引きで満点（スペック§6②）。
    point_rate < 2（楽天の通常1倍）はセール扱いせず 0（sale_note と閾値を統一）。
    """
    eff = point_rate if point_rate >= 2 else 0
    return min(1.0, max(eff / 10.0, discount / 0.3))


def linear_score(
    item: dict[str, Any], rank: int | None, global_mean: float, genre_specific: bool
) -> float:
    """score = 0.6×口コミ + 0.3×トレンド + 0.1×セール + ギフト加点。

    値域は最大 1.05（ギフト加点込み）。
    """
    w_review = _weight("NOSHI_CATALOG_W_REVIEW", 0.6)
    w_trend = _weight("NOSHI_CATALOG_W_TREND", 0.3)
    w_sale = _weight("NOSHI_CATALOG_W_SALE", 0.1)
    s = (
        w_review * bayes_score(item.get("rating", 0.0), item.get("review_count", 0), global_mean)
        + w_trend * trend_score(rank, genre_specific)
        + w_sale * sale_score(item.get("point_rate", 1), item.get("discount", 0.0))
    )
    if item.get("gift_flag") == 1:
        s += 0.05
    return s


def sale_note(item: dict[str, Any]) -> str:
    """saleNote の機械生成（スペック§6。LLMには作らせない）。

    %OFF 表記は未対応（楽天 Ichiba Search API は割引率・定価を返さないため。
    discount はスコア計算専用で既定0）。
    """
    rate = item.get("point_rate", 1)
    if rate < 2:
        return ""
    note = f"ポイント{rate}倍"
    end = item.get("point_end") or ""
    if end:
        try:
            dt = datetime.fromisoformat(end)
            note += f" ({dt.month}/{dt.day}まで)"
        except ValueError:
            pass
    return note
