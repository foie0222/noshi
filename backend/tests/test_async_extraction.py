"""非同期抽出（capture→S3→SQS→worker→ポーリング）のテスト。

S3/SQS は注入したフェイクで代替し、enqueue / run / get と capture エンドポイントの
pending→completed の流れを検証する（ネットワーク不要）。
"""

import base64

from app.main import create_app
from app.ports import GiftCatalogMock
from app.repository import InMemoryRepository
from app.services import NoshiService
from app.worker import handler as worker_handler
from fastapi.testclient import TestClient

TINY = "data:image/jpeg;base64," + base64.b64encode(b"\xff\xd8\xff\x00jpeg").decode()


class FakeImages:
    def __init__(self):
        self.store: dict[str, bytes] = {}

    def enabled(self):
        return True

    def new_key(self, scope, content_type):
        return f"households/{scope}/img.jpg"

    def put(self, key, data, content_type):
        self.store[key] = data

    def get(self, key):
        return self.store[key]


class FakeQueue:
    def __init__(self):
        self.sent: list[dict] = []

    def enabled(self):
        return True

    def send(self, payload):
        self.sent.append(payload)


class FakeOcr:
    def __init__(self, result=None, fail=False, error=None):
        self.result = result or {
            "candidates": {"amount": 30000, "party_name": "佐藤"},
            "confidence": 0.9,
            "field_confidence": {"amount": 0.9},
        }
        # error: 投げる例外（None なら正常）。fail=True は後方互換で RuntimeError(一時障害)。
        self.error = error or (RuntimeError("ocr boom") if fail else None)
        self.seen: list[list[str]] = []

    def extract(self, image_refs):
        self.seen.append(image_refs)
        if self.error is not None:
            raise self.error
        return self.result


def _svc(images, queue, ocr=None):
    return NoshiService(
        InMemoryRepository(), ocr or FakeOcr(), GiftCatalogMock(), images=images, queue=queue
    )


def test_async有効判定はqueueとimages両方必要():
    assert _svc(FakeImages(), FakeQueue()).async_extraction_enabled() is True
    assert (
        NoshiService(InMemoryRepository(), FakeOcr(), GiftCatalogMock()).async_extraction_enabled()
        is False
    )


def test_enqueueはS3保存しpendingジョブを作りSQSに積む():
    images, queue = FakeImages(), FakeQueue()
    svc = _svc(images, queue)
    job = svc.enqueue_extraction("u1", TINY)
    assert job.status == "pending"
    assert images.store  # S3 に保存された
    sent = queue.sent[0]
    assert sent["job_id"] == job.id and sent["content_type"] == "image/jpeg"
    assert sent["image_key"] in images.store


def test_run_extractionはS3画像をOCRしジョブをcompletedにする():
    images, queue, ocr = FakeImages(), FakeQueue(), FakeOcr()
    svc = _svc(images, queue, ocr)
    job = svc.enqueue_extraction("u1", TINY)
    msg = queue.sent[0]
    svc.run_extraction(msg["user_id"], msg["job_id"], msg["image_key"], msg["content_type"])
    done = svc.get_extraction("u1", job.id)
    assert done.status == "completed"
    assert done.candidates["amount"] == 30000
    # OCR には data URL（content_type 付き）が渡る
    assert ocr.seen[0][0].startswith("data:image/jpeg;base64,")


def test_run_extraction恒久エラー_ValueErrorはfailedで確定する():
    images, queue = FakeImages(), FakeQueue()
    svc = _svc(images, queue, FakeOcr(error=ValueError("形式不正")))
    job = svc.enqueue_extraction("u1", TINY)
    msg = queue.sent[0]
    # 恒久エラーは握って failed 確定（リトライ不要）→ 例外は出ない
    svc.run_extraction(msg["user_id"], msg["job_id"], msg["image_key"], msg["content_type"])
    assert svc.get_extraction("u1", job.id).status == "failed"


def test_run_extraction一時障害は例外を送出しジョブを触らない():
    import pytest

    images, queue = FakeImages(), FakeQueue()
    svc = _svc(images, queue, FakeOcr(error=RuntimeError("throttled")))
    job = svc.enqueue_extraction("u1", TINY)
    msg = queue.sent[0]
    # 一時障害は再試行のため送出（worker が SQS に戻す）。ジョブは pending のまま。
    with pytest.raises(RuntimeError):
        svc.run_extraction(msg["user_id"], msg["job_id"], msg["image_key"], msg["content_type"])
    assert svc.get_extraction("u1", job.id).status == "pending"


def test_run_extractionは未知ジョブを冪等に無視する():
    svc = _svc(FakeImages(), FakeQueue())
    svc.run_extraction("u1", "missing", "k")  # 例外にならない


def test_capture非同期エンドポイントはpendingを返しポーリングで完了する():
    images, queue, ocr = FakeImages(), FakeQueue(), FakeOcr()
    svc = _svc(images, queue, ocr)
    c = TestClient(create_app(svc))
    r = c.post("/api/capture", headers={"X-User-Id": "u1"}, json={"image": TINY})
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "pending" and "candidates" not in body
    # worker が処理（注入した svc を使う想定で run_extraction を直接呼ぶ）
    msg = queue.sent[0]
    svc.run_extraction(msg["user_id"], msg["job_id"], msg["image_key"], msg["content_type"])
    # ポーリング
    g = c.get(f"/api/capture/{body['job_id']}", headers={"X-User-Id": "u1"})
    assert g.status_code == 200
    assert g.json()["status"] == "completed"
    assert g.json()["candidates"]["amount"] == 30000


def test_capture同期フォールバック_S3未設定ならインライン抽出():
    # queue/images 未設定（既定モック）→ 即 completed を返す（後方互換）
    c = TestClient(create_app())
    r = c.post("/api/capture", headers={"X-User-Id": "u1"}, json={"image": TINY})
    assert r.status_code == 200
    assert r.json()["status"] == "completed"
    assert "candidates" in r.json()


def test_未知ジョブの取得は404():
    c = TestClient(create_app())
    r = c.get("/api/capture/nope", headers={"X-User-Id": "u1"})
    assert r.status_code == 404


def test_worker_handlerはSQSレコードを処理する():
    # worker._service() を使わず、run_extraction 相当をフェイクで検証する軽量版
    images, queue, ocr = FakeImages(), FakeQueue(), FakeOcr()
    svc = _svc(images, queue, ocr)
    job = svc.enqueue_extraction("u1", TINY)
    import json as _json

    event = {"Records": [{"messageId": "m1", "body": _json.dumps(queue.sent[0])}]}
    # _service をフェイク svc に差し替え
    import app.worker as w

    orig = w._service
    w._service = lambda: svc
    try:
        out = worker_handler(event, None)
    finally:
        w._service = orig
    assert out["batchItemFailures"] == []  # 成功 → 再試行対象なし
    assert svc.get_extraction("u1", job.id).status == "completed"


def test_worker_handlerは一時障害のmessageIdをbatchItemFailuresで返す():
    # run_extraction が一時障害で送出 → worker は当該 messageId を返し SQS に再試行させる
    images, queue = FakeImages(), FakeQueue()
    svc = _svc(images, queue, FakeOcr(error=RuntimeError("throttled")))
    svc.enqueue_extraction("u1", TINY)
    import json as _json

    import app.worker as w

    event = {"Records": [{"messageId": "m9", "body": _json.dumps(queue.sent[0])}]}
    orig = w._service
    w._service = lambda: svc
    try:
        out = worker_handler(event, None)
    finally:
        w._service = orig
    assert out["batchItemFailures"] == [{"itemIdentifier": "m9"}]
