"""サービス層。コンポーネントを業務フローに編成する。

application-design/services.md（CaptureRecordService / LedgerService / ReturnService /
PrivacyService / AccessControlService）を単一の NoshiService に集約（MVP）。
本人スコープ（A01）を全操作で強制し、セキュリティ関連操作を監査（A09）する。
"""

from __future__ import annotations

import datetime
from typing import Any

from app.account import canonical_sub
from app.domain import rules
from app.domain.entities import (
    AuditEntry,
    ExtractionJob,
    GiftEvent,
    GiftRecord,
    Household,
    Membership,
    Party,
    ReturnSuggestion,
)
from app.images import ImageStore
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
    def __init__(
        self,
        repo: Repository,
        ocr: OcrLlmPort,
        catalog: GiftCatalogPort,
        images: ImageStore | None = None,
    ):
        self.repo = repo
        self.ocr = ocr
        self.catalog = catalog
        self.images = images or ImageStore()  # 既定は環境変数 NOSHI_IMAGE_BUCKET を読む

    # --- 撮影画像（S3・署名付きURL）（#35）---
    def image_upload_url(self, user_id: str, content_type: str) -> dict[str, Any]:
        """アップロード用のサイズ上限つき署名POST(url/fields)と保存先キーを払い出す（世帯スコープ）。"""
        if content_type not in ("image/jpeg", "image/png", "image/webp"):
            raise ValidationError(["対応していない画像形式です。"])
        key = self.images.new_key(self._scope(user_id), content_type)
        post = self.images.upload_post(key, content_type)
        return {"url": post["url"], "fields": post["fields"], "key": key}

    # --- 監査 ---
    def _audit(self, actor_id: str, action: str, target_ref: str) -> None:
        self.repo.append_audit(AuditEntry(actor_id=actor_id, action=action, target_ref=target_ref))

    # --- 家族共有: 世帯（記録・お返しは「本人」ではなく「世帯」に属する）---
    def resolve_household(
        self, user_id: str, email: str = "", email_verified: bool = False
    ) -> Household:
        """ユーザーの世帯を返す。エイリアス解決→membership→自動リンク→新規作成の順（A01）。"""
        # 1. 別名なら代表 sub に正規化（1ホップ）。
        user_id = canonical_sub(self.repo, user_id)

        # 2. 既存 membership があればその世帯（＋email 自己修復・EMAIL# backfill）。
        #    email 自己修復（#167）: _scope() 経由の初回アクセスで世帯が作られると
        #    email="" のまま保存され、メンバー一覧で「ご家族のメンバー」としか表示
        #    できない。email が判明している呼び出しで補完・追従する。
        m = self.repo.get_membership(user_id)
        if m is not None:
            h = self.repo.get_household(m.household_id)
            if h is not None:
                if email and m.email != email:
                    m.email = email
                    self.repo.put_membership(m)
                if email and email_verified:
                    # claim は条件付き put（atomic）。既に別代表が確保済みなら False で no-op。
                    self.repo.claim_email_primary(email, user_id)
                return h

        # 3. 初回 sub。検証済みメールなら EMAIL# 条件付き put で代表確保 or 既存合流。
        if email and email_verified:
            claimed = self.repo.claim_email_primary(email, user_id)
            if not claimed:
                primary = self.repo.get_email_primary(email)
                if primary and primary != user_id:
                    pm = self.repo.get_membership(primary)
                    ph = self.repo.get_household(pm.household_id) if pm is not None else None
                    if ph is not None:
                        # 合流先世帯が存在するときだけ別名を張って合流する。
                        self.repo.put_account_link(user_id, primary, email=email)
                        self._audit(user_id, "auto_link", primary)  # A09
                        return ph
                    # 合流先世帯が無い（代表削除済み等）→ fail-closed。
                    # EMAIL# が defunct な代表を指したままだと、同じメールの次の新 sub も
                    # 合流できず収束しない。このユーザーを新しい代表に張り替えてから step4 へ
                    # 進み、以後のログインがここに収束するようにする（自己修復）。
                    self.repo.set_email_primary(email, user_id)

        # 4. 新規世帯を作成し本人を owner にする。
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

    # --- お返し期限のメール通知 設定（#178）---
    def notification_prefs(self, user_id: str) -> dict[str, Any]:
        """メール通知の受け取り設定を返す（既定オン）。"""
        self.resolve_household(user_id)  # メンバーシップを確実に用意する
        m = self.repo.get_membership(user_id)
        return {"email": m.notify_email if m is not None else True}

    def set_notification_prefs(self, user_id: str, email_on: bool) -> dict[str, Any]:
        """メール通知の受け取り可否を切り替える。"""
        self.resolve_household(user_id)
        m = self.repo.get_membership(user_id)
        if m is not None:
            m.notify_email = email_on
            self.repo.put_membership(m)
        return {"email": email_on}

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

    def delete_account(self, user_id: str) -> None:
        """アカウントを削除する（#118）。本人の世帯メンバーシップを外し、家族が残れば
        台帳は保持して owner を引き継ぐ。最後の利用者なら世帯データを完全消去する。
        Cognito ユーザー本体の削除は呼び出し側（main）で行う。"""
        m = self.repo.get_membership(user_id)
        hid = m.household_id if m else ""
        if m:
            others = [x for x in self.repo.list_members(hid) if x.user_id != user_id]
            if others:
                # 管理者が抜けて家族が残るなら最古参へ引き継ぐ（台帳は家族の資産として残す）。
                if m.role == "owner":
                    heir = sorted(others, key=lambda x: x.joined_at)[0]
                    self.repo.put_membership(
                        Membership(
                            user_id=heir.user_id,
                            household_id=hid,
                            role="owner",
                            email=heir.email,
                            joined_at=heir.joined_at,
                        )
                    )
                    self._audit(user_id, "transfer_ownership", heir.user_id)  # A09
            else:
                self._purge_household(hid)  # 最後の利用者: 世帯データを完全消去
            self.repo.delete_membership(user_id)
        self._audit(user_id, "delete_account", hid)  # A09

    def _purge_household(self, hid: str) -> None:
        """世帯に属する全データ（記録・お返し・相手・マスタ・世帯本体）と画像を消す。"""
        for rec in self.repo.list_records(hid):
            if rec.image_key and self.images.enabled():
                self.images.delete(rec.image_key)
            self.repo.delete_record(hid, rec.id)
        for ev in self.repo.list_events(hid):
            self.repo.delete_event(hid, ev.id)
        for p in self.repo.list_parties(hid):
            self.repo.delete_party(hid, p.id)
        for name in list(self.repo.list_household_purposes(hid)):
            self.repo.remove_household_purpose(hid, name)
        for name in list(self.repo.list_household_relationships(hid)):
            self.repo.remove_household_relationship(hid, name)
        self.repo.delete_household(hid)

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

    # --- 用途マスタ（システム既定 ＋ 世帯独自）（#37、続柄と同条件）---
    def purpose_master(self, user_id: str) -> dict[str, Any]:
        """選択肢に出す用途一覧。既定（システム固定）＋世帯独自の追加分（重複排除）。"""
        defaults = list(rules.PURPOSE_DEFAULTS)
        customs = [
            p for p in self.repo.list_household_purposes(self._scope(user_id)) if p not in defaults
        ]
        return {"options": defaults + customs, "defaults": defaults}

    def add_purpose(self, user_id: str, name: str) -> dict[str, Any]:
        """世帯独自の用途を追加する（世帯スコープで家族に共有）。重複排除・20字・30件上限。"""
        value = (name or "").strip()
        if value and value not in rules.PURPOSE_DEFAULTS:
            if len(value) > 20:
                raise ValidationError(["用途は20文字以内で入力してください。"])
            scope = self._scope(user_id)
            existing = self.repo.list_household_purposes(scope)
            if value not in existing and len(existing) >= rules.PURPOSE_CUSTOM_MAX:
                raise ValidationError(
                    [
                        f"独自の用途は{rules.PURPOSE_CUSTOM_MAX}件までです。不要なものを削除してください。"
                    ]
                )
            self.repo.add_household_purpose(scope, value)
            self._audit(user_id, "add_purpose", scope)  # A09
        return self.purpose_master(user_id)

    def remove_purpose(self, user_id: str, name: str) -> dict[str, Any]:
        """世帯独自の用途をマスタから削除する（既定は対象外、過去レコードの値は残す）。"""
        value = (name or "").strip()
        if value and value not in rules.PURPOSE_DEFAULTS:
            scope = self._scope(user_id)
            self.repo.remove_household_purpose(scope, value)
            self._audit(user_id, "remove_purpose", scope)  # A09
        return self.purpose_master(user_id)

    # --- 相手（人）マスタ（#47）。同名でも別人を区別するため ID で識別する ---
    @staticmethod
    def _party_dict(p: Party) -> dict[str, Any]:
        return {"id": p.id, "name": p.name, "relationship": p.relationship}

    def parties(self, user_id: str) -> list[dict[str, Any]]:
        """世帯の相手一覧（id・名前・続柄）。同名は続柄で見分けられる。"""
        ps = self.repo.list_parties(self._scope(user_id))
        return [self._party_dict(p) for p in sorted(ps, key=lambda x: x.name)]

    def add_party(self, user_id: str, name: str, relationship: str = "") -> dict[str, Any]:
        """相手を世帯に追加する。同名でも別人として別レコードを作る（識別はID）。"""
        value = (name or "").strip()
        if not value:
            raise ValidationError(["お名前を入力してください。"])
        if len(value) > 30:
            raise ValidationError(["お名前は30文字以内で入力してください。"])
        scope = self._scope(user_id)
        party = self.repo.put_party(
            scope, Party(name=value, relationship=(relationship or "").strip())
        )
        self._audit(user_id, "add_party", scope)  # A09
        return self._party_dict(party)

    def update_party(
        self, user_id: str, party_id: str, name: str, relationship: str
    ) -> dict[str, Any]:
        """相手の名前・続柄を更新し、記録の表示スナップショット(party_name)も同期する。"""
        scope = self._scope(user_id)
        party = self.repo.get_party(scope, party_id)
        if party is None:
            raise ForbiddenError("not your party")
        value = (name or "").strip()
        if not value:
            raise ValidationError(["お名前を入力してください。"])
        party.name = value
        party.relationship = (relationship or "").strip()
        self.repo.put_party(scope, party)
        # 表示用スナップショットを追従（おつきあい/台帳の名前が古くならないように）
        for rec in self.repo.list_records(scope):
            if rec.party_id == party_id and rec.party_name != value:
                rec.party_name = value
                self.repo.put_record(rec)
        self._audit(user_id, "update_party", scope)  # A09
        return self._party_dict(party)

    def delete_party(self, user_id: str, party_id: str) -> bool:
        """相手をマスタから削除する（過去レコードは表示用スナップショットで残る）。"""
        scope = self._scope(user_id)
        ok = self.repo.delete_party(scope, party_id)
        if ok:
            self._audit(user_id, "delete_party", scope)  # A09
        return ok

    def _resolve_party(self, scope: str, party_id: str, party_name: str) -> Party:
        """party_id があれば取得、無ければ名前から相手を解決（既存の同名 or 新規作成）。

        フロントは常に party_id を渡す（ピッカーで選択/新規）。party_name のみの経路は
        テスト/簡易用のフォールバック。
        """
        if party_id:
            p = self.repo.get_party(scope, party_id)
            if p is None:
                raise ValidationError(["相手が見つかりません。"])
            return p
        name = (party_name or "").strip()
        if not name:
            raise ValidationError(["お名前を入力してください。"])
        for p in self.repo.list_parties(scope):
            if p.name == name:
                return p
        return self.repo.put_party(scope, Party(name=name))

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
        self,
        user_id: str,
        amount: int,
        purpose: str,
        direction: str,
        party_name: str = "",
        **extra: Any,
    ) -> tuple[GiftRecord, GiftEvent | None]:
        scope = self._scope(user_id)
        # 相手は party_id で識別（同名でも別人を区別、#47）。名前はマスタから取りスナップショット。
        party = self._resolve_party(scope, extra.get("party_id", ""), party_name)
        errors = rules.validate_record(amount, purpose, party.name, direction)
        if errors:
            raise ValidationError(errors)
        rec = GiftRecord(
            user_id=scope,
            amount=amount,
            purpose=purpose,
            party_name=party.name,
            party_id=party.id,
            direction=direction,
            occurred_at=extra.get("occurred_at", ""),
            item=extra.get("item", ""),
            image_key=extra.get("image_key", ""),
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

    def _relationship_map(self, scope: str) -> tuple[dict[str, str], dict[str, str]]:
        """party_id / 相手名 → 現在の続き柄。続き柄は人の属性なので最新値を引く。"""
        by_id: dict[str, str] = {}
        by_name: dict[str, str] = {}
        for p in self.repo.list_parties(scope):
            rel = (p.relationship or "").strip()
            if rel:
                by_id[p.id] = rel
                by_name[p.name] = rel
        return by_id, by_name

    def relationships(self, user_id: str) -> list[dict[str, Any]]:
        """世帯の おつきあいバランス（差分・最終やりとり・偏り・気になる関係）を返す（N1）。

        続き柄は人の現在の属性で補正する（おつきあいを続き柄でグルーピングするため）。
        """
        scope = self._scope(user_id)
        rows = rules.relationship_balance(self.repo.list_records(scope))
        by_id, by_name = self._relationship_map(scope)
        for r in rows:
            cur = by_id.get(r.get("party_id", "")) or by_name.get(r.get("party_name", ""))
            if cur:
                r["relationship"] = cur
        return rows

    def ledger_records(self, user_id: str) -> list[dict[str, Any]]:
        """台帳のレコード一覧。各レコードに相手の現在の続き柄を添える（台帳の表示用）。"""
        scope = self._scope(user_id)
        by_id, by_name = self._relationship_map(scope)
        out: list[dict[str, Any]] = []
        for r in self.repo.list_records(scope):
            d = dict(vars(r))
            d["relationship"] = by_id.get(r.party_id, "") or by_name.get(r.party_name, "")
            out.append(d)
        return out

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
        party_name: str = "",
        **extra: Any,
    ) -> GiftRecord:
        """保存済みレコードを修正する（AI抽出の誤りを本人が訂正）。本人スコープ強制＋監査（A01, A09）。

        direction は変更しない（イベント生成/破棄の整合を避けるため）。
        """
        scope = self._scope(user_id)
        rec = self.repo.get_record(scope, record_id)
        if rec is None:
            raise ForbiddenError("not your record")
        # 相手の付け替え（#47）。party_id 指定があれば相手を解決して名前も更新。
        # party_id が無く party_name のみ指定なら表示スナップショットだけ更新（簡易/テスト）。
        if extra.get("party_id"):
            party = self._resolve_party(scope, extra["party_id"], "")
            rec.party_id = party.id
            rec.party_name = party.name
        elif party_name:
            rec.party_name = party_name
        errors = rules.validate_record(amount, purpose, rec.party_name, rec.direction)
        if errors:
            raise ValidationError(errors)
        rec.amount = amount
        rec.purpose = purpose
        if "item" in extra:
            rec.item = extra["item"]
        if "occurred_at" in extra:
            rec.occurred_at = extra["occurred_at"]
        if "image_key" in extra:
            new_key = extra["image_key"] or ""
            # 差し替え/削除なら旧オブジェクトを後始末（#35）
            if rec.image_key and rec.image_key != new_key and self.images.enabled():
                self.images.delete(rec.image_key)
            rec.image_key = new_key
        self.repo.put_record(rec)
        self._audit(user_id, "update_record", record_id)  # A09
        return rec

    def delete_record(self, user_id: str, record_id: str) -> bool:
        scope = self._scope(user_id)
        rec = self.repo.get_record(scope, record_id)
        if rec is None:
            raise ForbiddenError("not your record")
        # 紐づくお返しイベントも削除（孤立させない、#36）。
        for ev in self.repo.list_events(scope):
            if ev.record_id == record_id:
                self.repo.delete_event(scope, ev.id)
        if rec.image_key and self.images.enabled():  # 画像も後始末（#35）
            self.images.delete(rec.image_key)
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

    def log_suggestion_click(
        self, user_id: str, item_code: str, bucket: str, position: int, rel_group: str
    ) -> None:
        """提案リンクのクリック計測（効果計測のMVP分）。

        user_id は認可文脈の明示用に受け取るが catalog には渡さない（PIIなし）。
        他のサービスメソッドとシグネチャの一貫性を保つため引数として維持。
        rel_group は配信時に返した続柄グループの echo（グループ別CTR計測用）。
        """
        self.catalog.log_click(item_code, bucket, position, rel_group)

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
        image_key = rec.image_key if rec else ""
        # 続柄は相手(Party)から引く（記録ではなく人の属性、#47）。名前も最新を優先。
        party = self.repo.get_party(scope, rec.party_id) if (rec and rec.party_id) else None
        return {
            "id": ev.id,
            "status": ev.status,
            "record_id": ev.record_id,
            "party_id": rec.party_id if rec else "",
            "party_name": (party.name if party else (rec.party_name if rec else "")),
            "purpose": purpose,
            "amount": rec.amount if rec else 0,
            "direction": rec.direction if rec else "received",
            "occurred_at": occurred_at,
            "item": rec.item if rec else "",
            "relationship": party.relationship if party else "",
            "due_at": due.isoformat() if due else None,
            "due_default": default_due.isoformat() if default_due else None,
            "due_overridden": override is not None,
            "days_left": rules.days_left(due),
            "suggestion_id": ev.suggestion_id,
            # 撮影画像（署名付きGET URL、#35）。S3 無効時や未設定時は None。
            "image_url": (
                self.images.view_url(image_key) if image_key and self.images.enabled() else None
            ),
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

    def record_detail(self, user_id: str, record_id: str) -> dict[str, Any]:
        """記録IDの詳細ビュー（#48）。received はイベントビュー、given は記録ベース。

        あげた(given)はお返しイベントを持たないため、台帳からタップしても詳細・修正・
        削除ができるよう、イベントが無い場合は記録から組み立てたビューを返す。
        """
        scope = self._scope(user_id)
        rec = self.repo.get_record(scope, record_id)
        if rec is None:
            self._audit(user_id, "authz_denied", record_id)  # A09
            raise ForbiddenError("not your record")
        for ev in self.repo.list_events(scope):
            if ev.record_id == record_id:
                return self._view(scope, ev)
        # イベントなし（given）: 期限/ステータス等は持たない記録ベースのビュー
        party = self.repo.get_party(scope, rec.party_id) if rec.party_id else None
        return {
            "id": "",
            "status": "",
            "record_id": rec.id,
            "party_id": rec.party_id,
            "party_name": party.name if party else rec.party_name,
            "purpose": rec.purpose,
            "amount": rec.amount,
            "direction": rec.direction,
            "occurred_at": rec.occurred_at,
            "item": rec.item,
            "relationship": party.relationship if party else "",
            "due_at": None,
            "due_default": None,
            "due_overridden": False,
            "days_left": None,
            "suggestion_id": None,
            "image_url": (
                self.images.view_url(rec.image_key)
                if rec.image_key and self.images.enabled()
                else None
            ),
        }

    # --- 内部: 世帯スコープ（user_id は監査用、scope は世帯ID）---
    def _require_event(self, user_id: str, scope: str, event_id: str) -> GiftEvent:
        ev = self.repo.get_event(scope, event_id)
        if ev is None:
            self._audit(user_id, "authz_denied", event_id)  # A09
            raise ForbiddenError("not your event")
        return ev
