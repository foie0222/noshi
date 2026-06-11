"""GiftCatalogPort の本番実装（スペック§9）。NoshiCatalogTable から配信する。

- 鮮度マスク: priceFetchedAt から23時間（24h規約−1hマージン）で price/saleNote を落とす
- 補完: 自バケツ3件未満 → 下側→上側の±1帯のみ。0件 → fallback（金額目安）
"""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Any

from app.catalog.buckets import band_neighbors, band_of, slug_of
from app.catalog.relationships import group_of

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
        group = group_of(relationship)  # relationship は生の続柄文字列
        rows = _fit_sorted(self.store.read_bucket(slug, band, now), group)
        if len(rows) < _MIN_ITEMS:  # 隣接帯補完（下側優先・±1のみ。スペック§9）
            seen = {r["item_code"] for r in rows}  # 自バケツ優先（先勝ち）で重複排除
            extra: list[dict[str, Any]] = []
            for nb in band_neighbors(band):
                for r in self.store.read_bucket(slug, nb, now):
                    if r["item_code"] not in seen:
                        seen.add(r["item_code"])
                        extra.append(r)
            # 補完分は独立にソートして末尾へ連結（価格帯の適合 > 続柄の適合）
            rows = rows + _fit_sorted(extra, group)
        rows = rows[:_MAX_ITEMS]
        if not rows:
            return list(self.fallback.suggest(budget, relationship, purpose))
        # ラベルは商品自身の帯で表示（補完品にリクエスト帯を付けると誤認を招く）
        return [
            self._to_suggestion(r, i + 1, _band_of_row(r, band), now, group)
            for i, r in enumerate(rows)
        ]

    def log_click(self, item_code: str, bucket: str, position: int, rel_group: str) -> None:
        """クリック計測（ストアに委譲）。rel_group は配信時に返した値の echo。"""
        self.store.put_click(item_code, bucket, position, rel_group, self._now())

    def _to_suggestion(
        self, row: dict[str, Any], position: int, band: str, now: datetime, rel_group: str
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
            "rel_group": rel_group,
        }
        fresh = _is_fresh(row.get("price_fetched_at", ""), now)
        if fresh:
            out["price"] = row["price"]
            out["price_fetched_at"] = row["price_fetched_at"]
            note = row.get("sale_note", "")
            if note and not _sale_expired(row.get("sale_ends_at", ""), now):
                out["sale_note"] = note
        return out


def _fit_sorted(rows: list[dict[str, Any]], group: str) -> list[dict[str, Any]]:
    """fit を10点刻みに量子化して降順、同帯は元の RANK 順（安定ソート。スペック§5）。

    量子化の理由: fit の1〜2点差は LLM のノイズ。明確に適性が違う場合だけ並びを変える。
    """
    return sorted(rows, key=lambda r: -(int(r.get("fit", {}).get(group, 0)) // 10))


def _band_of_row(row: dict[str, Any], fallback: str) -> str:
    """行自身の価格帯を bucket（"BUCKET#<slug>#<band>"）から導出。異常時はリクエスト帯。"""
    parts = str(row.get("bucket", "")).split("#")
    return parts[2] if len(parts) == 3 and parts[2] else fallback


def _is_fresh(fetched_at: str, now: datetime) -> bool:
    """価格鮮度（23h以内）。パース不能・tz情報なしは安全側（False=マスク）。"""
    try:
        return now - datetime.fromisoformat(fetched_at) < _MASK_AFTER
    except (ValueError, TypeError):  # TypeError: naive と aware の比較
        return False


def _sale_expired(ends_at: str, now: datetime) -> bool:
    """セール期限切れ判定。不明な期限・tz情報なしは安全側（True=落とす）。"""
    if not ends_at:
        return False
    try:
        return datetime.fromisoformat(ends_at) < now
    except (ValueError, TypeError):  # TypeError: naive と aware の比較
        return True


def _band_label(band: str) -> str:
    """価格帯ラベル → 表示用（"5000-9999" → "〜¥9,999"、"50000-" → "¥50,000〜"）。"""
    low, _, high = band.partition("-")
    if not high:
        return f"¥{int(low):,}〜"
    return f"〜¥{int(high):,}"
