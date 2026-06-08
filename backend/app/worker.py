"""抽出ワーカー Lambda（SQS イベントソース）。

CDK WorkerStack の handler は app.worker.handler を指す。
SQS から抽出ジョブを受け、OcrLlmPort で抽出し DynamoDB を更新する（本番）。
MVP では同期モック抽出のため、本ワーカーは骨子（冪等キー=jobId）。
"""

from __future__ import annotations

from typing import Any


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    # event["Records"]: SQS メッセージ（body に jobId/userId/imageRef）。
    # 本番: OcrLlmPort 実行 → ExtractionCompleted/Failed → DynamoRepository 更新。
    records = (event or {}).get("Records", [])
    return {"processed": len(records)}
