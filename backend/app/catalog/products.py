"""CI が生成した静的カタログ（items.json）の読み出し。

実行時はこのモジュールしか触らない。ネットワーク・LLM・DynamoDB を一切使わず、
メモリ上の dict を引くだけ。生成は backend/tools/catalog/build.py（GitHub Actions）。

JSON はリポジトリにコミットされたものだが、差し替えられた場合に外部サイトへ
誘導しないよう、読み込み時にもアフィリエイトURLと画像ドメインを検証する。
価格は保存しない（楽天の24時間ルールを避けるため。相場は編集コンテンツ側の
price_hint が担う）。
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.catalog.buckets import bucket_key
from app.catalog.text import sanitize_name

_DATA = Path(__file__).with_name("data") / "items.json"

# 表示してよい先。CSP の img-src / 外部リンク先と一致させること。
_AFFILIATE_PREFIX = "https://hb.afl.rakuten.co.jp/"
_IMAGE_PREFIX = "https://thumbnail.image.rakuten.co.jp/"


def _clean(raw: Any) -> dict[str, Any] | None:
    """1件を検証して整形。表示に使えないものは None（捨てる）。"""
    if not isinstance(raw, dict):
        return None
    url = str(raw.get("url", ""))
    image = str(raw.get("image", ""))
    # 生成側でも整形済みだが、差し替えられた JSON を想定して読み込み側でも通す
    title = sanitize_name(str(raw.get("title", "")))
    if not title or not url.startswith(_AFFILIATE_PREFIX) or not image.startswith(_IMAGE_PREFIX):
        return None
    return {
        "title": title,
        "shop": sanitize_name(str(raw.get("shop", ""))),
        "url": url,
        "image": image,
        "rating": float(raw.get("rating") or 0.0),
        "reviews": int(raw.get("reviews") or 0),
    }


class ProductCatalog:
    """items.json を1回読んで保持する。存在しない・壊れている場合は空で動く。"""

    def __init__(self, path: Path | None = None) -> None:
        self._generated_at = ""
        self._buckets: dict[str, list[dict[str, Any]]] = {}
        self._load(path or _DATA)

    def _load(self, path: Path) -> None:
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return  # 初回ビルド前・生成失敗時。編集コンテンツだけで提案画面は成立する
        if not isinstance(data, dict):
            return
        self._generated_at = str(data.get("generated_at", ""))
        raw_buckets = data.get("buckets")
        if not isinstance(raw_buckets, dict):
            return
        for key, rows in raw_buckets.items():
            if not isinstance(rows, list):
                continue
            cleaned = [c for c in (_clean(r) for r in rows) if c is not None]
            if cleaned:
                self._buckets[str(key)] = cleaned

    @property
    def generated_at(self) -> str:
        """items.json を生成した日（表示の鮮度注記に使う）。未生成なら空文字。"""
        return self._generated_at

    def for_bucket(self, tone: str, cat: str, band: str) -> list[dict[str, Any]]:
        return list(self._buckets.get(bucket_key(tone, cat, band), []))
