"""CLOUD AI TRADER — FastAPI entrypoint.

Run:  uvicorn app.main:app --host 0.0.0.0 --port 8000
"""
from __future__ import annotations

import asyncio
import datetime
import logging
import zoneinfo
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .api.routes import auth_router, router
from .config import settings
from .core.state import state
from .services.market_service import service
from .ws.manager import manager

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")
log = logging.getLogger("nightly")


async def _nightly_audit_loop():
    """Phase 23 — run the self-tuning audit every day at 23:59 IST. Reads stored
    outcomes only (no broker), archives the report, caches it. Recommendations
    only — never auto-applies anything to the live trading gate."""
    ist = zoneinfo.ZoneInfo("Asia/Kolkata")
    while True:
        now = datetime.datetime.now(ist)
        target = now.replace(hour=23, minute=59, second=0, microsecond=0)
        if target <= now:
            target += datetime.timedelta(days=1)
        await asyncio.sleep(max(60, (target - now).total_seconds()))
        try:
            from .services import evolution
            rep = evolution.run_nightly()
            log.info("nightly audit complete — grade %s, %d settled",
                     rep.get("system_grade"), rep.get("overview", {}).get("settled", 0))
        except Exception:
            log.exception("nightly audit failed")
        # V31.1 — nightly KNOWLEDGE refresh (historical learning; broker calls
        # only when connected; knowledge stays separate from live validation)
        try:
            from .core.state import state as _st
            from .services.market_service import service as _svc
            if _st.connected and _svc.client:
                from .services import historical_learning
                hl = await historical_learning.run(_svc.client)
                log.info("nightly historical learning refreshed — %s sessions",
                         hl.get("days_analysed"))
        except Exception:
            log.exception("nightly historical learning failed")


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Deliberately idle on boot: engines start only after SAVE & CONNECT.
    # Phase 19 — restore self-learning memory (outcomes, calibration, engine
    # reliability) from Supabase if configured, so learning survives restarts.
    try:
        from .services import memory, weight_approval, missed_winner, verdicts
        memory.rehydrate()
        weight_approval.rehydrate()   # Phase 22 — restore human-approved weights
        missed_winner.rehydrate()     # V1.0 — restore gate-calibration evidence
        verdicts.rehydrate()          # RC1.5 — Gate Efficiency survives restarts
        from .services import global_feed
        global_feed.rehydrate_overnight()   # RC1.9 — morning bias handoff
        global_feed.rehydrate_accuracy()    # RC1.10 — Layer-4 prediction accuracy
    except Exception:
        pass
    # Phase 23 — always-on nightly self-tuning audit (independent of broker).
    nightly_task = asyncio.create_task(_nightly_audit_loop())
    yield
    nightly_task.cancel()
    await service.stop()


app = FastAPI(title="Cloud AI Trader", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_origin] if settings.frontend_origin != "*" else ["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth_router)
app.include_router(router)


@app.get("/health")
async def health():
    return {"ok": True, "connected": state.connected}


@app.websocket("/ws")
async def ws_endpoint(ws: WebSocket):
    await manager.connect(ws)
    try:
        await ws.send_json({"channel": "status", "data": state.status()})
        while True:
            await ws.receive_text()  # keepalive pings from the client
    except WebSocketDisconnect:
        manager.disconnect(ws)
