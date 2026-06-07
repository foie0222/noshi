"""noshi BFF/API（FastAPI）。

api-contracts.md の論理 API を実装。スタブ認証（X-User-Id）で本人スコープを確立し、
NoshiService に委譲。エラーは汎用文言で返し内部情報を漏らさない（A03）。
DI で Repository/ポートを差し替え可能（MVP は InMemory + モック）。
"""
from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.ports import OcrLlmMock, GiftCatalogMock
from app.repository import InMemoryRepository
from app.services import NoshiService, ForbiddenError, ValidationError
from app.auth import Identity
from app.schemas import (
    RecordIn, RecordUpdateIn, StatusIn, SelectSuggestionIn, LetterIn, CaptureIn, JoinHouseholdIn,
)


def _default_ocr():
    """OCR/LLM の実装を選ぶ。NOSHI_USE_BEDROCK=1 で本物(Bedrock/Claude)、既定はモック。"""
    import os
    if os.environ.get("NOSHI_USE_BEDROCK") == "1":
        from app.adapters import BedrockOcrLlm
        return BedrockOcrLlm()
    return OcrLlmMock()


def _default_repository():
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
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
    )
    svc = service or NoshiService(_default_repository(), _default_ocr(), GiftCatalogMock())

    def current_identity(
        authorization: str | None = Header(default=None),
        x_user_id: str | None = Header(default=None),
    ) -> Identity:
        # JWT 構成済み(Cognito/HS256)なら Bearer トークンを検証。未構成なら
        # 開発用 X-User-Id スタブにフォールバック。どちらも無ければ 401（A07）。
        from app.auth import auth_configured, decode_identity, AuthError
        if auth_configured() and authorization:
            token = authorization[7:] if authorization.lower().startswith("bearer ") else authorization
            try:
                return decode_identity(token)
            except AuthError:
                raise HTTPException(status_code=401, detail="authentication required")
        if x_user_id:
            return Identity(user_id=x_user_id)
        raise HTTPException(status_code=401, detail="authentication required")

    def current_user(ident: Identity = Depends(current_identity)) -> str:
        return ident.user_id

    @app.exception_handler(ForbiddenError)
    async def _forbidden(_req, _exc):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=403, content={"detail": "forbidden"})

    @app.exception_handler(ValidationError)
    async def _validation(_req, exc: ValidationError):
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=422, content={"detail": exc.errors})

    @app.get("/api/health")
    def health():
        return {"status": "ok"}

    @app.get("/api/household")
    def household(ident: Identity = Depends(current_identity)):
        # 自分の世帯（名前・招待コード・メンバー）。初回は自動作成される。
        svc.resolve_household(ident.user_id, email=ident.email)
        return {"household": svc.household_view(ident.user_id)}

    @app.post("/api/household/join")
    def join_household(body: JoinHouseholdIn, ident: Identity = Depends(current_identity)):
        # 招待コードで家族の世帯に参加（以後その世帯の台帳を共有）。
        svc.join_household(ident.user_id, body.code, email=ident.email)
        return {"household": svc.household_view(ident.user_id)}

    @app.get("/api/home")
    def home(uid: str = Depends(current_user)):
        # P0-3: 収支・差分は見せない。主役はお返し期限（pending: 期限つき・残日数昇順）。
        records = svc.list_records(uid)
        return {
            "pending": svc.pending_views(uid),
            "recent": [vars(r) for r in records[-5:]],
        }

    @app.post("/api/capture")
    def capture(body: CaptureIn | None = None, uid: str = Depends(current_user)):
        # 画像があれば抽出器（モック or Bedrock）へ渡す。無ければモック用のダミー参照。
        image_refs = [body.image] if (body and body.image) else ["mock.jpg"]
        try:
            job = svc.submit_extraction(uid, image_refs)
        except Exception as exc:  # 抽出失敗は握り潰さず 502 で返す（モックへ無言降格しない）
            import logging
            logging.getLogger("noshi").exception("extraction failed")
            raise HTTPException(status_code=502, detail="画像の読み取りに失敗しました。時間をおいて再度お試しください。") from exc
        return {"job_id": job.id, "status": job.status,
                "candidates": job.candidates, "confidence": job.confidence,
                "field_confidence": job.field_confidence,
                "field_review": svc.field_review(job),  # 項目別 要確認（P0-2）
                "needs_review": svc.extraction_needs_review(job)}

    @app.post("/api/records")
    def create_record(body: RecordIn, uid: str = Depends(current_user)):
        rec, ev = svc.create_record(
            uid, amount=body.amount, purpose=body.purpose, party_name=body.party_name,
            direction=body.direction, occurred_at=body.occurred_at, relationship=body.relationship)
        # given はお返しイベントを持たない（ev is None）。安全に null を返す（FR-8-1）。
        return {"record": vars(rec), "event": vars(ev) if ev is not None else None}

    @app.get("/api/relationships")
    def relationships(uid: str = Depends(current_user)):
        # N1: 相手別おつきあいバランス（本人データのみ）。
        return {"relationships": svc.relationships(uid)}

    @app.get("/api/gift-tax")
    def gift_tax(uid: str = Depends(current_user)):
        # P1-3: 暦年の対象もらった合計と110万枠の気づき（税アドバイスではない）。
        return svc.gift_tax(uid)

    @app.get("/api/annual")
    def annual(year: int | None = None, uid: str = Depends(current_user)):
        # 年間振り返り（本人の受領/あげた件数・合計・相手人数）。
        return svc.annual_summary(uid, year)

    @app.get("/api/ledger")
    def ledger(uid: str = Depends(current_user)):
        return {"records": [vars(r) for r in svc.list_records(uid)],
                "party_summary": svc.party_summary(uid)}

    @app.patch("/api/records/{record_id}")
    def update_record(record_id: str, body: RecordUpdateIn, uid: str = Depends(current_user)):
        # AI抽出の誤りを本人が訂正（本人スコープ＋監査）。direction は変更しない。
        # None のフィールドは渡さない＝既存値を保持（金額のみ修正で日付が消えないように）。
        extra = {k: v for k, v in (("occurred_at", body.occurred_at),
                                   ("relationship", body.relationship)) if v is not None}
        rec = svc.update_record(
            uid, record_id, amount=body.amount, purpose=body.purpose,
            party_name=body.party_name, **extra)
        return {"record": vars(rec)}

    @app.delete("/api/records/{record_id}")
    def delete_record(record_id: str, uid: str = Depends(current_user)):
        svc.delete_record(uid, record_id)
        return {"ok": True}

    @app.get("/api/returns/half-return")
    def half_return(amount: int, purpose: str, uid: str = Depends(current_user)):
        if amount <= 0:
            raise HTTPException(status_code=422, detail="amount must be > 0")
        r = svc.half_return(amount, purpose)
        return {"recommended": r.recommended, "low": r.low, "high": r.high,
                "ratio": r.ratio, "rationale": r.rationale, "gift_unneeded": r.gift_unneeded}

    @app.get("/api/events/{event_id}/suggestions")
    def suggestions(event_id: str, budget: int, relationship: str = "", purpose: str = "",
                    uid: str = Depends(current_user)):
        return {"suggestions": svc.suggest_returns(uid, event_id, budget, relationship, purpose)}

    @app.post("/api/events/{event_id}/suggestion")
    def select_suggestion(event_id: str, body: SelectSuggestionIn, uid: str = Depends(current_user)):
        sug = svc.select_suggestion(uid, event_id, body.model_dump())
        return {"suggestion": vars(sug)}

    @app.post("/api/events/{event_id}/letter")
    def letter(event_id: str, body: LetterIn, uid: str = Depends(current_user)):
        lt = svc.generate_letter(uid, event_id, body.purpose, body.relationship, body.tone)
        return {"letter": vars(lt)}

    @app.patch("/api/events/{event_id}")
    def set_status(event_id: str, body: StatusIn, uid: str = Depends(current_user)):
        svc.set_event_status(uid, event_id, body.status)
        return {"event": svc.event_view(uid, event_id)}

    @app.get("/api/events/{event_id}")
    def get_event(event_id: str, uid: str = Depends(current_user)):
        return {"event": svc.event_view(uid, event_id)}

    @app.get("/api/records/{record_id}/event")
    def event_for_record(record_id: str, uid: str = Depends(current_user)):
        ev = svc.event_for_record(uid, record_id)
        if ev is None:
            raise HTTPException(status_code=404, detail="not found")
        return {"event": svc.event_view(uid, ev.id)}

    return app


app = create_app()
