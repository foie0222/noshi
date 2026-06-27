"""抽出ワーカー Lambda（SQS イベントソース）。

capture が S3 に保存して積んだジョブを受け、Claude(Agent SDK 等) で OCR して
DynamoDB のジョブを completed/failed に更新する。OCR は時間がかかり API Gateway の
30s 統合上限を超え得るため、ここ（timeout 余裕あり）で実行する。
冪等キーは jobId（取り違え/期限切れは run_extraction が無視）。
"""

from __future__ import annotations

import json
import logging
from typing import Any

logger = logging.getLogger(__name__)


def _service() -> Any:
    """worker 用の NoshiService を組み立てる（DynamoRepository + 実 OCR + ImageStore）。"""
    from app.adapters import default_ocr
    from app.images import ImageStore
    from app.ports import GiftCatalogMock
    from app.repository import DynamoRepository
    from app.services import NoshiService

    return NoshiService(DynamoRepository(), default_ocr(), GiftCatalogMock(), images=ImageStore())


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    # event["Records"]: SQS メッセージ（body に job_id/user_id/image_key/content_type）。
    # 失敗した record は batchItemFailures で SQS に返す（再試行→DLQ）。例外を握りつぶして
    # 正常 return すると SQS がメッセージを削除し、再試行/DLQ が一切働かなくなる（要 reportBatchItemFailures）。
    records = (event or {}).get("Records", [])
    svc = _service()
    failures: list[dict[str, str]] = []
    for rec in records:
        try:
            msg = json.loads(rec["body"])
            svc.run_extraction(
                msg["user_id"],
                msg["job_id"],
                msg["image_key"],
                msg.get("content_type", "image/jpeg"),
            )
        except Exception:  # noqa: BLE001 - 1件の失敗を他に波及させず、当該のみ再試行対象に
            logger.exception("extraction record failed messageId=%s", rec.get("messageId"))
            mid = rec.get("messageId")
            if mid:
                failures.append({"itemIdentifier": mid})
    return {"batchItemFailures": failures}
