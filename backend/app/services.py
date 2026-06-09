"""サービス層。コンポーネントを業務フローに編成する。

application-design/services.md（CaptureRecordService / LedgerService / ReturnService /
PrivacyService / AccessControlService）を単一の NoshiService に集約（MVP）。
本人スコープ（A01）を全操作で強制し、セキュリティ関連操作を監査（A09）する。
"""

from __future__ import annotations

import datetime
from typing import Any

from app.domain import rules
from app.domain.entities import (
    AuditEntry,
    ExtractionJob,
    GiftEvent,
    GiftRecord,
    Household,
    Membership,
    ReturnSuggestion,
)
from app.ports import GiftCatalogPort, OcrLlmPort
from app.repository import Repository


def _parse_date(value: str | None) -> datetime.date | None:
    """YYYY-MM-DD を date に変換する。空/不正は None（呼び出し側で既定へフォールバック）。"""
    try:
        return datetime.date.fromisoformat((value or "")[:10])
    except ValueError:
        return None


class ValidationError(Exception):
    """入力検証エラー（BR-VAL）。"""

    def __init__(self, errors: list[str]):
        super().__init__("; ".join(errors))
        self.errors = errors


class ForbiddenError(Exception):
    """本人スコープ外アクセス（A01）。"""


class NoshiService:
    def __init__(self, repo: Repository, ocr: OcrLlmPort, catalog: GiftCatalogPort):
        self.repo = repo
        self.ocr = ocr
        self.catalog = catalog

    # --- 監査 ---
    def _audit(self, actor_id: str, action: str, target_ref: str) -> None:
        self.repo.append_audit(AuditEntry(actor_id=actor_id, action=action, target_ref=target_ref))

    # --- 家族共有: 世帯（記録・お返しは「本人」ではなく「世帯」に属する）---
    def resolve_household(self, user_id: str, email: str = "") -> Household:
        """ユーザーの世帯を返す。初回は世帯を自動作成し本人を owner にする（A01）。"""
        m = self.repo.get_membership(user_id)
        if m is not None:
            h = self.repo.get_household(m.household_id)
            if h is not None:
                return h
        h = Household()
        self.repo.put_household(h)
        self.repo.put_membership(
            Membership(user_id=user_id, household_id=h.id, role="owner", email=email)
        )
        self._audit(user_id, "create_household", h.id)  # A09
        return h

    def _scope(self, user_id: str) -> str:
        """データ操作のスコープID（= 世帯ID）。すべての repo 呼び出しに用いる。"""
        return self.resolve_household(user_id).id

    def household_members(self, user_id: str) -> list[dict[str, Any]]:
        """同じ世帯のメンバー一覧（本人・家族）。"""
        hid = self._scope(user_id)
        return [
            {"user_id": m.user_id, "role": m.role, "email": m.email}
            for m in self.repo.list_members(hid)
        ]

    def household_invite_code(self, user_id: str) -> str:
        """世帯への招待コード（家族に伝えて参加してもらう）。"""
        return self.resolve_household(user_id).invite_code

    def household_view(self, user_id: str) -> dict[str, Any]:
        h = self.resolve_household(user_id)
        return {
            "id": h.id,
            "name": h.name,
            "invite_code": h.invite_code,
            "members": self.household_members(user_id),
        }

    def join_household(self, user_id: str, code: str, email: str = "") -> Household:
        """招待コードで世帯に参加する（既存の所属は上書き）。"""
        h = self.repo.get_household_by_invite((code or "").strip().upper())
        if h is None:
            raise ValidationError(["招待コードが正しくありません。"])
        self.repo.put_membership(
            Membership(user_id=user_id, household_id=h.id, role="member", email=email)
        )
        self._audit(user_id, "join_household", h.id)  # A09
        return h

    def leave_household(self, user_id: str) -> Household:
        """現在の世帯から脱退する。台帳は残る家族側に保持され、本人は新しい空の世帯を持つ。"""
        m = self.repo.get_membership(user_id)
        email = ""
        if m is not None:
            email = m.email
            old_hid, was_owner = m.household_id, m.role == "owner"
            self.repo.delete_membership(user_id)
            self._audit(user_id, "leave_household", old_hid)  # A09
            # 管理者が抜けて家族が残るなら、最古参のメンバーに管理者を引き継ぐ
            if was_owner:
                remaining = sorted(self.repo.list_members(old_hid), key=lambda x: x.joined_at)
                if remaining:
                    heir = remaining[0]
                    self.repo.put_membership(
                        Membership(
                            user_id=heir.user_id,
                            household_id=old_hid,
                            role="owner",
                            email=heir.email,
                            joined_at=heir.joined_at,
                        )
                    )
                    self._audit(user_id, "transfer_ownership", heir.user_id)  # A09
        return self.resolve_household(user_id, email=email)  # 常にどこかの世帯に属する

    def remove_member(self, user_id: str, target_user_id: str) -> dict[str, Any]:
        """管理者が世帯から家族メンバーを外す。外された人は次回アクセスで新しい世帯になる。"""
        me = self.repo.get_membership(user_id)
        if me is None or me.role != "owner":
            raise ForbiddenError("only the owner can remove members")
        if target_user_id == user_id:
            raise ValidationError(["ご自身は「脱退」から行ってください。"])
        target = self.repo.get_membership(target_user_id)
        if target is None or target.household_id != me.household_id:
            raise ValidationError(["その方はこの世帯のメンバーではありません。"])
        self.repo.delete_membership(target_user_id)
        self._audit(user_id, "remove_member", target_user_id)  # A09
        return self.household_view(user_id)

    # --- 続柄マスタ（システム既定 ＋ 世帯独自）（#1）---
    def relationship_master(self, user_id: str) -> dict[str, Any]:
        """選択肢に出す続柄一覧。既定（システム固定）＋世帯独自の追加分（重複排除）。"""
        defaults = list(rules.RELATIONSHIP_DEFAULTS)
        customs = [
            r
            for r in self.repo.list_household_relationships(self._scope(user_id))
            if r not in defaults
        ]
        return {"options": defaults + customs, "defaults": defaults}

    def add_relationship(self, user_id: str, name: str) -> dict[str, Any]:
        """世帯独自の続柄を追加する（世帯スコープで家族に共有）。

        空文字・既定と重複・既存の独自と重複は無視（重複排除）。長すぎる入力は拒否。
        世帯あたり RELATIONSHIP_CUSTOM_MAX 件を超える追加は拒否。
        """
        value = (name or "").strip()
        if value and value not in rules.RELATIONSHIP_DEFAULTS:
            if len(value) > 20:
                raise ValidationError(["続柄は20文字以内で入力してください。"])
            scope = self._scope(user_id)
            existing = self.repo.list_household_relationships(scope)
            if value not in existing and len(existing) >= rules.RELATIONSHIP_CUSTOM_MAX:
                raise ValidationError(
                    [
                        f"独自の続柄は{rules.RELATIONSHIP_CUSTOM_MAX}件までです。不要なものを削除してください。"
                    ]
                )
            self.repo.add_household_relationship(scope, value)
            self._audit(user_id, "add_relationship", scope)  # A09
        return self.relationship_master(user_id)

    def remove_relationship(self, user_id: str, name: str) -> dict[str, Any]:
        """世帯独自の続柄をマスタから削除する（既定は対象外）。

        過去レコードの relationship 文字列は触らない（後方互換でそのまま残る）。
        """
        value = (name or "").strip()
        if value and value not in rules.RELATIONSHIP_DEFAULTS:
            scope = self._scope(user_id)
            self.repo.remove_household_relationship(scope, value)
            self._audit(user_id, "remove_relationship", scope)  # A09
        return self.relationship_master(user_id)

    # --- 撮影 → 抽出 ---
    def submit_extraction(self, user_id: str, image_refs: list[str]) -> ExtractionJob:
        out = self.ocr.extract(image_refs)
        job = ExtractionJob(
            user_id=self._scope(user_id),
            status="completed",
            candidates=out["candidates"],
            confidence=out["confidence"],
            field_confidence=out.get("field_confidence", {}),
        )
        return self.repo.put_job(job)

    def extraction_needs_review(self, job: ExtractionJob) -> bool:
        return rules.needs_review(job.confidence)

    def field_review(self, job: ExtractionJob) -> dict[str, Any]:
        """項目別に要確認かどうかを返す（P0-2: 低信頼の項目だけ True）。"""
        return {k: rules.needs_review(v) for k, v in (job.field_confidence or {}).items()}

    # --- 記録 ---
    def create_record(
        self, user_id: str, amount: int, purpose: str, party_name: str, direction: str, **extra: Any
    ) -> tuple[GiftRecord, GiftEvent | None]:
        errors = rules.validate_record(amount, purpose, party_name, direction)
        if errors:
            raise ValidationError(errors)
        scope = self._scope(user_id)
        rec = GiftRecord(
            user_id=scope,
            amount=amount,
            purpose=purpose,
            party_name=party_name,
            direction=direction,
            occurred_at=extra.get("occurred_at", ""),
            relationship=extra.get("relationship", ""),
        )
        self.repo.put_record(rec)
        # received のみお返しイベントを生成（BR-3-GIVEN: given は対象外）
        ev = None
        if direction == "received":
            ev = GiftEvent(user_id=scope, record_id=rec.id, status="received")
            self.repo.put_event(ev)
        return rec, ev

    def list_records(self, user_id: str) -> list[GiftRecord]:
        return self.repo.list_records(self._scope(user_id))

    def relationships(self, user_id: str) -> list[dict[str, Any]]:
        """世帯の おつきあいバランス（差分・最終やりとり・偏り・気になる関係）を返す（N1）。"""
        return rules.relationship_balance(self.repo.list_records(self._scope(user_id)))

    def gift_tax(self, user_id: str, year: int | None = None) -> dict[str, Any]:
        """世帯の暦年「もらった」対象合計と110万円枠サマリを返す（P1-3）。"""
        import datetime

        y = year or datetime.date.today().year
        return rules.gift_tax_summary(self.repo.list_records(self._scope(user_id)), y)

    def annual_summary(self, user_id: str, year: int | None = None) -> dict[str, Any]:
        """世帯の指定年（既定は今年）の年間振り返りを返す。"""
        import datetime

        y = year or datetime.date.today().year
        return rules.annual_summary(self.repo.list_records(self._scope(user_id)), y)

    def party_summary(self, user_id: str) -> dict[str, Any]:
        """相手別の もらった/あげた/差分。"""
        summary: dict[str, dict[str, int]] = {}
        for r in self.repo.list_records(self._scope(user_id)):
            s = summary.setdefault(r.party_name, {"received": 0, "given": 0})
            s[r.direction] = s.get(r.direction, 0) + r.amount
        for s in summary.values():
            s["diff"] = s.get("received", 0) - s.get("given", 0)
        return summary

    def update_record(
        self,
        user_id: str,
        record_id: str,
        *,
        amount: int,
        purpose: str,
        party_name: str,
        **extra: Any,
    ) -> GiftRecord:
        """保存済みレコードを修正する（AI抽出の誤りを本人が訂正）。本人スコープ強制＋監査（A01, A09）。

        direction は変更しない（イベント生成/破棄の整合を避けるため）。
        """
        rec = self.repo.get_record(self._scope(user_id), record_id)
        if rec is None:
            raise ForbiddenError("not your record")
        errors = rules.validate_record(amount, purpose, party_name, rec.direction)
        if errors:
            raise ValidationError(errors)
        rec.amount = amount
        rec.purpose = purpose
        rec.party_name = party_name
        if "occurred_at" in extra:
            rec.occurred_at = extra["occurred_at"]
        if "relationship" in extra:
            rec.relationship = extra["relationship"]
        self.repo.put_record(rec)
        self._audit(user_id, "update_record", record_id)  # A09
        return rec

    def delete_record(self, user_id: str, record_id: str) -> bool:
        scope = self._scope(user_id)
        if self.repo.get_record(scope, record_id) is None:
            raise ForbiddenError("not your record")
        # 紐づくお返しイベントも削除（孤立させない、#36）。
        for ev in self.repo.list_events(scope):
            if ev.record_id == record_id:
                self.repo.delete_event(scope, ev.id)
        ok = self.repo.delete_record(scope, record_id)
        self._audit(user_id, "delete_record", record_id)  # A09
        return ok

    # --- 半返し / お返し ---
    def half_return(self, amount: int, purpose: str) -> rules.ReturnRange:
        return rules.half_return(amount, purpose)

    def suggest_returns(
        self, user_id: str, event_id: str, budget: int, relationship: str, purpose: str
    ) -> list[dict[str, Any]]:
        self._require_event(user_id, self._scope(user_id), event_id)
        return self.catalog.suggest(budget, relationship, purpose)

    def select_suggestion(
        self, user_id: str, event_id: str, suggestion: dict[str, Any]
    ) -> ReturnSuggestion:
        ev = self._require_event(user_id, self._scope(user_id), event_id)
        sug = ReturnSuggestion(
            event_id=event_id,
            title=suggestion["title"],
            summary=suggestion.get("summary", ""),
            external_ref=suggestion.get("external_ref", ""),
            price_band=suggestion.get("price_band", ""),
        )
        ev.suggestion_id = sug.id
        self.repo.put_event(ev)
        return sug

    # --- イベント状態 ---
    def set_event_status(self, user_id: str, event_id: str, status: str) -> GiftEvent:
        # considering=対応中（表示名）。キーは互換のため据え置き（#4）。
        if status not in ("received", "considering", "done"):
            raise ValidationError([f"不正なステータス: {status}"])
        ev = self._require_event(user_id, self._scope(user_id), event_id)
        ev.status = status  # 自由遷移（BR-EVT-1）
        return self.repo.put_event(ev)

    def list_pending_events(self, user_id: str) -> list[GiftEvent]:
        return self.repo.list_pending_events(self._scope(user_id))

    def get_event(self, user_id: str, event_id: str) -> GiftEvent:
        return self._require_event(user_id, self._scope(user_id), event_id)

    # --- 表示用ビュー（UX: ID ではなく相手・用途・金額・期限を見せる） ---
    def _view(self, scope: str, ev: GiftEvent) -> dict[str, Any]:
        rec = self.repo.get_record(scope, ev.record_id)
        purpose = rec.purpose if rec else ""
        occurred_at = rec.occurred_at if rec else ""
        default_due = rules.due_date(occurred_at, purpose)  # BR-3-DUE（用途・受領日からの既定）
        override = _parse_date(ev.override_due)  # 手動上書きがあれば優先
        due = override or default_due
        return {
            "id": ev.id,
            "status": ev.status,
            "record_id": ev.record_id,
            "party_name": rec.party_name if rec else "",
            "purpose": purpose,
            "amount": rec.amount if rec else 0,
            "direction": rec.direction if rec else "received",
            "occurred_at": occurred_at,
            "relationship": rec.relationship if rec else "",
            "due_at": due.isoformat() if due else None,
            "due_default": default_due.isoformat() if default_due else None,
            "due_overridden": override is not None,
            "days_left": rules.days_left(due),
            "suggestion_id": ev.suggestion_id,
        }

    def set_event_due(self, user_id: str, event_id: str, due_at: str | None) -> GiftEvent:
        """お返し期限を手動で上書き/解除する（#2）。

        空文字/None で上書きを解除し、用途・受領日からの自動計算へ戻す。
        値があれば YYYY-MM-DD 形式を要求する（本人スコープ強制）。
        """
        ev = self._require_event(user_id, self._scope(user_id), event_id)
        value = (due_at or "").strip()
        if value and _parse_date(value) is None:
            raise ValidationError([f"期限は YYYY-MM-DD 形式で入力してください: {value}"])
        ev.override_due = value or None
        self.repo.put_event(ev)
        self._audit(user_id, "set_event_due", event_id)  # A09
        return ev

    def pending_views(self, user_id: str) -> list[dict[str, Any]]:
        """未完了お返しを、相手・用途・金額・期限つきで、残日数の近い順に返す。

        お返し不要（期限なし）の用途は除外する（BR-3-DUE-2）。
        """
        scope = self._scope(user_id)
        views = [self._view(scope, e) for e in self.repo.list_pending_events(scope)]
        views = [v for v in views if v["due_at"] is not None]  # 期限なしは除外
        views.sort(key=lambda v: v["days_left"])  # 残日数 昇順（期限が近い順）
        return views

    def event_view(self, user_id: str, event_id: str) -> dict[str, Any]:
        """単一イベントを表示用ビューで返す（世帯スコープ強制）。"""
        scope = self._scope(user_id)
        return self._view(scope, self._require_event(user_id, scope, event_id))

    def event_for_record(self, user_id: str, record_id: str) -> GiftEvent | None:
        """台帳の記録IDから対応するイベントを引く（ledger→お返しフロー、done 含む）。"""
        for e in self.repo.list_events(self._scope(user_id)):
            if e.record_id == record_id:
                return e
        return None

    # --- 内部: 世帯スコープ（user_id は監査用、scope は世帯ID）---
    def _require_event(self, user_id: str, scope: str, event_id: str) -> GiftEvent:
        ev = self.repo.get_event(scope, event_id)
        if ev is None:
            self._audit(user_id, "authz_denied", event_id)  # A09
            raise ForbiddenError("not your event")
        return ev
