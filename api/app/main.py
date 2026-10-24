"""Shoebox API: receipt in, categorized expense out."""
from __future__ import annotations

import hashlib
import hmac
import os
import time
from typing import Any, Callable, Optional

from fastapi import FastAPI, File, Header, HTTPException, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from .extract import SUPPORTED_TYPES, ExtractionError, extract_receipt
from .ratelimit import RateLimiter
from .schemas import SCHEDULE_C_LINE, Receipt, deductible_estimate
from .store import ALLOWED_EVENTS, Store

MAX_BYTES = 6 * 1024 * 1024
CLIENT_EVENTS = ALLOWED_EVENTS - {"parse", "parse_error"}  # those are logged server-side only


class EventIn(BaseModel):
    event: str
    meta: dict[str, Any] = Field(default_factory=dict)


def _client_id(x_client_id: Optional[str], request: Request) -> str:
    cid = (x_client_id or "").strip()[:64]
    if cid:
        return cid
    ip = request.headers.get("x-forwarded-for", request.client.host if request.client else "?")
    return "ip-" + hashlib.sha256(ip.split(",")[0].encode()).hexdigest()[:16]


def create_app(
    extractor: Callable[[bytes, str], Receipt] = extract_receipt,
    db_path: Optional[str] = None,
) -> FastAPI:
    if os.getenv("DEMO_MODE") == "1" and extractor is extract_receipt:
        from .demo import demo_extractor

        extractor = demo_extractor
    app = FastAPI(title="Shoebox API", version="1.0.0")
    origins = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:3000").split(",") if o.strip()]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Content-Type", "X-Client-Id", "Authorization"],
    )
    store = Store(db_path or os.getenv("DB_PATH", "data/shoebox.db"))
    limiter = RateLimiter(
        per_client_per_hour=int(os.getenv("RATE_LIMIT_PER_HOUR", "40")),
        daily_cap=int(os.getenv("MAX_DAILY_PARSES", "500")),
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/api/parse")
    async def parse(
        request: Request,
        file: UploadFile = File(...),
        x_client_id: Optional[str] = Header(default=None),
    ) -> dict[str, Any]:
        cid = _client_id(x_client_id, request)
        media_type = (file.content_type or "").lower()
        if media_type == "image/jpg":
            media_type = "image/jpeg"
        if media_type not in SUPPORTED_TYPES:
            raise HTTPException(415, "Please upload a JPG, PNG, WEBP, GIF or PDF.")
        data = await file.read(MAX_BYTES + 1)
        if not data:
            raise HTTPException(400, "That file is empty.")
        if len(data) > MAX_BYTES:
            raise HTTPException(413, "File is too large (max 6 MB).")
        ok, reason = limiter.allow(cid)
        if not ok:
            raise HTTPException(429, reason)

        started = time.perf_counter()
        try:
            receipt = await run_in_threadpool(extractor, data, media_type)
        except ExtractionError as e:
            store.log(cid, "parse_error", {"error": str(e)[:200]})
            raise HTTPException(502, "Couldn't read that receipt. Try a clearer photo.") from e
        ms = int((time.perf_counter() - started) * 1000)
        store.log(cid, "parse", {"category": receipt.category, "ms": ms, "type": media_type})
        return {
            "receipt": receipt.model_dump(),
            "schedule_c_line": SCHEDULE_C_LINE.get(receipt.category, ""),
            "deductible_estimate": deductible_estimate(receipt),
            "latency_ms": ms,
        }

    @app.post("/api/events", status_code=204)
    def events(body: EventIn, request: Request, x_client_id: Optional[str] = Header(default=None)) -> None:
        if body.event not in CLIENT_EVENTS:
            raise HTTPException(400, "Unknown event")
        store.log(_client_id(x_client_id, request), body.event, body.meta)

    @app.get("/api/stats")
    def stats(authorization: Optional[str] = Header(default=None)) -> dict[str, Any]:
        token = os.getenv("ADMIN_TOKEN", "")
        given = (authorization or "").removeprefix("Bearer ").strip()
        if not token or not hmac.compare_digest(given, token):
            raise HTTPException(401, "Unauthorized")
        return store.stats()

    return app


app = create_app()
