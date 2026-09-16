"""足切りゲート・線形スコア・saleNote 生成（スペック§6）。すべて純粋関数。

足切りの条件（レビュー数・評価・NG ワード）は app.catalog.gate、商品名の整形は
app.catalog.text にあり、どちらも実行時の読み込み側（products.py）と共用する。
"""

from __future__ import annotations

import math
import os
from datetime import datetime
from typing import Any

from app.catalog.gate import is_mourning_slug, quality_ok, title_allowed

_AFFILIATE_PREFIX = "https://hb.afl.rakuten.co.jp/"


def _weight(name: str, default: float) -> float:
    """環境変数による重み調整（NOSHI_CATALOG_W_REVIEW 等）。"""
    try:
        return float(os.environ.get(name, ""))
    except ValueError:
        return default


def passes_gate(item: dict[str, Any], slug: str) -> bool:
    """足切りゲート（スペック§6①）。条件の実体は app.catalog.gate（実行時と共用）。"""
    if not quality_ok(float(item.get("rating", 0.0)), int(item.get("review_count", 0))):
        return False
    if item.get("availability", 0) != 1:
        return False
    if not str(item.get("affiliate_url", "")).startswith(_AFFILIATE_PREFIX):
        return False
    return title_allowed(str(item.get("title", "")), is_mourning_slug(slug))


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
