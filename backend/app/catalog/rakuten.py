"""楽天ウェブサービス API クライアント（Ichiba Item Search API 2 / Item Ranking API）。

- レート制御: リクエスト間に1秒（規約の約1req/秒）。呼び出しは単一プロセス直列前提
  （バッチ Lambda は reserved concurrency=1）。
- 失敗はバックオフ2秒で1回リトライ。日次コール上限（max_calls）超過は RuntimeError
  （ジョブ打ち切り。スペック§7/§10）。
- fetch/sleep 注入でテスト可能。本物は urllib（依存追加なし）。
"""

from __future__ import annotations

import json
import time
import urllib.parse
import urllib.request
from collections.abc import Callable
from datetime import datetime, timedelta, timezone
from typing import Any

_SEARCH_URL = "https://app.rakuten.co.jp/services/api/IchibaItem/Search/20220601"
_RANKING_URL = "https://app.rakuten.co.jp/services/api/IchibaItem/Ranking/20220601"
_JST = timezone(timedelta(hours=9))


def _default_fetch(url: str) -> dict[str, Any]:
    with urllib.request.urlopen(url, timeout=15) as r:  # noqa: S310 (https固定)
        loaded = json.loads(r.read().decode("utf-8"))
    return loaded if isinstance(loaded, dict) else {}


def _iso_jst(raw: str) -> str:
    """楽天の 'YYYY-MM-DD HH:MM' (JST) を ISO 8601 に。不明なら空文字。"""
    if not raw:
        return ""
    try:
        return datetime.strptime(raw, "%Y-%m-%d %H:%M").replace(tzinfo=_JST).isoformat()
    except ValueError:
        return ""


class RakutenClient:
    def __init__(
        self,
        app_id: str,
        affiliate_id: str,
        fetch: Callable[[str], dict[str, Any]] | None = None,
        sleep: Callable[[float], None] = time.sleep,
        # 日次上限（スペック§7）。リトライ分も含めた実APIヒット数の上限。
        # 超過は RuntimeError でジョブ打ち切り。
        max_calls: int = 500,
    ):
        self.app_id = app_id
        self.affiliate_id = affiliate_id
        self._fetch = fetch or _default_fetch
        self._sleep = sleep
        self._first = True
        self._calls = 0
        self._max_calls = max_calls

    def _get(self, base: str, params: dict[str, Any]) -> dict[str, Any]:
        if not self._first:
            self._sleep(1.0)  # 規約: 約1req/秒
        self._first = False
        params = {
            "applicationId": self.app_id,
            "affiliateId": self.affiliate_id,
            "format": "json",
            **params,
        }
        url = f"{base}?{urllib.parse.urlencode(params)}"
        for attempt in (1, 2):  # バックオフ付き1回リトライ（スペック§10）
            self._calls += 1
            if self._calls > self._max_calls:
                raise RuntimeError("楽天APIの日次コール上限に達しました（ジョブ打ち切り）")
            try:
                return self._fetch(url)
            except Exception:  # noqa: BLE001
                if attempt == 2:
                    raise
                self._sleep(2.0)
        raise AssertionError("unreachable")

    def search_items(
        self, keyword: str, min_price: int, max_price: int | None, page: int
    ) -> list[dict[str, Any]]:
        params: dict[str, Any] = {
            "keyword": keyword,
            "minPrice": min_price,
            "sort": "-reviewCount",
            "hits": 30,
            "page": page,
        }
        if max_price is not None:
            params["maxPrice"] = max_price
        data = self._get(_SEARCH_URL, params)
        return [self._normalize(w.get("Item", {})) for w in data.get("Items", [])]

    def ranking(self, genre_id: str | None) -> dict[str, int]:
        """ジャンル別（None なら総合）ランキング: itemCode -> 順位。

        rank が取得できない場合は 0（scoring.trend_score は rank<1 を
        圏外=0.0 として扱うため安全）。
        """
        params: dict[str, Any] = {}
        if genre_id:
            params["genreId"] = genre_id
        data = self._get(_RANKING_URL, params)
        out: dict[str, int] = {}
        for w in data.get("Items", []):
            item = w.get("Item", {})
            if item.get("itemCode"):
                out[str(item["itemCode"])] = int(item.get("rank", 0))
        return out

    @staticmethod
    def _normalize(raw: dict[str, Any]) -> dict[str, Any]:
        images = raw.get("mediumImageUrls") or []
        image = images[0].get("imageUrl", "") if images else ""
        return {
            "item_code": str(raw.get("itemCode", "")),
            "title": str(raw.get("itemName", "")),
            "price": int(raw.get("itemPrice") or 0),
            "item_url": str(raw.get("itemUrl", "")),
            "affiliate_url": str(raw.get("affiliateUrl", "")),
            "image_url": str(image),
            "shop_name": str(raw.get("shopName", "")),
            "rating": float(raw.get("reviewAverage") or 0.0),
            "review_count": int(raw.get("reviewCount") or 0),
            "point_rate": int(raw.get("pointRate") or 1),
            "point_end": _iso_jst(str(raw.get("pointRateEndTime", "") or "")),
            "availability": int(raw.get("availability") or 0),
            "gift_flag": int(raw.get("giftFlag") or 0),
        }
