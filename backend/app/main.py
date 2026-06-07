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
from app.schemas import RecordIn, StatusIn, SelectSuggestionIn, LetterIn


def create_app(service: NoshiService | None = None) -> FastAPI:
    app = FastAPI(title="noshi API", version="0.1.0")
    app.add_middleware(
        CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
    )
    svc = service or NoshiService(InMemoryRepository(), OcrLlmMock(), GiftCatalogMock())

    def current_user(x_user_id: str | None = Header(default=None)) -> str:
        # スタブ認証: 本番は OIDC トークン検証に置換。未提示は 401（A07）。
        if not x_user_id:
            raise HTTPException(status_code=401, detail="authentication required")
        return x_user_id

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

    @app.get("/api/home")
    def home(uid: str = Depends(current_user)):
        # P0-3: 収支・差分は見せない。主役はお返し期限（pending: 期限つき・残日数昇順）。
        records = svc.list_records(uid)
        return {
            "pending": svc.pending_views(uid),
            "recent": [vars(r) for r in records[-5:]],
        }

    @app.post("/api/capture")
    def capture(uid: str = Depends(current_user)):
        job = svc.submit_extraction(uid, ["mock.jpg"])
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
        return {"record": vars(rec), "event": vars(ev)}

    @app.get("/api/relationships")
    def relationships(uid: str = Depends(current_user)):
        # N1: 相手別おつきあいバランス（本人データのみ）。
        return {"relationships": svc.relationships(uid)}

    @app.get("/api/gift-tax")
    def gift_tax(uid: str = Depends(current_user)):
        # P1-3: 暦年の対象もらった合計と110万枠の気づき（税アドバイスではない）。
        return svc.gift_tax(uid)

    @app.get("/api/ledger")
    def ledger(uid: str = Depends(current_user)):
        return {"records": [vars(r) for r in svc.list_records(uid)],
                "party_summary": svc.party_summary(uid)}

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
