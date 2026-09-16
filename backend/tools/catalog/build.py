"""items.json のビルド（GitHub Actions 専用。Lambda には載らない）。

  楽天 検索API（無料・約1req/秒）
    → passes_gate（純粋関数）で足切り
    → linear_score（純粋関数）で並べ替え
    → 各バケツ上位10件
  → backend/app/catalog/data/items.json

LLM は使わない。推薦理由は app/catalog/guide.py の編集コンテンツが担い、
ここは「その品目の実売れ筋」を並べるだけ。

保存しないもの:
- 実売価格   楽天の24時間ルールに触れるため。相場は guide.py の price_hint
- セール表記 週次生成では表示時点で期限切れの可能性があるため（スコアには使う）
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections.abc import Iterable, Sequence
from datetime import date
from pathlib import Path
from typing import Any, Protocol

from app.catalog.buckets import all_buckets, band_range, bucket_key
from app.catalog.text import sanitize_name

from tools.catalog.keywords import keyword_for
from tools.catalog.rakuten import RakutenBudgetExceeded, RakutenClient
from tools.catalog.scoring import linear_score, passes_gate

_OUT = Path(__file__).resolve().parents[2] / "app" / "catalog" / "data" / "items.json"
_REQUIRED_ENV = ("RAKUTEN_APP_ID", "RAKUTEN_AFFILIATE_ID", "RAKUTEN_ACCESS_KEY")
_PER_BUCKET = 10
_DEFAULT_MEAN = 4.2  # レビューが1件も取れなかったときのベイズ事前分布


class _Search(Protocol):
    def search_items(
        self, keyword: str, min_price: int, max_price: int | None, page: int
    ) -> list[dict[str, Any]]: ...


class _Ranking(Protocol):
    def ranking(self, genre_id: str | None) -> dict[str, int]: ...


def global_mean(items: Iterable[dict[str, Any]]) -> float:
    """ベイズ平均の事前分布に使う全体平均。商品が無ければ既定値。"""
    ratings = [float(i.get("rating") or 0.0) for i in items]
    return sum(ratings) / len(ratings) if ratings else _DEFAULT_MEAN


def _to_product(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "title": sanitize_name(str(item.get("title", ""))),
        "shop": sanitize_name(str(item.get("shop_name", ""))),
        "url": str(item.get("affiliate_url", "")),
        "image": str(item.get("image_url", "")),
        "rating": float(item.get("rating") or 0.0),
        "reviews": int(item.get("review_count") or 0),
    }


def rank_bucket(
    items: Sequence[dict[str, Any]],
    slug: str,
    ranking: dict[str, int],
    mean: float,
    limit: int = _PER_BUCKET,
) -> list[dict[str, Any]]:
    """足切り → スコア降順 → 上位 limit 件。同点は item_code 順で安定させる。"""
    passed = [i for i in items if passes_gate(i, slug)]
    scored = sorted(
        passed,
        key=lambda i: (
            -linear_score(
                i,
                rank=ranking.get(str(i.get("item_code", ""))),
                global_mean=mean,
                genre_specific=False,  # 総合ランキングのみ使う（トレンド寄与は半減）
            ),
            str(i.get("item_code", "")),
        ),
    )
    return [_to_product(i) for i in scored[:limit]]


def build(client: _Search, ranking: dict[str, int], generated_at: str) -> dict[str, Any]:
    """全84バケツを検索して items.json の中身を組み立てる。

    1バケツの失敗（検索エラー・0件）はそのバケツを空にして続行する。画面は
    編集コンテンツだけでも成立するため、全体を落とすより欠けたまま出す方が良い。
    ただし API コール上限超過だけは中断する（部分的な JSON をコミットすると、
    商品が消えた理由が後から追えなくなるため）。
    """
    fetched: dict[str, list[dict[str, Any]]] = {}
    for tone, cat, band in all_buckets():
        low, high = band_range(band)
        keyword = keyword_for(tone, cat)
        try:
            fetched[bucket_key(tone, cat, band)] = client.search_items(keyword, low, high, 1)
        except RakutenBudgetExceeded:
            raise
        except Exception as e:  # noqa: BLE001 - 1バケツの失敗で全体を落とさない
            print(f"warn: {bucket_key(tone, cat, band)} の取得に失敗しました: {e}", file=sys.stderr)
            fetched[bucket_key(tone, cat, band)] = []

    mean = global_mean([i for rows in fetched.values() for i in rows])
    buckets: dict[str, list[dict[str, Any]]] = {}
    for tone, cat, band in all_buckets():
        key = bucket_key(tone, cat, band)
        ranked = rank_bucket(fetched[key], f"{tone}#{cat}", ranking, mean)
        if ranked:  # 0件のバケツはキーごと省く（読み出し側は欠損を空として扱う）
            buckets[key] = ranked
    return {"generated_at": generated_at, "buckets": buckets}


def ranking_or_empty(client: _Ranking) -> dict[str, int]:
    """総合ランキング（1回だけ）。取れなければ空で続ける。

    トレンドはスコアの加点要素にすぎず、圏外は 0 点として扱われる。ランキングAPIの
    一時的な不調で週次ビルド全体を落とす理由にはならない。
    """
    try:
        return client.ranking(None)
    except Exception as e:  # noqa: BLE001 - 加点が無いだけでビルドは成立する
        print(
            f"warn: ランキングを取得できませんでした（トレンド加点なしで続行）: {e}",
            file=sys.stderr,
        )
        return {}


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="お返し品カタログ（items.json）を生成する")
    ap.add_argument("--out", type=Path, default=_OUT)
    args = ap.parse_args(argv)

    # 新APIは applicationId と accessKey の両方が必須。1つでも欠けると全バケツが403になる。
    # 84回ぶんの失敗ログを出してから落ちても原因が読み取れないので、ここで先に弾く。
    env = {name: os.environ.get(name, "") for name in _REQUIRED_ENV}
    missing = [name for name, value in env.items() if not value]
    if missing:
        print(f"環境変数が足りません: {', '.join(missing)}", file=sys.stderr)
        return 2

    client = RakutenClient(
        env["RAKUTEN_APP_ID"], env["RAKUTEN_AFFILIATE_ID"], env["RAKUTEN_ACCESS_KEY"]
    )
    out = build(client, ranking_or_empty(client), date.today().isoformat())

    total = sum(len(v) for v in out["buckets"].values())
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        json.dumps(out, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(f"{args.out}: {len(out['buckets'])} バケツ / {total} 商品")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
