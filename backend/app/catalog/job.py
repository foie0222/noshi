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
from app.catalog.buckets import CATEGORIES, PRICE_BANDS, RAKUTEN_GENRE_BY_CATEGORY
from app.catalog.curation import template_reason

logger = logging.getLogger(__name__)

_LLM_TIME_RESERVE = timedelta(minutes=3)  # 残り3分でLLM打ち切り（スペック§7）


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
    """全63バケツを処理する。categories/bands はCLIの1バケツ実行用（既定は全部）。"""
    categories = categories or CATEGORIES
    bands = bands or PRICE_BANDS
    job_run_id = f"{now.strftime('%Y%m%dT%H%M')}-{uuid.uuid4().hex[:6]}"
    season = _season_note(now)
    failed = 0
    llm_fallback = 0

    # ランキングはカテゴリ単位で1回だけ取得（9コール）
    ranks: dict[str, dict[str, int]] = {}
    genre_specific: dict[str, bool] = {}
    for slug in categories:
        genre = RAKUTEN_GENRE_BY_CATEGORY.get(slug)
        genre_specific[slug] = genre is not None
        try:
            ranks[slug] = rakuten.ranking(genre)
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
                store.replace_bucket(slug, band, top or [], job_run_id, now)
            except Exception:  # noqa: BLE001
                logger.exception("bucket failed: %s %s", slug, band)
                failed += 1

    _emf({"CatalogJobBucketsFailed": failed, "CatalogLlmFallbackCount": llm_fallback})
    return {"buckets_failed": failed, "llm_fallback": llm_fallback}


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
                {**by_code[p["item_code"]], "llm_score": p["llm_score"], "reason": p["reason"]}
                for p in picked
                if p["item_code"] in by_code
            ]
        except Exception:  # noqa: BLE001
            logger.exception("curation failed (attempt %d): %s %s", attempt, slug, band)
    return None


def handler(event: dict[str, Any], context: Any) -> dict[str, int]:
    """Lambda エントリポイント（EventBridge から起動）。"""
    from app.catalog.curation import BedrockCurator
    from app.catalog.rakuten import RakutenClient
    from app.catalog.store import CatalogStore

    now = datetime.now(UTC)
    remaining_ms = context.get_remaining_time_in_millis() if context else 15 * 60 * 1000
    deadline = now + timedelta(milliseconds=remaining_ms)
    rakuten = RakutenClient(
        app_id=_ssm("/noshi/rakuten/app-id"),
        affiliate_id=_ssm("/noshi/rakuten/affiliate-id"),
    )
    return run_job(rakuten, BedrockCurator(), CatalogStore(), now=now, deadline=deadline)


def _ssm(name: str) -> str:
    """SSM Parameter Store から認証情報を取得（SecureString 対応）。"""
    import boto3

    r = boto3.client("ssm").get_parameter(Name=name, WithDecryption=True)
    return str(r["Parameter"]["Value"])
