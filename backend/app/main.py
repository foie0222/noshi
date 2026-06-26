"""noshi BFF/API（FastAPI）。

api-contracts.md の論理 API を実装。スタブ認証（X-User-Id）で本人スコープを確立し、
NoshiService に委譲。エラーは汎用文言で返し内部情報を漏らさない（A03）。
DI で Repository/ポートを差し替え可能（MVP は InMemory + モック）。
"""

from __future__ import annotations

from dataclasses import replace
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.auth import Identity
from app.ports import GiftCatalogMock, GiftCatalogPort, OcrLlmPort
from app.repository import InMemoryRepository, Repository
from app.schemas import (
    CaptureIn,
    DeleteAccountIn,
    DueIn,
    ImageUploadIn,
    JoinHouseholdIn,
    NotificationPrefsIn,
    PartyIn,
    PurposeIn,
    RecordIn,
    RecordUpdateIn,
    RelationshipIn,
    SelectSuggestionIn,
    StatusIn,
    SuggestionClickIn,
)
from app.services import ForbiddenError, NoshiService, ValidationError


def _default_ocr() -> OcrLlmPort:
    """OCR/LLM の実装を選ぶ（NOSHI_LLM_PROVIDER。worker と共用の adapters.default_ocr）。

    本番では OCR は worker（SQS）で実行されるため、API 側がこの実装を直接使うのは
    S3/SQS 未設定のローカル・モック時の同期フォールバックのみ。
    """
    from app.adapters import default_ocr

    ocr: OcrLlmPort = default_ocr()
    return ocr


def _default_catalog() -> GiftCatalogPort:
    """カタログ実装を選ぶ。NOSHI_CATALOG_TABLE があれば本番(DynamoDB)、既定はモック。"""
    import os

    if os.environ.get("NOSHI_CATALOG_TABLE"):
        from app.catalog.adapter import DynamoCatalogAdapter
        from app.catalog.store import CatalogStore

        return DynamoCatalogAdapter(store=CatalogStore(), fallback=GiftCatalogMock())
    return GiftCatalogMock()


def _default_repository() -> Repository:
    """既定のデータ層を選ぶ。NOSHI_USE_DYNAMO=1 か DYNAMODB_ENDPOINT があれば永続化(DynamoDB)。

    未設定なら InMemory（再起動でデータは消える）。本番/ローカル永続化は環境変数で切替。
    """
    import os

    if os.environ.get("NOSHI_USE_DYNAMO") == "1" or os.environ.get("DYNAMODB_ENDPOINT"):
        from app.repository import DynamoRepository

        return DynamoRepository()
    return InMemoryRepository()


def create_app(service: NoshiService | None = None) -> FastAPI:
    app = FastAPI(title="noshi API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    svc = service or NoshiService(_default_repository(), _default_ocr(), _default_catalog())

    def current_identity(
        authorization: str | None = Header(default=None),
        x_user_id: str | None = Header(default=None),
    ) -> Identity:
        # JWT 構成済み(Cognito/HS256)なら Bearer トークンを検証。未構成なら
        # 開発用 X-User-Id スタブにフォールバック。どちらも無ければ 401（A07）。
        from app.account import canonical_sub
        from app.auth import AuthError, auth_configured, decode_identity

        def _normalized(ident: Identity) -> Identity:
            # リクエスト境界で生 sub を代表 sub に正規化（別名でも同じ世帯に解決）。
            cano = canonical_sub(svc.repo, ident.user_id)
            if cano == ident.user_id:
                return ident
            return replace(ident, user_id=cano, raw_user_id=ident.raw_user_id or ident.user_id)

        if auth_configured():
            # 本番: Cognito/JWT 必須。X-User-Id スタブは受け付けない（なりすまし防止）。
            if not authorization:
                raise HTTPException(status_code=401, detail="authentication required")
            token = (
                authorization[7:] if authorization.lower().startswith("bearer ") else authorization
            )
            try:
                return _normalized(decode_identity(token))
            except AuthError:
                raise HTTPException(status_code=401, detail="authentication required") from None
        # ローカル開発: スタブ認証（X-User-Id）。
        if x_user_id:
            return _normalized(Identity(user_id=x_user_id, raw_user_id=x_user_id))
        raise HTTPException(status_code=401, detail="authentication required")

    def current_user(ident: Identity = Depends(current_identity)) -> str:
        return ident.user_id

    @app.exception_handler(ForbiddenError)
    async def _forbidden(_req: Request, _exc: Exception) -> JSONResponse:
        return JSONResponse(status_code=403, content={"detail": "forbidden"})

    @app.exception_handler(ValidationError)
    async def _validation(_req: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(status_code=422, content={"detail": exc.errors})

    @app.get("/api/health")
    def health() -> dict[str, Any]:
        return {"status": "ok"}

    @app.get("/api/household")
    def household(ident: Identity = Depends(current_identity)) -> dict[str, Any]:
        # 自分の世帯（名前・招待コード・メンバー）。初回は自動作成される。
        svc.resolve_household(ident.user_id, email=ident.email, email_verified=ident.email_verified)
        return {"household": svc.household_view(ident.user_id)}

    @app.get("/api/notifications")
    def get_notifications(ident: Identity = Depends(current_identity)) -> dict[str, Any]:
        # お返し期限のメール通知 設定（既定オン、#178）。
        svc.resolve_household(ident.user_id, email=ident.email, email_verified=ident.email_verified)
        return svc.notification_prefs(ident.user_id)

    @app.put("/api/notifications")
    def put_notifications(
        body: NotificationPrefsIn, ident: Identity = Depends(current_identity)
    ) -> dict[str, Any]:
        svc.resolve_household(ident.user_id, email=ident.email, email_verified=ident.email_verified)
        return svc.set_notification_prefs(ident.user_id, body.email)

    @app.post("/api/household/join")
    def join_household(
        body: JoinHouseholdIn, ident: Identity = Depends(current_identity)
    ) -> dict[str, Any]:
        # 招待コードで家族の世帯に参加（以後その世帯の台帳を共有）。
        svc.join_household(ident.user_id, body.code, email=ident.email)
        return {"household": svc.household_view(ident.user_id)}

    @app.post("/api/household/leave")
    def leave_household(ident: Identity = Depends(current_identity)) -> dict[str, Any]:
        # 現在の世帯から脱退（台帳は家族側に残り、本人は新しい空の世帯になる）。
        svc.leave_household(ident.user_id)
        return {"household": svc.household_view(ident.user_id)}

    @app.get("/api/account/delete-info")
    def account_delete_info(ident: Identity = Depends(current_identity)) -> dict[str, Any]:
        # 削除画面で再認証要否を判断するための情報。Apple 連携があれば再認証(SiwA)が要る。
        import os

        from app import cognito_admin

        pool = os.environ.get("NOSHI_COGNITO_POOL_ID")
        subs = svc.account_subs(ident.user_id)
        apple_linked = cognito_admin.any_apple_sub(pool, subs) if pool else False
        return {"apple_linked": apple_linked}

    @app.delete("/api/account")
    def delete_account(
        ident: Identity = Depends(current_identity),
        body: DeleteAccountIn | None = None,
    ) -> dict[str, Any]:
        # 論理アカウント削除（#118/#198）。Apple code があれば失効（ベストエフォート）→
        # データ/別名/EMAIL# 削除 → 本人の全 Cognito ユーザー削除。
        import os

        from app import apple_revoke, cognito_admin

        code = body.apple_authorization_code if body else None
        if code:
            if not apple_revoke.revoke_apple_for_code(code):
                import logging

                logging.getLogger(__name__).warning("apple token revoke failed (削除は続行)")
        subs = svc.delete_account(ident.user_id)
        pool = os.environ.get("NOSHI_COGNITO_POOL_ID")
        if pool:
            cognito_admin.delete_users_by_subs(pool, subs)
        return {"ok": True}

    @app.delete("/api/household/members/{target_user_id}")
    def remove_member(
        target_user_id: str, ident: Identity = Depends(current_identity)
    ) -> dict[str, Any]:
        # 管理者が家族メンバーを世帯から外す。
        return {"household": svc.remove_member(ident.user_id, target_user_id)}

    @app.get("/api/home")
    def home(uid: str = Depends(current_user)) -> dict[str, Any]:
        # P0-3: 収支・差分は見せない。主役はお返し期限（pending: 期限つき・残日数昇順）。
        records = svc.list_records(uid)
        return {
            "pending": svc.pending_views(uid),
            "recent": [vars(r) for r in records[-5:]],
        }

    def _capture_view(job: Any) -> dict[str, Any]:
        return {
            "job_id": job.id,
            "status": job.status,
            "candidates": job.candidates,
            "confidence": job.confidence,
            "field_confidence": job.field_confidence,
            "field_review": svc.field_review(job),  # 項目別 要確認（P0-2）
            "needs_review": svc.extraction_needs_review(job),
        }

    @app.post("/api/capture")
    def capture(body: CaptureIn | None = None, uid: str = Depends(current_user)) -> dict[str, Any]:
        # 本番(S3+SQS構成): 画像を保存し pending を返す → worker が OCR → フロントは GET でポーリング。
        # OCR は API Gateway の 30s 統合上限を超え得るためリクエストから切り離す。
        # ローカル/モック(未設定)時は同期インライン抽出にフォールバック。
        image = body.image if (body and body.image) else None
        try:
            if image and svc.async_extraction_enabled():
                job = svc.enqueue_extraction(uid, image)
                return {"job_id": job.id, "status": job.status}  # pending
            job = svc.submit_extraction(uid, [image] if image else ["mock.jpg"])
        except Exception as exc:  # 抽出失敗は握り潰さず 502 で返す（モックへ無言降格しない）
            import logging

            logging.getLogger("noshi").exception("extraction failed")
            raise HTTPException(
                status_code=502,
                detail="画像の読み取りに失敗しました。時間をおいて再度お試しください。",
            ) from exc
        return _capture_view(job)

    @app.get("/api/capture/{job_id}")
    def capture_status(job_id: str, uid: str = Depends(current_user)) -> dict[str, Any]:
        # フロントのポーリング: 完了なら候補を返し、pending/failed なら status のみ。
        job = svc.get_extraction(uid, job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="not found")
        if job.status == "completed":
            return _capture_view(job)
        return {"job_id": job.id, "status": job.status}

    @app.post("/api/records")
    def create_record(body: RecordIn, uid: str = Depends(current_user)) -> dict[str, Any]:
        rec, ev = svc.create_record(
            uid,
            amount=body.amount,
            purpose=body.purpose,
            direction=body.direction,
            party_id=body.party_id,
            party_name=body.party_name,
            occurred_at=body.occurred_at,
            item=body.item,
            image_key=body.image_key,
        )
        # given はお返しイベントを持たない（ev is None）。安全に null を返す（FR-8-1）。
        return {"record": vars(rec), "event": vars(ev) if ev is not None else None}

    @app.post("/api/images/upload-url")
    def image_upload_url(body: ImageUploadIn, uid: str = Depends(current_user)) -> dict[str, Any]:
        # #35: 撮影画像の署名付きPUT URLを払い出す。S3 未設定（ローカル）は 501。
        if not svc.images.enabled():
            raise HTTPException(status_code=501, detail="画像保存は未設定です。")
        return svc.image_upload_url(uid, body.content_type)

    @app.get("/api/relationships")
    def relationships(uid: str = Depends(current_user)) -> dict[str, Any]:
        # N1: 相手別おつきあいバランス（本人データのみ）。
        return {"relationships": svc.relationships(uid)}

    @app.get("/api/relationship-master")
    def relationship_master(uid: str = Depends(current_user)) -> dict[str, Any]:
        # #1: 続柄の選択肢（システム既定＋世帯独自）。
        return svc.relationship_master(uid)

    @app.post("/api/relationship-master")
    def add_relationship(body: RelationshipIn, uid: str = Depends(current_user)) -> dict[str, Any]:
        # #1: 世帯独自の続柄を追加（世帯スコープで家族に共有）。
        return svc.add_relationship(uid, body.name)

    @app.delete("/api/relationship-master/{name}")
    def remove_relationship(name: str, uid: str = Depends(current_user)) -> dict[str, Any]:
        # #1: 世帯独自の続柄を削除（既定は対象外／過去レコードの値は残す）。
        return svc.remove_relationship(uid, name)

    @app.get("/api/purpose-master")
    def purpose_master(uid: str = Depends(current_user)) -> dict[str, Any]:
        # #37: 用途の選択肢（システム既定＋世帯独自）。
        return svc.purpose_master(uid)

    @app.post("/api/purpose-master")
    def add_purpose(body: PurposeIn, uid: str = Depends(current_user)) -> dict[str, Any]:
        # #37: 世帯独自の用途を追加（世帯スコープで家族に共有）。
        return svc.add_purpose(uid, body.name)

    @app.delete("/api/purpose-master/{name}")
    def remove_purpose(name: str, uid: str = Depends(current_user)) -> dict[str, Any]:
        # #37: 世帯独自の用途を削除（既定は対象外／過去レコードの値は残す）。
        return svc.remove_purpose(uid, name)

    @app.get("/api/parties")
    def parties(uid: str = Depends(current_user)) -> dict[str, Any]:
        # #47: 相手（人）の一覧。同名でも別人を ID で区別。
        return {"parties": svc.parties(uid)}

    @app.post("/api/parties")
    def add_party(body: PartyIn, uid: str = Depends(current_user)) -> dict[str, Any]:
        # #47: 相手を新規追加（同名でも別人として作成）。
        return {"party": svc.add_party(uid, body.name, body.relationship)}

    @app.patch("/api/parties/{party_id}")
    def update_party(
        party_id: str, body: PartyIn, uid: str = Depends(current_user)
    ) -> dict[str, Any]:
        # #47: 相手の名前・続柄を更新（記録の表示名も同期）。
        return {"party": svc.update_party(uid, party_id, body.name, body.relationship)}

    @app.delete("/api/parties/{party_id}")
    def remove_party(party_id: str, uid: str = Depends(current_user)) -> dict[str, Any]:
        # #47: 相手をマスタから削除（過去レコードは表示名スナップショットで残る）。
        return {"ok": svc.delete_party(uid, party_id)}

    @app.get("/api/gift-tax")
    def gift_tax(uid: str = Depends(current_user)) -> dict[str, Any]:
        # P1-3: 暦年の対象もらった合計と110万枠の気づき（税アドバイスではない）。
        return svc.gift_tax(uid)

    @app.get("/api/annual")
    def annual(year: int | None = None, uid: str = Depends(current_user)) -> dict[str, Any]:
        # 年間振り返り（本人の受領/あげた件数・合計・相手人数）。
        return svc.annual_summary(uid, year)

    @app.get("/api/ledger")
    def ledger(uid: str = Depends(current_user)) -> dict[str, Any]:
        return {
            "records": svc.ledger_records(uid),
            "party_summary": svc.party_summary(uid),
        }

    @app.patch("/api/records/{record_id}")
    def update_record(
        record_id: str, body: RecordUpdateIn, uid: str = Depends(current_user)
    ) -> dict[str, Any]:
        # AI抽出の誤りを本人が訂正（本人スコープ＋監査）。direction は変更しない。
        # None のフィールドは渡さない＝既存値を保持（金額のみ修正で日付が消えないように）。
        extra = {
            k: v
            for k, v in (
                ("occurred_at", body.occurred_at),
                ("item", body.item),
                ("image_key", body.image_key),
            )
            if v is not None
        }
        if body.party_id:  # 空なら相手は変更しない（#47）
            extra["party_id"] = body.party_id
        rec = svc.update_record(
            uid,
            record_id,
            amount=body.amount,
            purpose=body.purpose,
            **extra,
        )
        return {"record": vars(rec)}

    @app.delete("/api/records/{record_id}")
    def delete_record(record_id: str, uid: str = Depends(current_user)) -> dict[str, Any]:
        svc.delete_record(uid, record_id)
        return {"ok": True}

    @app.get("/api/returns/half-return")
    def half_return(amount: int, purpose: str, uid: str = Depends(current_user)) -> dict[str, Any]:
        if amount <= 0:
            raise HTTPException(status_code=422, detail="amount must be > 0")
        r = svc.half_return(amount, purpose)
        return {
            "recommended": r.recommended,
            "low": r.low,
            "high": r.high,
            "ratio": r.ratio,
            "rationale": r.rationale,
            "gift_unneeded": r.gift_unneeded,
        }

    @app.get("/api/events/{event_id}/suggestions")
    def suggestions(
        event_id: str,
        budget: int,
        relationship: str = "",
        purpose: str = "",
        category: str = "",
        uid: str = Depends(current_user),
    ) -> dict[str, Any]:
        return svc.returns_payload(uid, event_id, budget, relationship, purpose, category or None)

    @app.post("/api/events/{event_id}/suggestion")
    def select_suggestion(
        event_id: str, body: SelectSuggestionIn, uid: str = Depends(current_user)
    ) -> dict[str, Any]:
        sug = svc.select_suggestion(uid, event_id, body.model_dump())
        return {"suggestion": vars(sug)}

    @app.post("/api/suggestions/click", status_code=204)
    def suggestion_click(body: SuggestionClickIn, uid: str = Depends(current_user)) -> Response:
        # 計測はUXをブロックしない（失敗してもエラーを返さない）
        try:
            svc.log_suggestion_click(
                uid, body.item_code, body.bucket, body.position, body.rel_group
            )
        except Exception:  # noqa: BLE001
            import logging

            logging.getLogger("noshi").exception("click logging failed")
        return Response(status_code=204)

    @app.patch("/api/events/{event_id}")
    def set_status(
        event_id: str, body: StatusIn, uid: str = Depends(current_user)
    ) -> dict[str, Any]:
        svc.set_event_status(uid, event_id, body.status)
        return {"event": svc.event_view(uid, event_id)}

    @app.put("/api/events/{event_id}/due")
    def set_event_due(
        event_id: str, body: DueIn, uid: str = Depends(current_user)
    ) -> dict[str, Any]:
        # お返し期限の手動上書き/解除（#2）。本人スコープ＋監査。
        svc.set_event_due(uid, event_id, body.due_at)
        return {"event": svc.event_view(uid, event_id)}

    @app.get("/api/events/{event_id}")
    def get_event(event_id: str, uid: str = Depends(current_user)) -> dict[str, Any]:
        return {"event": svc.event_view(uid, event_id)}

    @app.get("/api/records/{record_id}/event")
    def event_for_record(record_id: str, uid: str = Depends(current_user)) -> dict[str, Any]:
        # #48: given でもエラーにせず記録ベースの詳細を返す（あげた記録もタップして開ける）。
        return {"event": svc.record_detail(uid, record_id)}

    return app


app = create_app()
