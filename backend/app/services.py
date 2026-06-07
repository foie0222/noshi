"""サービス層。コンポーネントを業務フローに編成する。

application-design/services.md（CaptureRecordService / LedgerService / ReturnService /
PrivacyService / AccessControlService）を単一の NoshiService に集約（MVP）。
本人スコープ（A01）を全操作で強制し、セキュリティ関連操作を監査（A09）する。
"""
from __future__ import annotations

from app.domain import rules
from app.domain.entities import (
    GiftRecord, GiftEvent, ExtractionJob, ReturnSuggestion, Letter, AuditEntry,
)
from app.ports import OcrLlmPort, GiftCatalogPort
from app.repository import Repository


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

    # --- 撮影 → 抽出 ---
    def submit_extraction(self, user_id: str, image_refs: list[str]) -> ExtractionJob:
        out = self.ocr.extract(image_refs)
        job = ExtractionJob(
            user_id=user_id, status="completed",
            candidates=out["candidates"], confidence=out["confidence"],
            field_confidence=out.get("field_confidence", {}),
        )
        return self.repo.put_job(job)

    def extraction_needs_review(self, job: ExtractionJob) -> bool:
        return rules.needs_review(job.confidence)

    def field_review(self, job: ExtractionJob) -> dict:
        """項目別に要確認かどうかを返す（P0-2: 低信頼の項目だけ True）。"""
        return {k: rules.needs_review(v) for k, v in (job.field_confidence or {}).items()}

    # --- 記録 ---
    def create_record(self, user_id: str, amount: int, purpose: str,
                      party_name: str, direction: str, **extra) -> tuple[GiftRecord, GiftEvent]:
        errors = rules.validate_record(amount, purpose, party_name, direction)
        if errors:
            raise ValidationError(errors)
        rec = GiftRecord(
            user_id=user_id, amount=amount, purpose=purpose,
            party_name=party_name, direction=direction,
            occurred_at=extra.get("occurred_at", ""), relationship=extra.get("relationship", ""),
        )
        self.repo.put_record(rec)
        # received のみお返しイベントを生成（BR-3-GIVEN: given は対象外）
        ev = None
        if direction == "received":
            ev = GiftEvent(user_id=user_id, record_id=rec.id, status="received")
            self.repo.put_event(ev)
        return rec, ev

    def list_records(self, user_id: str) -> list[GiftRecord]:
        return self.repo.list_records(user_id)

    def relationships(self, user_id: str) -> list[dict]:
        """相手別の おつきあいバランス（差分・最終やりとり・偏り・気になる関係）を返す（N1, A01）。"""
        return rules.relationship_balance(self.repo.list_records(user_id))

    def gift_tax(self, user_id: str, year: int | None = None) -> dict:
        """本人の暦年「もらった」対象合計と110万円枠サマリを返す（P1-3, A01）。"""
        import datetime
        y = year or datetime.date.today().year
        return rules.gift_tax_summary(self.repo.list_records(user_id), y)

    def annual_summary(self, user_id: str, year: int | None = None) -> dict:
        """本人の指定年（既定は今年）の年間振り返りを返す（A01）。"""
        import datetime
        y = year or datetime.date.today().year
        return rules.annual_summary(self.repo.list_records(user_id), y)

    def party_summary(self, user_id: str) -> dict:
        """相手別の もらった/あげた/差分。"""
        summary: dict[str, dict] = {}
        for r in self.repo.list_records(user_id):
            s = summary.setdefault(r.party_name, {"received": 0, "given": 0})
            s[r.direction] = s.get(r.direction, 0) + r.amount
        for s in summary.values():
            s["diff"] = s.get("received", 0) - s.get("given", 0)
        return summary

    def update_record(self, user_id: str, record_id: str, *, amount: int,
                      purpose: str, party_name: str, **extra) -> GiftRecord:
        """保存済みレコードを修正する（AI抽出の誤りを本人が訂正）。本人スコープ強制＋監査（A01, A09）。

        direction は変更しない（イベント生成/破棄の整合を避けるため）。
        """
        rec = self.repo.get_record(user_id, record_id)
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
        if self.repo.get_record(user_id, record_id) is None:
            raise ForbiddenError("not your record")
        ok = self.repo.delete_record(user_id, record_id)
        self._audit(user_id, "delete_record", record_id)  # A09
        return ok

    # --- 半返し / お返し ---
    def half_return(self, amount: int, purpose: str) -> rules.ReturnRange:
        return rules.half_return(amount, purpose)

    def suggest_returns(self, user_id: str, event_id: str, budget: int,
                        relationship: str, purpose: str) -> list[dict]:
        self._require_event(user_id, event_id)
        return self.catalog.suggest(budget, relationship, purpose)

    def select_suggestion(self, user_id: str, event_id: str, suggestion: dict) -> ReturnSuggestion:
        ev = self._require_event(user_id, event_id)
        sug = ReturnSuggestion(
            event_id=event_id, title=suggestion["title"], summary=suggestion.get("summary", ""),
            external_ref=suggestion.get("external_ref", ""), price_band=suggestion.get("price_band", ""),
        )
        ev.suggestion_id = sug.id
        self.repo.put_event(ev)
        return sug

    def generate_letter(self, user_id: str, event_id: str, purpose: str,
                        relationship: str, tone: str) -> Letter:
        ev = self._require_event(user_id, event_id)
        # 送信は最小化（BR-LTR-1）: 氏名等の restricted は渡さない
        body = self.ocr.generate_letter(purpose=purpose, relationship=relationship, tone=tone)
        letter = Letter(event_id=event_id, tone=tone, body_text=body)
        ev.letter_id = letter.id
        self.repo.put_event(ev)
        return letter

    # --- イベント状態 ---
    def set_event_status(self, user_id: str, event_id: str, status: str) -> GiftEvent:
        if status not in ("received", "considering", "done"):
            raise ValidationError([f"不正なステータス: {status}"])
        ev = self._require_event(user_id, event_id)
        ev.status = status  # 自由遷移（BR-EVT-1）
        return self.repo.put_event(ev)

    def list_pending_events(self, user_id: str) -> list[GiftEvent]:
        return self.repo.list_pending_events(user_id)

    def get_event(self, user_id: str, event_id: str) -> GiftEvent:
        return self._require_event(user_id, event_id)

    # --- 表示用ビュー（UX: ID ではなく相手・用途・金額・期限を見せる） ---
    def _view(self, user_id: str, ev: GiftEvent) -> dict:
        rec = self.repo.get_record(user_id, ev.record_id)
        purpose = rec.purpose if rec else ""
        occurred_at = rec.occurred_at if rec else ""
        due = rules.due_date(occurred_at, purpose)  # BR-3-DUE
        return {
            "id": ev.id,
            "status": ev.status,
            "record_id": ev.record_id,
            "party_name": rec.party_name if rec else "",
            "purpose": purpose,
            "amount": rec.amount if rec else 0,
            "direction": rec.direction if rec else "received",
            "occurred_at": occurred_at,
            "due_at": due.isoformat() if due else None,
            "days_left": rules.days_left(due),
            "suggestion_id": ev.suggestion_id,
            "letter_id": ev.letter_id,
        }

    def pending_views(self, user_id: str) -> list[dict]:
        """未完了お返しを、相手・用途・金額・期限つきで、残日数の近い順に返す。

        お返し不要（期限なし）の用途は除外する（BR-3-DUE-2）。
        """
        views = [self._view(user_id, e) for e in self.repo.list_pending_events(user_id)]
        views = [v for v in views if v["due_at"] is not None]  # 期限なしは除外
        views.sort(key=lambda v: v["days_left"])  # 残日数 昇順（期限が近い順）
        return views

    def event_view(self, user_id: str, event_id: str) -> dict:
        """単一イベントを表示用ビューで返す（本人スコープ強制）。"""
        return self._view(user_id, self._require_event(user_id, event_id))

    def event_for_record(self, user_id: str, record_id: str):
        """台帳の記録IDから対応するイベントを引く（ledger→お返しフロー、done 含む）。"""
        for e in self.repo.list_events(user_id):
            if e.record_id == record_id:
                return e
        return None

    # --- 内部: 本人スコープ ---
    def _require_event(self, user_id: str, event_id: str) -> GiftEvent:
        ev = self.repo.get_event(user_id, event_id)
        if ev is None:
            self._audit(user_id, "authz_denied", event_id)  # A09
            raise ForbiddenError("not your event")
        return ev
