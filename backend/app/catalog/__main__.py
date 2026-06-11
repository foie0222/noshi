"""スモークCLI（スペック§11-5）。1バケツだけ実行して動作確認・初回シードに使う。

使い方（backend/ で実行。要 NOSHI_RAKUTEN_APP_ID / NOSHI_RAKUTEN_AFFILIATE_ID / NOSHI_RAKUTEN_ACCESS_KEY）:
  dry-run（書き込みなし・結果表示のみ）:
    python -m app.catalog --bucket baby:5000-9999
  実書き込み（初回シード等。要 NOSHI_CATALOG_TABLE）:
    python -m app.catalog --bucket baby:5000-9999 --write
  全バケツ実書き込み（初回シード）:
    python -m app.catalog --all --write
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from typing import Any

from app.catalog.buckets import CATEGORIES, PRICE_BANDS
from app.catalog.curation import BedrockCurator
from app.catalog.job import run_job
from app.catalog.rakuten import RakutenClient
from app.catalog.store import CatalogStore


class _DryRunStore:
    """書き込みの代わりに内容を表示する。"""

    def replace_bucket(
        self, slug: str, band: str, items: list[dict[str, Any]], job_run_id: str, now: datetime
    ) -> None:
        print(f"== {slug} {band} ({len(items)}件) ==")
        for i, it in enumerate(items, 1):
            print(
                f"  {i:2d}. {it['title'][:40]} ¥{it['price']:,} "
                f"評価{it['rating']}({it['review_count']}) {it.get('sale', '')}"
            )
            print(f"      → {it.get('reason', '')}")


def main() -> int:
    ap = argparse.ArgumentParser(description="カタログバッチのスモーク実行")
    ap.add_argument("--bucket", help="slug:band 形式（例 baby:5000-9999）")
    ap.add_argument("--all", action="store_true", help="全63バケツ")
    ap.add_argument("--write", action="store_true", help="DynamoDB に実書き込み")
    args = ap.parse_args()
    if not args.bucket and not args.all:
        ap.error("--bucket か --all を指定してください")

    rakuten = RakutenClient(
        app_id=os.environ["NOSHI_RAKUTEN_APP_ID"],
        affiliate_id=os.environ["NOSHI_RAKUTEN_AFFILIATE_ID"],
        access_key=os.environ["NOSHI_RAKUTEN_ACCESS_KEY"],
    )
    store: Any = CatalogStore() if args.write else _DryRunStore()

    categories = None
    bands = None
    if args.bucket:  # 1バケツに絞る（run_job の引数で渡す）
        slug, _, band = args.bucket.partition(":")
        if slug not in CATEGORIES:
            print(f"未知のslug: {slug}", file=sys.stderr)
            return 1
        categories = {slug: CATEGORIES[slug]}
        bands = [b for b in PRICE_BANDS if b[2] == band]
        if not bands:
            print(f"未知の価格帯: {band}", file=sys.stderr)
            return 1

    summary = run_job(
        rakuten,
        BedrockCurator(),
        store,
        now=datetime.now(UTC),
        deadline=None,
        categories=categories,
        bands=bands,
    )
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
