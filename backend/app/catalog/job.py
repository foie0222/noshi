"""日次バッチ（スペック§7）。収集→足切り→線形スコア→LLM→書き込みをバケツ単位で実行。

- バケツ単位で独立（1バケツの失敗を波及させない）
- 時間バジェット: deadline 超過後は LLM を呼ばず線形のみで確定
- メトリクスは EMF（CloudWatch Embedded Metric Format）を print で出す（追加権限不要）
"""

from __future__ import annotations

import json
import logging
import time
import uuid
from datetime import UTC, datetime, timedelta, timezone
from typing import Any

from app.catalog import scoring
from app.catalog.buckets import (
    CATEGORIES,
    ITEM_CATEGORY_KEYWORDS,
    PRICE_BANDS,
    RAKUTEN_GENRE_BY_CATEGORY,
    RAKUTEN_GENRE_BY_ITEM_CATEGORY,
)
from app.catalog.curation import template_reason
from app.catalog.rakuten import RakutenBudgetExceeded

logger = logging.getLogger(__name__)

_LLM_TIME_RESERVE = timedelta(minutes=3)  # 残り3分でLLM打ち切り（スペック§7）


def _job_selection(sel: str) -> tuple[dict[str, str] | None, str]:
    """EventBridge の set 値 → (run_job に渡す categories, ロックID)。

    'purpose'=用途バケツのみ / 'item'=品目バケツのみ / その他=両方（手動全実行）。
    用途と品目を別ジョブにし、別ロックで相互ブロックを避ける（15分制約のマージン確保）。
    'all' は基底ロック JOBLOCK を使う（分割ロックとは別）。スケジュールは purpose/item の
    2ジョブのみで、手動全実行('all')をスケジュールジョブと同時に走らせる運用はしない。
    """
    if sel == "purpose":
        return CATEGORIES, "JOBLOCK#purpose"
    if sel == "item":
        return ITEM_CATEGORY_KEYWORDS, "JOBLOCK#item"
    return None, "JOBLOCK"


def _season_note(now: datetime) -> str:
    """季節文脈（お中元・お歳暮の時期をプロンプトに伝える）。"""
    m = now.astimezone(timezone(timedelta(hours=9))).month
    if m in (6, 7):
        return "今はお中元の時期です。"
    if m in (11, 12):
        return "今はお歳暮の時期です。"
    return ""


def _emf(metrics: dict[str, float]) -> None:
    """CloudWatch EMF。print するだけでメトリクスになる。"""
    print(
        json.dumps(
            {
                "_aws": {
                    "Timestamp": int(time.time() * 1000),
                    "CloudWatchMetrics": [
                        {
                            "Namespace": "NoshiCatalog",
                            "Dimensions": [[]],
                            "Metrics": [{"Name": k} for k in metrics],
                        }
                    ],
                },
                **metrics,
            }
        )
    )


def run_job(
    rakuten: Any,
    curator: Any,
    store: Any,
    now: datetime,
    deadline: datetime | None,
    categories: dict[str, str] | None = None,
    bands: list[tuple[int, int | None, str]] | None = None,
) -> dict[str, int]:
    """全147バケツを処理する（用途63＋品目84）。categories/bands はCLIの1バケツ実行用（既定は全部）。"""
    # 既定（Lambda 全実行）は用途バケツ＋品目バケツの両方。CLI は categories 明示で1バケツに絞る。
    categories = categories or {**CATEGORIES, **ITEM_CATEGORY_KEYWORDS}
    bands = bands or PRICE_BANDS
    genre_by_slug = {**RAKUTEN_GENRE_BY_CATEGORY, **RAKUTEN_GENRE_BY_ITEM_CATEGORY}
    job_run_id = f"{now.strftime('%Y%m%dT%H%M')}-{uuid.uuid4().hex[:6]}"
    season = _season_note(now)
    failed = 0
    llm_fallback = 0
    fit_degenerate = 0
    manifest_acc: dict[tuple[str, str], list[str]] = {}

    # ランキングはスラッグ単位で1回だけ取得（用途9＋品目12=21コール）
    ranks: dict[str, dict[str, int]] = {}
    genre_specific: dict[str, bool] = {}
    for slug in categories:
        genre = genre_by_slug.get(slug)
        genre_specific[slug] = genre is not None
        try:
            ranks[slug] = rakuten.ranking(genre)
        except RakutenBudgetExceeded:
            raise  # コール上限はジョブ全体を即終了（バケツ失敗として握り潰さない）
        except Exception:  # noqa: BLE001
            logger.exception("ranking failed: %s", slug)
            ranks[slug] = {}

    for slug, keyword in categories.items():
        for low, high, band in bands:
            try:
                raw: list[dict[str, Any]] = []
                for page in (1, 2):
                    raw.extend(rakuten.search_items(keyword, low, high, page))
                candidates = _select(raw, slug, ranks[slug], genre_specific[slug])
                use_llm = deadline is None or datetime.now(UTC) < deadline - _LLM_TIME_RESERVE
                top = _curate(curator, slug, band, candidates, season) if use_llm else None
                if not top and candidates:
                    # 線形フォールバック（LLM失敗・空応答 or 時間バジェット超過）
                    if use_llm:
                        llm_fallback += 1
                    top = [
                        {**c, "llm_score": 0, "reason": template_reason(c)} for c in candidates[:10]
                    ]
                if top and all("fit" in i for i in top) and _is_degenerate(top):
                    fit_degenerate += 1
                store.replace_bucket(slug, band, top or [], job_run_id, now)
                if "#" in slug:  # 品目バケツ: (tone, band) ごとに在庫ありの品目を記録
                    tone, _, cat = slug.partition("#")
                    manifest_acc.setdefault((tone, band), [])
                    if top:
                        manifest_acc[(tone, band)].append(cat)
            except RakutenBudgetExceeded:
                raise  # コール上限はジョブ全体を即終了（残りバケツを空上書きしない）
            except Exception:  # noqa: BLE001
                logger.exception("bucket failed: %s %s", slug, band)
                failed += 1

    for (tone, band), cats in manifest_acc.items():
        store.write_manifest(tone, band, cats, now)

    _emf(
        {
            "CatalogJobBucketsFailed": failed,
            "CatalogLlmFallbackCount": llm_fallback,
            "CatalogFitDegenerationCount": fit_degenerate,
        }
    )
    return {
        "buckets_failed": failed,
        "llm_fallback": llm_fallback,
        "fit_degenerate": fit_degenerate,
    }


def _select(
    raw: list[dict[str, Any]],
    slug: str,
    ranks: dict[str, int],
    genre_specific: bool,
) -> list[dict[str, Any]]:
    """足切り→線形スコア→上位30件（候補）。"""
    gated = [i for i in raw if scoring.passes_gate(i, slug)]
    ratings = [i["rating"] for i in gated]
    global_mean = sum(ratings) / len(ratings) if ratings else 4.2
    seen: set[str] = set()
    scored: list[dict[str, Any]] = []
    for item in gated:
        if item["item_code"] in seen:
            continue  # 2頁での重複排除
        seen.add(item["item_code"])
        enriched = dict(item)
        enriched["title"] = scoring.sanitize_name(enriched["title"])
        enriched["linear_score"] = scoring.linear_score(
            enriched, ranks.get(enriched["item_code"]), global_mean, genre_specific
        )
        enriched["sale"] = scoring.sale_note(enriched)
        scored.append(enriched)
    scored.sort(key=lambda x: float(x["linear_score"]), reverse=True)
    return scored[:30]


def _curate(
    curator: Any, slug: str, band: str, candidates: list[dict[str, Any]], season: str
) -> list[dict[str, Any]] | None:
    """LLMキュレーション（1回リトライ）。失敗は None（呼び出し側で線形フォールバック）。"""
    if not candidates:
        return []
    by_code = {c["item_code"]: c for c in candidates}
    for attempt in (1, 2):
        try:
            picked = curator.curate(slug, band, candidates, season_note=season)
            # LLM の選定順に、収集済みの全属性をマージして返す
            return [
                {
                    **by_code[p["item_code"]],
                    "llm_score": p["llm_score"],
                    "reason": p["reason"],
                    "fit": p["fit"],
                }
                for p in picked
                if p["item_code"] in by_code
            ]
        except Exception:  # noqa: BLE001
            logger.exception("curation failed (attempt %d): %s %s", attempt, slug, band)
    return None


def _is_degenerate(items: list[dict[str, Any]]) -> bool:
    """各商品の fit 4値がすべて同値（タイプ間の差別化放棄）のバケツを退化とみなす（スペック§3 退化検知）。"""
    return all(len(set(i["fit"].values())) == 1 for i in items)


def handler(event: dict[str, Any], context: Any) -> dict[str, int]:
    """Lambda エントリポイント（EventBridge から起動）。"""
    import boto3

    from app.catalog.curation import default_curator
    from app.catalog.rakuten import RakutenClient
    from app.catalog.store import CatalogStore

    sel = (event or {}).get("set", "all")
    categories, lock_id = _job_selection(sel)
    now = datetime.now(UTC)
    store = CatalogStore()
    if not store.acquire_job_lock(now, lock_id=lock_id):
        # 二重実行ガード（スペック§7）。先行ジョブのロックが生きている間はスキップ
        logger.warning("job lock is held by another run; skipping")
        return {"buckets_failed": 0, "llm_fallback": 0, "skipped": 1}
    remaining_ms = context.get_remaining_time_in_millis() if context else 15 * 60 * 1000
    deadline = now + timedelta(milliseconds=remaining_ms)
    ssm = boto3.client("ssm")
    rakuten = RakutenClient(
        app_id=_ssm(ssm, "/noshi/rakuten/app-id"),
        affiliate_id=_ssm(ssm, "/noshi/rakuten/affiliate-id"),
        access_key=_ssm(ssm, "/noshi/rakuten/access-key"),
    )
    return run_job(
        rakuten, default_curator(), store, now=now, deadline=deadline, categories=categories
    )


def _ssm(client: Any, name: str) -> str:
    """SSM Parameter Store から認証情報を取得（SecureString 対応）。"""
    r = client.get_parameter(Name=name, WithDecryption=True)
    return str(r["Parameter"]["Value"])
