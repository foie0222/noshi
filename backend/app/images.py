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
_PUT_TTL = 300  # 署名付きアップロードの有効期限（秒）
_GET_TTL = 3600  # 署名付きGETの有効期限（秒）
_MAX_BYTES = 10 * 1024 * 1024  # アップロードの最大サイズ（10MB、サーバ側で強制）


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

    def upload_post(self, key: str, content_type: str) -> dict[str, Any]:
        """サイズ上限つきの署名付き POST（ブラウザ直アップロード）。

        content-length-range 条件で最大サイズをサーバ側で強制する（巨大アップロード
        による濫用・コスト増を防ぐ、#100）。返り値は {"url", "fields"}。
        """
        return dict(
            self._s3().generate_presigned_post(
                Bucket=self.bucket,
                Key=key,
                Fields={"Content-Type": content_type},
                Conditions=[
                    {"Content-Type": content_type},
                    ["content-length-range", 1, _MAX_BYTES],
                ],
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

    def put(self, key: str, data: bytes, content_type: str) -> None:
        """サーバ側からオブジェクトを保存する（撮影画像の非同期OCR用、capture が直接S3へ）。"""
        self._s3().put_object(Bucket=self.bucket, Key=key, Body=data, ContentType=content_type)

    def get(self, key: str) -> bytes:
        """オブジェクトのバイト列を取得する（抽出ワーカーが S3 から画像を読む）。"""
        r = self._s3().get_object(Bucket=self.bucket, Key=key)
        body: bytes = r["Body"].read()
        return body

    def delete(self, key: str) -> None:
        # 差し替え/削除時の後始末。失敗しても致命ではない（後続の TTL/手動掃除で回収）が、
        # IAM 誤設定等で恒久的に失敗し続けるとPII画像が残るため、握りつぶさずログに残す。
        if not self.bucket:
            return
        try:
            self._s3().delete_object(Bucket=self.bucket, Key=key)
        except Exception:  # noqa: BLE001 - ベストエフォート（ログは残す）
            import logging

            logging.getLogger("noshi").warning("image delete failed key=%s", key, exc_info=True)
