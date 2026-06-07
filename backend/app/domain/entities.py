"""noshi ドメインエンティティ（技術非依存・dataclass）。

各フィールドの機微度分類は functional-design/domain-entities.md に対応:
restricted=認証情報 / confidential=第三者PII・金額 / internal=集計・状態。
"""
from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import Optional


def _id() -> str:
    return uuid.uuid4().hex


def _now() -> float:
    return time.time()


def _invite_code() -> str:
    # 家族に口頭/メッセージで伝えやすい短い英数字コード（紛らわしい文字を除外）。
    import random
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"
    return "".join(random.choice(alphabet) for _ in range(6))


@dataclass
class Household:
    """世帯（家族の共有単位）。記録・お返しは User ではなく Household に属する。"""
    name: str = "わたしの家"
    invite_code: str = field(default_factory=_invite_code)  # 共有参加用コード
    id: str = field(default_factory=_id)
    created_at: float = field(default_factory=_now)


@dataclass
class Membership:
    """ユーザーの世帯への所属（誰がどの世帯の owner/member か）。"""
    user_id: str
    household_id: str
    role: str = "member"  # owner / member
    email: str = ""  # confidential
    joined_at: float = field(default_factory=_now)


@dataclass
class User:
    auth_identifier: str  # restricted
    id: str = field(default_factory=_id)
    created_at: float = field(default_factory=_now)


@dataclass
class Party:
    user_id: str
    name: str  # confidential
    relationship: str = ""  # confidential
    id: str = field(default_factory=_id)


@dataclass
class GiftRecord:
    user_id: str
    party_name: str  # confidential
    amount: int  # confidential
    purpose: str  # confidential
    direction: str = "received"  # received / given
    occurred_at: str = ""  # confidential
    relationship: str = ""
    memo: str = ""
    id: str = field(default_factory=_id)


@dataclass
class GiftEvent:
    user_id: str
    record_id: str
    status: str = "received"  # received / considering / done（自由遷移）
    override_return_amount: Optional[int] = None
    suggestion_id: Optional[str] = None
    letter_id: Optional[str] = None
    id: str = field(default_factory=_id)


@dataclass
class ExtractionJob:
    user_id: str
    status: str = "pending"  # pending / completed / failed
    candidates: dict = field(default_factory=dict)  # confidential（確定前）
    confidence: float = 0.0
    field_confidence: dict = field(default_factory=dict)  # 項目別信頼度（P0-2）
    id: str = field(default_factory=_id)


@dataclass
class ReturnSuggestion:
    event_id: str
    title: str
    summary: str
    external_ref: str
    price_band: str
    id: str = field(default_factory=_id)


@dataclass
class Letter:
    event_id: str
    tone: str
    body_text: str  # confidential
    id: str = field(default_factory=_id)


@dataclass
class AuditEntry:
    actor_id: str
    action: str
    target_ref: str  # 識別子のみ（restricted 平文禁止）
    at: float = field(default_factory=_now)
    id: str = field(default_factory=_id)
