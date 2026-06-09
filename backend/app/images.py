"""撮影画像の保存（S3・署名付きURL）（#35）。

ブラウザは API が発行する署名付き PUT URL で S3 に直接アップロードし、
表示は署名付き GET URL で読む。Lambda は URL に署名するだけで画像本体は通さない。
バケットは環境変数 NOSHI_IMAGE_BUCKET で注入。未設定（ローカル）では無効化し、
画像以外の機能は通常どおり動く。
"""

from __future__ import annotations

import os
import uuid
from typing import Any

_EXT = {"image/jpeg": "jpg", "image/png": "png", "image/webp": "webp"}
_PUT_TTL = 300  # 署名付きPUTの有効期限（秒）
_GET_TTL = 3600  # 署名付きGETの有効期限（秒）


class ImageStore:
    def __init__(self, bucket: str | None = None) -> None:
        self.bucket = bucket if bucket is not None else os.environ.get("NOSHI_IMAGE_BUCKET", "")
        self._client = None

    def enabled(self) -> bool:
        return bool(self.bucket)

    def _s3(self) -> Any:
        if self._client is None:
            import boto3  # 遅延 import（未導入環境でも import 時に落ちない）

            self._client = boto3.client("s3")
        return self._client

    def new_key(self, scope: str, content_type: str) -> str:
        """世帯スコープを含む一意なオブジェクトキーを払い出す。"""
        ext = _EXT.get(content_type, "jpg")
        return f"households/{scope}/{uuid.uuid4().hex}.{ext}"

    def upload_url(self, key: str, content_type: str) -> str:
        return str(
            self._s3().generate_presigned_url(
                "put_object",
                Params={"Bucket": self.bucket, "Key": key, "ContentType": content_type},
                ExpiresIn=_PUT_TTL,
            )
        )

    def view_url(self, key: str) -> str:
        return str(
            self._s3().generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=_GET_TTL,
            )
        )

    def delete(self, key: str) -> None:
        # 差し替え/削除時の後始末。失敗しても致命ではない（孤立オブジェクトはライフサイクルで回収可）。
        try:
            self._s3().delete_object(Bucket=self.bucket, Key=key)
        except Exception:  # noqa: BLE001 - ベストエフォート
            pass
