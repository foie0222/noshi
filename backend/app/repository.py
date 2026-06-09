"""データ層。Repository 抽象 + InMemory 実装（テスト/最小起動）+ DynamoDB 実装（boto3）。

本人スコープ（A01）をデータ層でも強制: get/list/delete は user_id を必須にし、
所有者が一致しない場合は None / 空を返す。DynamoDB 実装では PK に userId を内包。
"""

from __future__ import annotations

from typing import Any, Protocol, TypeVar

from app.domain.entities import (
    AuditEntry,
    ExtractionJob,
    GiftEvent,
    GiftRecord,
    Household,
    Membership,
)

T = TypeVar("T")


class Repository(Protocol):
    # 注: record/event/job の第1引数 user_id は「スコープID」。家族共有では世帯ID を渡す。
    def put_record(self, rec: GiftRecord) -> GiftRecord: ...
    def get_record(self, user_id: str, record_id: str) -> GiftRecord | None: ...
    def list_records(self, user_id: str) -> list[GiftRecord]: ...
    def delete_record(self, user_id: str, record_id: str) -> bool: ...
    def put_event(self, ev: GiftEvent) -> GiftEvent: ...
    def get_event(self, user_id: str, event_id: str) -> GiftEvent | None: ...
    def list_events(self, user_id: str) -> list[GiftEvent]: ...
    def list_pending_events(self, user_id: str) -> list[GiftEvent]: ...
    def put_job(self, job: ExtractionJob) -> ExtractionJob: ...
    def get_job(self, user_id: str, job_id: str) -> ExtractionJob | None: ...
    def append_audit(self, entry: AuditEntry) -> None: ...
    # --- 家族共有: 世帯とメンバーシップ ---
    def put_household(self, h: Household) -> Household: ...
    def get_household(self, household_id: str) -> Household | None: ...
    def get_household_by_invite(self, code: str) -> Household | None: ...
    def put_membership(self, m: Membership) -> Membership: ...
    def get_membership(self, user_id: str) -> Membership | None: ...
    def list_members(self, household_id: str) -> list[Membership]: ...
    def delete_membership(self, user_id: str) -> bool: ...
    # --- 世帯独自の続柄マスタ（#1）---
    def add_household_relationship(self, household_id: str, name: str) -> None: ...
    def list_household_relationships(self, household_id: str) -> list[str]: ...
    def remove_household_relationship(self, household_id: str, name: str) -> None: ...


class InMemoryRepository:
    """プロセス内辞書による実装。外部依存なしでテスト/最小起動に使う。"""

    def __init__(self) -> None:
        self._records: dict[str, GiftRecord] = {}
        self._events: dict[str, GiftEvent] = {}
        self._jobs: dict[str, ExtractionJob] = {}
        self._audit: list[AuditEntry] = []
        self._households: dict[str, Household] = {}
        self._memberships: dict[str, Membership] = {}  # user_id -> Membership
        self._relationships: dict[str, list[str]] = {}  # household_id -> 続柄（追加順）

    # --- records ---
    def put_record(self, rec: GiftRecord) -> GiftRecord:
        self._records[rec.id] = rec
        return rec

    def get_record(self, user_id: str, record_id: str) -> GiftRecord | None:
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

    def get_event(self, user_id: str, event_id: str) -> GiftEvent | None:
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

    def get_job(self, user_id: str, job_id: str) -> ExtractionJob | None:
        job = self._jobs.get(job_id)
        return job if job and job.user_id == user_id else None

    # --- audit ---
    def append_audit(self, entry: AuditEntry) -> None:
        self._audit.append(entry)

    @property
    def audit_entries(self) -> list[AuditEntry]:
        return list(self._audit)

    # --- households / memberships ---
    def put_household(self, h: Household) -> Household:
        self._households[h.id] = h
        return h

    def get_household(self, household_id: str) -> Household | None:
        return self._households.get(household_id)

    def get_household_by_invite(self, code: str) -> Household | None:
        return next((h for h in self._households.values() if h.invite_code == code), None)

    def put_membership(self, m: Membership) -> Membership:
        self._memberships[m.user_id] = m
        return m

    def get_membership(self, user_id: str) -> Membership | None:
        return self._memberships.get(user_id)

    def list_members(self, household_id: str) -> list[Membership]:
        return [m for m in self._memberships.values() if m.household_id == household_id]

    def delete_membership(self, user_id: str) -> bool:
        return self._memberships.pop(user_id, None) is not None

    # --- 世帯独自の続柄マスタ ---
    def add_household_relationship(self, household_id: str, name: str) -> None:
        names = self._relationships.setdefault(household_id, [])
        if name not in names:
            names.append(name)

    def list_household_relationships(self, household_id: str) -> list[str]:
        return list(self._relationships.get(household_id, []))

    def remove_household_relationship(self, household_id: str, name: str) -> None:
        names = self._relationships.get(household_id)
        if names and name in names:
            names.remove(name)


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

    def _item(self, pk: str, sk: str, type_: str, obj: Any) -> dict[str, Any]:
        # float は DynamoDB が拒否するため Decimal へ深く変換して保存する。
        return {"PK": pk, "SK": sk, "type": type_, **_to_dynamo(vars(obj))}

    @staticmethod
    def _hydrate(cls: type[T], item: dict[str, Any] | None) -> T | None:
        # Decimal を int/float へ戻し、データクラスのフィールドだけで復元する。
        if not item:
            return None
        clean = _from_dynamo({k: v for k, v in item.items() if k in cls.__annotations__})
        if "amount" in clean and clean["amount"] is not None:
            clean["amount"] = int(clean["amount"])  # 金額は常に int
        return cls(**clean)

    def put_record(self, rec: GiftRecord) -> GiftRecord:
        self.table.put_item(
            Item=self._item(self._pk(rec.user_id), f"RECORD#{rec.id}", "record", rec)
        )
        return rec

    def get_record(self, user_id: str, record_id: str) -> GiftRecord | None:
        r = self.table.get_item(Key={"PK": self._pk(user_id), "SK": f"RECORD#{record_id}"}).get(
            "Item"
        )
        return self._hydrate(GiftRecord, r)

    def list_records(self, user_id: str) -> list[GiftRecord]:
        from boto3.dynamodb.conditions import Key

        items = self.table.query(
            KeyConditionExpression=Key("PK").eq(self._pk(user_id))
            & Key("SK").begins_with("RECORD#")
        ).get("Items", [])
        return [h for it in items if (h := self._hydrate(GiftRecord, it)) is not None]

    def delete_record(self, user_id: str, record_id: str) -> bool:
        if self.get_record(user_id, record_id) is None:
            return False
        self.table.delete_item(Key={"PK": self._pk(user_id), "SK": f"RECORD#{record_id}"})
        return True

    def put_event(self, ev: GiftEvent) -> GiftEvent:
        self.table.put_item(Item=self._item(self._pk(ev.user_id), f"EVENT#{ev.id}", "event", ev))
        return ev

    def get_event(self, user_id: str, event_id: str) -> GiftEvent | None:
        r = self.table.get_item(Key={"PK": self._pk(user_id), "SK": f"EVENT#{event_id}"}).get(
            "Item"
        )
        return self._hydrate(GiftEvent, r)

    def list_events(self, user_id: str) -> list[GiftEvent]:
        from boto3.dynamodb.conditions import Key

        items = self.table.query(
            KeyConditionExpression=Key("PK").eq(self._pk(user_id)) & Key("SK").begins_with("EVENT#")
        ).get("Items", [])
        return [h for it in items if (h := self._hydrate(GiftEvent, it)) is not None]

    def list_pending_events(self, user_id: str) -> list[GiftEvent]:
        return [e for e in self.list_events(user_id) if e.status != "done"]

    def put_job(self, job: ExtractionJob) -> ExtractionJob:
        self.table.put_item(Item=self._item(self._pk(job.user_id), f"JOB#{job.id}", "job", job))
        return job

    def get_job(self, user_id: str, job_id: str) -> ExtractionJob | None:
        r = self.table.get_item(Key={"PK": self._pk(user_id), "SK": f"JOB#{job_id}"}).get("Item")
        return self._hydrate(ExtractionJob, r)

    def append_audit(self, entry: AuditEntry) -> None:
        self.table.put_item(
            Item=self._item(
                self._pk(entry.actor_id), f"AUDIT#{entry.at}#{entry.id}", "audit", entry
            )
        )

    # --- households / memberships ---
    def put_household(self, h: Household) -> Household:
        self.table.put_item(Item=self._item(f"HOUSEHOLD#{h.id}", "META", "household", h))
        # 招待コード→世帯 の逆引きインデックス
        self.table.put_item(
            Item={
                "PK": f"INVITE#{h.invite_code}",
                "SK": "INVITE",
                "type": "invite",
                "household_id": h.id,
            }
        )
        return h

    def get_household(self, household_id: str) -> Household | None:
        r = self.table.get_item(Key={"PK": f"HOUSEHOLD#{household_id}", "SK": "META"}).get("Item")
        return self._hydrate(Household, r)

    def get_household_by_invite(self, code: str) -> Household | None:
        idx = self.table.get_item(Key={"PK": f"INVITE#{code}", "SK": "INVITE"}).get("Item")
        return self.get_household(idx["household_id"]) if idx else None

    def put_membership(self, m: Membership) -> Membership:
        self.table.put_item(Item=self._item(f"USER#{m.user_id}", "MEMBERSHIP", "membership", m))
        # 世帯→メンバー の一覧引きインデックス
        self.table.put_item(
            Item=self._item(f"HOUSEHOLD#{m.household_id}", f"MEMBER#{m.user_id}", "member", m)
        )
        return m

    def get_membership(self, user_id: str) -> Membership | None:
        r = self.table.get_item(Key={"PK": f"USER#{user_id}", "SK": "MEMBERSHIP"}).get("Item")
        return self._hydrate(Membership, r)

    def list_members(self, household_id: str) -> list[Membership]:
        from boto3.dynamodb.conditions import Key

        items = self.table.query(
            KeyConditionExpression=Key("PK").eq(f"HOUSEHOLD#{household_id}")
            & Key("SK").begins_with("MEMBER#")
        ).get("Items", [])
        return [h for it in items if (h := self._hydrate(Membership, it)) is not None]

    def delete_membership(self, user_id: str) -> bool:
        m = self.get_membership(user_id)
        if m is None:
            return False
        self.table.delete_item(Key={"PK": f"USER#{user_id}", "SK": "MEMBERSHIP"})
        self.table.delete_item(Key={"PK": f"HOUSEHOLD#{m.household_id}", "SK": f"MEMBER#{user_id}"})
        return True

    # --- 世帯独自の続柄マスタ ---
    def add_household_relationship(self, household_id: str, name: str) -> None:
        import time

        key = {"PK": f"HOUSEHOLD#{household_id}", "SK": f"REL#{name}"}
        # 既存はそのまま（重複追加で added_at を上書きして順序が崩れるのを防ぐ）。
        if self.table.get_item(Key=key).get("Item"):
            return
        self.table.put_item(
            Item={**key, "type": "relationship", "name": name, "added_at": _to_dynamo(time.time())}
        )

    def list_household_relationships(self, household_id: str) -> list[str]:
        from boto3.dynamodb.conditions import Key

        items = self.table.query(
            KeyConditionExpression=Key("PK").eq(f"HOUSEHOLD#{household_id}")
            & Key("SK").begins_with("REL#")
        ).get("Items", [])
        # 追加順（added_at 昇順）で返す。古いデータに added_at が無い場合は末尾。
        items.sort(key=lambda it: float(it.get("added_at", 0)))
        return [str(it["name"]) for it in items]

    def remove_household_relationship(self, household_id: str, name: str) -> None:
        self.table.delete_item(Key={"PK": f"HOUSEHOLD#{household_id}", "SK": f"REL#{name}"})


def _to_dynamo(value: Any) -> Any:
    """書き込み用に float を Decimal へ深く変換する（DynamoDB は float 非対応）。"""
    from decimal import Decimal

    if isinstance(value, float):
        return Decimal(str(value))
    if isinstance(value, dict):
        return {k: _to_dynamo(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_to_dynamo(v) for v in value]
    return value


def _from_dynamo(value: Any) -> Any:
    """読み出し用に Decimal を int（整数なら）/ float へ深く戻す。"""
    from decimal import Decimal

    if isinstance(value, Decimal):
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, dict):
        return {k: _from_dynamo(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_from_dynamo(v) for v in value]
    return value


def create_table(table_name: str = "noshi", endpoint_url: str | None = None) -> Any:
    """単一テーブル（PK/SK 文字列キー）を作成する。ローカル/CI 用ブートストラップ。

    既に存在する場合は既存テーブルを返す（冪等）。本番は CDK(DataStack) が作成する。
    """
    import os

    import boto3
    from botocore.exceptions import ClientError

    ddb = boto3.resource(
        "dynamodb", endpoint_url=endpoint_url or os.environ.get("DYNAMODB_ENDPOINT")
    )
    try:
        table = ddb.create_table(
            TableName=table_name,
            KeySchema=[
                {"AttributeName": "PK", "KeyType": "HASH"},
                {"AttributeName": "SK", "KeyType": "RANGE"},
            ],
            AttributeDefinitions=[
                {"AttributeName": "PK", "AttributeType": "S"},
                {"AttributeName": "SK", "AttributeType": "S"},
            ],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()
        return table
    except ClientError as e:
        if e.response["Error"]["Code"] == "ResourceInUseException":
            return ddb.Table(table_name)  # 既存（冪等）
        raise
