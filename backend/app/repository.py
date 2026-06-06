"""データ層。Repository 抽象 + InMemory 実装（テスト/最小起動）+ DynamoDB 実装（boto3）。

本人スコープ（A01）をデータ層でも強制: get/list/delete は user_id を必須にし、
所有者が一致しない場合は None / 空を返す。DynamoDB 実装では PK に userId を内包。
"""
from __future__ import annotations

from typing import Optional, Protocol

from app.domain.entities import GiftRecord, GiftEvent, ExtractionJob, AuditEntry


class Repository(Protocol):
    def put_record(self, rec: GiftRecord) -> GiftRecord: ...
    def get_record(self, user_id: str, record_id: str) -> Optional[GiftRecord]: ...
    def list_records(self, user_id: str) -> list[GiftRecord]: ...
    def delete_record(self, user_id: str, record_id: str) -> bool: ...
    def put_event(self, ev: GiftEvent) -> GiftEvent: ...
    def get_event(self, user_id: str, event_id: str) -> Optional[GiftEvent]: ...
    def list_events(self, user_id: str) -> list[GiftEvent]: ...
    def list_pending_events(self, user_id: str) -> list[GiftEvent]: ...
    def put_job(self, job: ExtractionJob) -> ExtractionJob: ...
    def get_job(self, user_id: str, job_id: str) -> Optional[ExtractionJob]: ...
    def append_audit(self, entry: AuditEntry) -> None: ...


class InMemoryRepository:
    """プロセス内辞書による実装。外部依存なしでテスト/最小起動に使う。"""

    def __init__(self) -> None:
        self._records: dict[str, GiftRecord] = {}
        self._events: dict[str, GiftEvent] = {}
        self._jobs: dict[str, ExtractionJob] = {}
        self._audit: list[AuditEntry] = []

    # --- records ---
    def put_record(self, rec: GiftRecord) -> GiftRecord:
        self._records[rec.id] = rec
        return rec

    def get_record(self, user_id: str, record_id: str) -> Optional[GiftRecord]:
        rec = self._records.get(record_id)
        return rec if rec and rec.user_id == user_id else None

    def list_records(self, user_id: str) -> list[GiftRecord]:
        return [r for r in self._records.values() if r.user_id == user_id]

    def delete_record(self, user_id: str, record_id: str) -> bool:
        if self.get_record(user_id, record_id) is None:
            return False
        del self._records[record_id]
        return True

    # --- events ---
    def put_event(self, ev: GiftEvent) -> GiftEvent:
        self._events[ev.id] = ev
        return ev

    def get_event(self, user_id: str, event_id: str) -> Optional[GiftEvent]:
        ev = self._events.get(event_id)
        return ev if ev and ev.user_id == user_id else None

    def list_events(self, user_id: str) -> list[GiftEvent]:
        return [e for e in self._events.values() if e.user_id == user_id]

    def list_pending_events(self, user_id: str) -> list[GiftEvent]:
        return [e for e in self.list_events(user_id) if e.status != "done"]

    # --- jobs ---
    def put_job(self, job: ExtractionJob) -> ExtractionJob:
        self._jobs[job.id] = job
        return job

    def get_job(self, user_id: str, job_id: str) -> Optional[ExtractionJob]:
        job = self._jobs.get(job_id)
        return job if job and job.user_id == user_id else None

    # --- audit ---
    def append_audit(self, entry: AuditEntry) -> None:
        self._audit.append(entry)

    @property
    def audit_entries(self) -> list[AuditEntry]:
        return list(self._audit)


class DynamoRepository:
    """DynamoDB 実装（boto3）。PK に userId を内包して本人スコープをキー設計で強制（A01）。

    boto3 は遅延 import（テスト環境に未導入でも InMemory は動く）。テーブル/エンドポイントは
    環境変数で注入（ローカルは DynamoDB Local、本番は AWS）。MVP の骨子実装。
    """

    def __init__(self, table_name: str | None = None, endpoint_url: str | None = None):
        import os
        import boto3  # 遅延 import

        self.table_name = table_name or os.environ.get("NOSHI_TABLE", "noshi")
        self._ddb = boto3.resource(
            "dynamodb",
            endpoint_url=endpoint_url or os.environ.get("DYNAMODB_ENDPOINT"),
        )
        self.table = self._ddb.Table(self.table_name)

    @staticmethod
    def _pk(user_id: str) -> str:
        return f"USER#{user_id}"

    def put_record(self, rec: GiftRecord) -> GiftRecord:
        item = {"PK": self._pk(rec.user_id), "SK": f"RECORD#{rec.id}", "type": "record", **vars(rec)}
        self.table.put_item(Item=item)
        return rec

    def get_record(self, user_id: str, record_id: str) -> Optional[GiftRecord]:
        r = self.table.get_item(Key={"PK": self._pk(user_id), "SK": f"RECORD#{record_id}"}).get("Item")
        return GiftRecord(**{k: v for k, v in r.items() if k in GiftRecord.__annotations__}) if r else None

    def list_records(self, user_id: str) -> list[GiftRecord]:
        from boto3.dynamodb.conditions import Key
        items = self.table.query(
            KeyConditionExpression=Key("PK").eq(self._pk(user_id)) & Key("SK").begins_with("RECORD#")
        ).get("Items", [])
        return [GiftRecord(**{k: v for k, v in it.items() if k in GiftRecord.__annotations__}) for it in items]

    def delete_record(self, user_id: str, record_id: str) -> bool:
        if self.get_record(user_id, record_id) is None:
            return False
        self.table.delete_item(Key={"PK": self._pk(user_id), "SK": f"RECORD#{record_id}"})
        return True

    def put_event(self, ev: GiftEvent) -> GiftEvent:
        self.table.put_item(Item={"PK": self._pk(ev.user_id), "SK": f"EVENT#{ev.id}", "type": "event", **vars(ev)})
        return ev

    def get_event(self, user_id: str, event_id: str) -> Optional[GiftEvent]:
        r = self.table.get_item(Key={"PK": self._pk(user_id), "SK": f"EVENT#{event_id}"}).get("Item")
        return GiftEvent(**{k: v for k, v in r.items() if k in GiftEvent.__annotations__}) if r else None

    def list_events(self, user_id: str) -> list[GiftEvent]:
        from boto3.dynamodb.conditions import Key
        items = self.table.query(
            KeyConditionExpression=Key("PK").eq(self._pk(user_id)) & Key("SK").begins_with("EVENT#")
        ).get("Items", [])
        return [GiftEvent(**{k: v for k, v in it.items() if k in GiftEvent.__annotations__}) for it in items]

    def list_pending_events(self, user_id: str) -> list[GiftEvent]:
        return [e for e in self.list_events(user_id) if e.status != "done"]

    def put_job(self, job: ExtractionJob) -> ExtractionJob:
        self.table.put_item(Item={"PK": self._pk(job.user_id), "SK": f"JOB#{job.id}", "type": "job", **vars(job)})
        return job

    def get_job(self, user_id: str, job_id: str) -> Optional[ExtractionJob]:
        r = self.table.get_item(Key={"PK": self._pk(user_id), "SK": f"JOB#{job_id}"}).get("Item")
        return ExtractionJob(**{k: v for k, v in r.items() if k in ExtractionJob.__annotations__}) if r else None

    def append_audit(self, entry: AuditEntry) -> None:
        self.table.put_item(Item={"PK": self._pk(entry.actor_id), "SK": f"AUDIT#{entry.at}#{entry.id}", "type": "audit", **vars(entry)})
