"""抽出ジョブのキュー（SQS）。capture が enqueue し、worker が消費する（非同期OCR）。

ImageStore と同じ思想: 環境変数 EXTRACTION_QUEUE_URL を読み、未設定なら enabled()=False
（ローカル/テストは同期インライン抽出にフォールバック）。boto3 は遅延 import。
"""

from __future__ import annotations

import json
import os
from typing import Any


class ExtractionQueue:
    def __init__(self, url: str | None = None) -> None:
        self.url = url if url is not None else os.environ.get("EXTRACTION_QUEUE_URL", "")
        self._client: Any = None

    def enabled(self) -> bool:
        return bool(self.url)

    def _sqs(self) -> Any:
        if self._client is None:
            import boto3  # 遅延 import（未設定環境でも import 時に落ちない）

            self._client = boto3.client("sqs")
        return self._client

    def send(self, payload: dict[str, Any]) -> None:
        """抽出ジョブ（job_id / user_id(スコープ) / image_key / content_type）を送る。"""
        self._sqs().send_message(QueueUrl=self.url, MessageBody=json.dumps(payload))
