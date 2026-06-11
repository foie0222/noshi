"""NoshiCatalogTable の読み書き（スペック§8）。

- 書き込み: TransactWriteItems で常に RANK#01〜10 の10スロットを Put/Delete（べき等な総入れ替え）
- 読み取り: Query + FilterExpression で期限切れ除外（DynamoDB TTL は遅延削除のため）
- クリック: PK=CLICK#<日付>, PII なし, TTL 13ヶ月
"""

from __future__ import annotations

import json
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Any

from app.catalog.buckets import bucket_pk

_SLOTS = 10
_ITEM_TTL = timedelta(hours=48)
_CLICK_TTL = timedelta(days=396)  # 13ヶ月


class CatalogStore:
    def __init__(
        self,
        table_name: str | None = None,
        endpoint_url: str | None = None,
        client: Any = None,
    ):
        self.table_name = table_name or os.environ.get("NOSHI_CATALOG_TABLE", "noshi-catalog")
        if client is not None:
            self._client = client
        else:
            import boto3  # 遅延 import

            self._client = boto3.client(
                "dynamodb",
                endpoint_url=endpoint_url or os.environ.get("DYNAMODB_ENDPOINT") or None,
            )

    # --- バッチ書き込み ---

    def replace_bucket(
        self,
        slug: str,
        band: str,
        items: list[dict[str, Any]],
        job_run_id: str,
        now: datetime,
    ) -> None:
        """採用アイテム（順位順・最大10）でバケツを総入れ替えする。"""
        pk = bucket_pk(slug, band)
        expires = str(int((now + _ITEM_TTL).timestamp()))
        ops: list[dict[str, Any]] = []
        for i, item in enumerate(items[:_SLOTS], start=1):
            ops.append(
                {
                    "Put": {
                        "TableName": self.table_name,
                        "Item": {
                            "PK": {"S": pk},
                            "SK": {"S": f"RANK#{i:02d}"},
                            "itemCode": {"S": item["item_code"]},
                            "title": {"S": item["title"]},
                            "price": {"N": str(item["price"])},
                            "priceFetchedAt": {"S": now.isoformat()},
                            "imageUrl": {"S": item.get("image_url", "")},
                            "shopName": {"S": item.get("shop_name", "")},
                            "affiliateUrl": {"S": item["affiliate_url"]},
                            "llmReason": {"S": item.get("reason", "")},
                            "saleNote": {"S": item.get("sale", "")},
                            "saleEndsAt": {"S": item.get("point_end", "")},
                            "rating": {"N": str(item.get("rating", 0))},
                            "reviewCount": {"N": str(item.get("review_count", 0))},
                            "linearScore": {"N": str(round(item.get("linear_score", 0.0), 6))},
                            "llmScore": {"N": str(item.get("llm_score", 0))},
                            "jobRunId": {"S": job_run_id},
                            "expiresAt": {"N": expires},
                        },
                    }
                }
            )
        for i in range(len(items[:_SLOTS]) + 1, _SLOTS + 1):
            ops.append(
                {
                    "Delete": {
                        "TableName": self.table_name,
                        "Key": {"PK": {"S": pk}, "SK": {"S": f"RANK#{i:02d}"}},
                    }
                }
            )
        self._client.transact_write_items(TransactItems=ops)

    def acquire_job_lock(self, now: datetime, ttl_minutes: int = 60) -> bool:
        """ジョブの二重実行ガード（条件付き書き込み）。

        reserved concurrency が使えない環境でも、ロックが生きている間は
        2本目のジョブを開始させない。取得できなければ False。
        """
        from datetime import timedelta as _td

        try:
            self._client.put_item(
                TableName=self.table_name,
                Item={
                    "PK": {"S": "JOBLOCK"},
                    "SK": {"S": "JOBLOCK"},
                    "expiresAt": {"N": str(int((now + _td(minutes=ttl_minutes)).timestamp()))},
                },
                ConditionExpression="attribute_not_exists(PK) OR expiresAt < :now",
                ExpressionAttributeValues={":now": {"N": str(int(now.timestamp()))}},
            )
            return True
        except self._client.exceptions.ConditionalCheckFailedException:
            return False

    # --- 配信読み取り ---

    def read_bucket(self, slug: str, band: str, now: datetime) -> list[dict[str, Any]]:
        """バケツの中身を順位順で返す。期限切れ（expiresAt <= now）は除外する。"""
        r = self._client.query(
            TableName=self.table_name,
            KeyConditionExpression="PK = :pk AND begins_with(SK, :rank)",
            FilterExpression="expiresAt > :now",
            Limit=_SLOTS,  # SK は最大10件設計だが防御として（スペック§9）
            ExpressionAttributeValues={
                ":pk": {"S": bucket_pk(slug, band)},
                ":rank": {"S": "RANK#"},
                ":now": {"N": str(int(now.timestamp()))},
            },
        )
        return [self._from_ddb(item) for item in r.get("Items", [])]

    # --- クリック計測 ---

    def put_click(self, item_code: str, bucket: str, position: int, now: datetime) -> None:
        """クリックを記録（PIIなし・user_id は持たない）。"""
        self._client.put_item(
            TableName=self.table_name,
            Item={
                "PK": {"S": f"CLICK#{now.date().isoformat()}"},
                "SK": {"S": f"{now.isoformat()}#{uuid.uuid4().hex[:8]}"},
                "itemCode": {"S": item_code},
                "bucket": {"S": bucket},
                "position": {"N": str(int(position))},
                "expiresAt": {"N": str(int((now + _CLICK_TTL).timestamp()))},
            },
        )
        self._emit_click_metric()

    def _emit_click_metric(self) -> None:
        """SuggestionClicks メトリクスを EMF フォーマットで出力する。

        print するだけで CloudWatch Embedded Metric Format としてメトリクスが記録される。
        """
        print(
            json.dumps(
                {
                    "_aws": {
                        "Timestamp": int(time.time() * 1000),
                        "CloudWatchMetrics": [
                            {
                                "Namespace": "NoshiCatalog",
                                "Dimensions": [[]],
                                "Metrics": [{"Name": "SuggestionClicks"}],
                            }
                        ],
                    },
                    "SuggestionClicks": 1,
                }
            )
        )

    @staticmethod
    def _from_ddb(item: dict[str, Any]) -> dict[str, Any]:
        # linearScore/llmScore/jobRunId はデバッグ用属性のため配信レスポンスに含めない
        def s(k: str) -> str:
            return str(item.get(k, {}).get("S", ""))

        def n(k: str) -> float:
            return float(item.get(k, {}).get("N", "0"))

        return {
            "item_code": s("itemCode"),
            "title": s("title"),
            "price": int(n("price")),
            "price_fetched_at": s("priceFetchedAt"),
            "image_url": s("imageUrl"),
            "shop_name": s("shopName"),
            "affiliate_url": s("affiliateUrl"),
            "reason": s("llmReason"),
            "sale_note": s("saleNote"),
            "sale_ends_at": s("saleEndsAt"),
            "rating": n("rating"),
            "review_count": int(n("reviewCount")),
            "bucket": s("PK"),
            "rank": s("SK"),
        }
