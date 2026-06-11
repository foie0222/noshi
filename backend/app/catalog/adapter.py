"""GiftCatalogPort の本番実装（スペック§9）。NoshiCatalogTable から配信する。

- 鮮度マスク: priceFetchedAt から23時間（24h規約−1hマージン）で price/saleNote を落とす
- 補完: 自バケツ3件未満 → 下側→上側の±1帯のみ。0件 → fallback（金額目安）
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from app.catalog.buckets import band_neighbors, band_of, slug_of

_MASK_AFTER = timedelta(hours=23)
_MIN_ITEMS = 3
_MAX_ITEMS = 10


class DynamoCatalogAdapter:
    def __init__(
        self,
        store: Any,
        fallback: Any,
        now: Callable[[], datetime] | None = None,
    ):
        self.store = store
        self.fallback = fallback
        self._now = now or (lambda: datetime.now(UTC))

    def suggest(self, budget: int, relationship: str, purpose: str) -> list[dict[str, Any]]:
        """提案を返す（既存 GiftCatalogPort 互換 + 拡張フィールド）。"""
        now = self._now()
        slug = slug_of(purpose)
        band = band_of(budget)
        rows = self.store.read_bucket(slug, band, now)
        if len(rows) < _MIN_ITEMS:  # 隣接帯補完（下側優先・±1のみ。スペック§9）
            for nb in band_neighbors(band):
                rows.extend(self.store.read_bucket(slug, nb, now))
        rows = rows[:_MAX_ITEMS]
        if not rows:
            return list(self.fallback.suggest(budget, relationship, purpose))
        return [self._to_suggestion(r, i + 1, band, now) for i, r in enumerate(rows)]

    def log_click(self, item_code: str, bucket: str, position: int) -> None:
        """クリック計測（ストアに委譲）。"""
        self.store.put_click(item_code, bucket, position, self._now())

    def _to_suggestion(
        self, row: dict[str, Any], position: int, band: str, now: datetime
    ) -> dict[str, Any]:
        out: dict[str, Any] = {
            "title": row["title"],
            "summary": row["reason"],
            "price_band": _band_label(band),
            "external_ref": row["affiliate_url"],
            "image_url": row["image_url"],
            "shop_name": row["shop_name"],
            "rating": row["rating"],
            "review_count": row["review_count"],
            "item_code": row["item_code"],
            "bucket": row["bucket"],
            "position": position,
        }
        fresh = _is_fresh(row.get("price_fetched_at", ""), now)
        if fresh:
            out["price"] = row["price"]
            out["price_fetched_at"] = row["price_fetched_at"]
            note = row.get("sale_note", "")
            if note and not _sale_expired(row.get("sale_ends_at", ""), now):
                out["sale_note"] = note
        return out


def _is_fresh(fetched_at: str, now: datetime) -> bool:
    """価格鮮度（23h以内）。パース不能は安全側（False=マスク）。"""
    try:
        return now - datetime.fromisoformat(fetched_at) < _MASK_AFTER
    except ValueError:
        return False


def _sale_expired(ends_at: str, now: datetime) -> bool:
    """セール期限切れ判定。不明な期限は安全側（True=落とす）。"""
    if not ends_at:
        return False
    try:
        return datetime.fromisoformat(ends_at) < now
    except ValueError:
        return True


def _band_label(band: str) -> str:
    """価格帯ラベル → 表示用（"5000-9999" → "〜¥9,999"、"50000-" → "¥50,000〜"）。"""
    low, _, high = band.partition("-")
    if not high:
        return f"¥{int(low):,}〜"
    return f"〜¥{int(high):,}"
