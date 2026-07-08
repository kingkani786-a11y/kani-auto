"""REST API. Every market endpoint refuses to answer until connected."""
from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import pathlib
import time

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field

from ..broker.dhan import BrokerError, RateLimitError
from ..broker.instruments import INSTRUMENTS, get_instrument, register_stock
from ..config import settings
from ..core.state import state
from ..services import journal
from ..services.market_service import service


# ---------- secure login (active only when CAT_APP_PASSWORD is set) ----------
def _session_token() -> str:
    return hmac.new(settings.app_password.encode(), b"cat-x-session", hashlib.sha256).hexdigest()


async def require_auth(x_auth_token: str | None = Header(default=None)):
    if settings.app_password and x_auth_token != _session_token():
        raise HTTPException(401, "Login required")


router = APIRouter(prefix="/api", dependencies=[Depends(require_auth)])
auth_router = APIRouter(prefix="/api/auth")


class LoginBody(BaseModel):
    password: str


@auth_router.get("/check")
async def auth_check():
    return {"login_required": bool(settings.app_password)}


@auth_router.post("/login")
async def login(body: LoginBody):
    if not settings.app_password:
        return {"token": "", "login_required": False}
    if not hmac.compare_digest(body.password, settings.app_password):
        raise HTTPException(401, "Wrong password")
    return {"token": _session_token(), "login_required": True}


# ---------- watchlist persistence (file-backed, survives restarts) ----------
_WL_FILE = pathlib.Path(__file__).resolve().parents[2] / "data" / "watchlist.json"


def _load_watchlist() -> None:
    try:
        d = json.loads(_WL_FILE.read_text())
        state.watchlist = d.get("watchlist", [])
        state.favorites = d.get("favorites", [])
        for s in d.get("stocks", []):
            register_stock(s["symbol"], s["security_id"], s["exchange"])
    except FileNotFoundError:
        pass
    except Exception:
        pass


def _save_watchlist() -> None:
    from ..broker.instruments import DYNAMIC
    _WL_FILE.parent.mkdir(exist_ok=True)
    _WL_FILE.write_text(json.dumps({
        "watchlist": state.watchlist,
        "favorites": state.favorites,
        "stocks": [{"symbol": i.symbol, "security_id": i.security_id,
                    "exchange": "NSE" if i.segment == "NSE_EQ" else "BSE"}
                   for i in DYNAMIC.values()],
    }))


_load_watchlist()


def _require_connection() -> None:
    if not state.connected:
        raise HTTPException(409, "Not connected. Save credentials in Settings first.")


# ---------- settings / auth ----------
class ConnectBody(BaseModel):
    client_id: str = Field(min_length=3)
    access_token: str = Field(min_length=20)


@router.post("/settings/connect")
async def connect(body: ConnectBody):
    """SAVE & CONNECT: validate -> connect -> start every engine."""
    try:
        await service.connect(body.client_id.strip(), body.access_token.strip())
    except BrokerError as e:
        raise HTTPException(401, str(e))
    return {"ok": True, "status": state.status()}


@router.post("/settings/disconnect")
async def disconnect():
    await service.stop()
    return {"ok": True}


@router.get("/settings")
async def get_settings():
    """Never returns the token itself — only its shape, for the UI."""
    c = state.credentials
    return {
        "client_id": c.client_id,
        "token_set": bool(c.access_token),
        "token_tail": c.access_token[-4:] if c.access_token else "",
        "confidence_threshold": settings.confidence_threshold,
    }


class ThresholdBody(BaseModel):
    confidence_threshold: float = Field(ge=50, le=95)


@router.put("/settings/threshold")
async def set_threshold(body: ThresholdBody):
    settings.confidence_threshold = body.confidence_threshold
    return {"ok": True, "confidence_threshold": settings.confidence_threshold}


# ---------- status / market ----------
@router.get("/status")
async def status():
    return state.status()


@router.get("/symbols")
async def symbols():
    return [
        {"symbol": i.symbol, "market_type": i.market_type, "tv_symbol": i.tv_symbol}
        for i in INSTRUMENTS.values()
    ]


class SymbolBody(BaseModel):
    symbol: str


@router.post("/symbol")
async def set_symbol(body: SymbolBody):
    _require_connection()
    try:
        get_instrument(body.symbol)
    except ValueError as e:
        raise HTTPException(400, str(e))
    await service.set_symbol(body.symbol)
    return {"ok": True, "status": state.status()}


@router.get("/market/overview")
async def overview():
    _require_connection()
    return {
        "status": state.status(),
        "spot": state.spot,
        "analytics": {k: v for k, v in state.analytics.items() if k != "chain"},
        "greeks": state.greeks,
        "smart_money": state.smart_money,
        "signal": state.signal,
        "decision": state.decision,
        "risk": state.risk,
    }


@router.get("/market/optionchain")
async def option_chain():
    _require_connection()
    return state.option_chain


@router.get("/market/candles")
async def candles():
    _require_connection()
    return state.candles


@router.get("/signal/latest")
async def latest_signal():
    _require_connection()
    return {"signal": state.signal, "risk": state.risk}


@router.get("/addon/insights")
async def addon_insights():
    """ADD-ON advisory layer — strict JSON contract, read-only. Supplements
    the dashboard; never replaces existing outputs. Always returns valid JSON
    (empty/zero-confidence when there's no data) so it can never break a panel."""
    from ..engines import addon_flow
    from ..services import scanner
    tech = (state.intelligence.get("signal", {}) or {}).get("tech", {}) \
        or (state.signal.get("tech", {}) if state.signal else {})
    try:
        return addon_flow.compute(state.symbol, state.analytics, tech, scanner.results)
    except Exception:
        return addon_flow.EMPTY


@router.get("/intelligence")
async def intelligence():
    """Full Cloud AI Trader X packet: 10 layers, strike, warning, narrative."""
    _require_connection()
    return state.intelligence


@router.get("/lifecycle")
async def lifecycle():
    _require_connection()
    return service.lifecycle.snapshot()


class BrainBody(BaseModel):
    question: str


@router.post("/brain")
async def ai_market_brain(body: BrainBody):
    """AI Market Brain — natural-language Q&A over existing state (no new data)."""
    from ..services import brain
    return brain.answer(body.question)


@router.get("/brain/auto")
async def ai_brain_auto():
    """S14 — auto-answered key questions (the AI answers before you ask)."""
    from ..services import brain
    return brain.auto_brief()


@router.get("/strategist")
async def ai_chief_strategist():
    """Phase 25 — AI Chief Strategist: a single structured decision card +
    permanent questions answered, all derived from existing engine state."""
    from ..services import brain
    return brain.chief_strategist()


@router.get("/evolution")
async def evolution_center(period: str = "weekly"):
    """Phase 21 — Evolution Center: self-analysis report (daily/weekly/monthly)
    over the platform's own measured outcomes. Advisory; never auto-applied."""
    from ..services import evolution
    if period not in ("daily", "weekly", "monthly"):
        period = "weekly"
    return evolution.report(period)


@router.get("/simulator")
async def today_tomorrow_simulator():
    """Phase 29 — today/tomorrow scenario simulator (derivation-only)."""
    return state.simulator or {"ready": False, "note": "No live analysis yet."}


@router.get("/professor")
async def options_professor():
    """Phase 30 — Options Professor: plain-language 'why' for the current trade."""
    return (state.decision or {}).get("options_professor") or {"ready": False,
            "note": "No live analysis yet."}


@router.get("/safemode")
async def safe_mode_status():
    """Phase D — Disaster Recovery / Safe Mode status + recent incidents."""
    from ..services import safe_mode
    return {**(state.safe_mode or {"active": False, "triggers": []}),
            "incidents": safe_mode.incidents()}


@router.get("/validate")
async def system_validation():
    """Phase F — lightweight module validation (PASS/WARNING/FAIL) from live state."""
    dec = state.decision or {}
    conn = state.connected
    # When disconnected, modules that need a live cycle are idle-by-design →
    # WARNING, not FAIL (they populate on connect).
    def chk(ok: bool, needs_live: bool = False):
        if ok:
            return "PASS"
        return "WARNING" if (needs_live or not conn) else "FAIL"
    results = {
        "Dashboard": chk(True),
        "Strategist": chk(bool(dec), needs_live=True),
        "DNA": chk((state.market_dna or {}).get("ready", False), needs_live=True),
        "Evolution": chk(True),
        "Audit": chk(True),
        "Simulator": chk((state.simulator or {}).get("ready", False), needs_live=True),
        "Probability Ladder": chk(bool(dec.get("probability_ladder", {}).get("ready")), needs_live=True),
        "Premium Forecast": chk(bool(dec.get("premium_forecast", {}).get("ready")), needs_live=True),
        "Entry Zone": chk(bool(dec.get("entry_zone", {}).get("ready")), needs_live=True),
        "Kill Switch": chk(bool(state.kill_switch), needs_live=True),
        "Safe Mode": chk(bool(state.safe_mode), needs_live=True),
    }
    npass = sum(1 for v in results.values() if v == "PASS")
    nwarn = sum(1 for v in results.values() if v == "WARNING")
    return {"results": results, "pass": npass, "warning": nwarn,
            "fail": len(results) - npass - nwarn, "total": len(results),
            "connected": conn,
            "note": "WARNING = built but idle (needs live connect/data), not a failure."}


@router.get("/health/persistence")
async def health_persistence():
    """Phase 19 — real Supabase persistence status + activation steps."""
    from ..services import persistence
    return persistence.status()


@router.get("/health/center")
async def health_center():
    """System Health Center — composite A+…D score across all subsystems."""
    from ..services import health_center
    return health_center.score()


@router.get("/research")
async def research_lab_report():
    """Phase 31 — Autonomous Research Lab: live self-diagnosis + prioritised findings."""
    from ..services import research_lab
    return research_lab.report()


@router.get("/execution-card")
async def execution_card_status():
    """V24.5 — one actionable instruction + dual-mode opportunity radar."""
    return (state.decision or {}).get("execution_card") or {"ready": False,
            "note": "No live analysis yet."}


@router.get("/execution-gate")
async def execution_gate_status():
    """Section 24 — final execution gate verdict + mandatory conditions."""
    return (state.decision or {}).get("execution_gate") or {"ready": False,
            "note": "No live analysis yet."}


@router.get("/market-path")
async def market_path_status():
    """AI Market Path Predictor — bias, next touch + ETA, targets, scenarios, NL."""
    return (state.decision or {}).get("market_path") or {"ready": False, "note": "No live analysis yet."}


@router.get("/projection")
async def candle_projection_status():
    """Layer 6 — forward-only probability candle projection (no repaint)."""
    return (state.decision or {}).get("candle_projection") or {"ready": False,
            "note": "No live analysis yet."}


@router.get("/alpha")
async def alpha_status():
    """V29 — alpha score + opportunity queue + entry timing + confidence dist."""
    return (state.decision or {}).get("alpha") or {"ready": False, "note": "No live analysis yet."}


@router.get("/market-clock")
async def market_clock_status():
    """V28 §6 — AI market clock: current session phase + timeline."""
    from ..engines import market_clock
    return market_clock.now_phase(state.market_type)


@router.get("/report-card")
async def ai_report_card():
    """V27 §1 — consolidated AI accuracy report card (measured outcomes only)."""
    from ..services import validation
    return validation.report_card()


@router.get("/daily-review")
async def daily_review():
    """Market-closed Daily Review / learning summary."""
    from ..services import validation
    return validation.daily_review()


@router.get("/gamma-shield")
async def gamma_shield_status():
    """V8 §8 — advisory gamma-spike protection state."""
    return (state.decision or {}).get("gamma_shield") or {"ready": False, "note": "No live analysis yet."}


@router.get("/missed-winners")
async def missed_winners():
    """Evidence layer — winners the gate blocked, attributed by blocking reason."""
    from ..services import missed_winner
    return missed_winner.summary()


@router.get("/entry-score")
async def entry_score_timeline_status():
    """V26 §1 — entry/fire score over time (strengthening / fading / ENTRY NOW)."""
    return (state.decision or {}).get("entry_score_timeline") or {"ready": False,
            "note": "No live analysis yet."}


@router.get("/confidence")
async def confidence_evolution_status():
    """Module 9 — confidence evolution timeline + layer attribution."""
    return (state.decision or {}).get("confidence_evolution") or {"ready": False,
            "note": "No live analysis yet."}


@router.get("/checklist")
async def entry_checklist_status():
    """Phase 2/3/8 — live entry checklist + fire score + why-not reasons."""
    return (state.decision or {}).get("entry_checklist") or {"ready": False,
            "note": "No live analysis yet."}


@router.get("/maturity")
async def signal_maturity_status():
    """Phase 7/6 — signal maturity + entry-trigger state for the current setup."""
    return (state.decision or {}).get("signal_maturity") or {"ready": False,
            "note": "No live analysis yet."}


@router.get("/decision")
async def decision_intelligence():
    """Phase 1/5/13 — one synthesised institutional decision + trade-quality +
    governance, derived from existing engines."""
    return (state.decision or {}).get("intelligence_synthesis") or {"ready": False,
            "note": "No live analysis yet."}


@router.get("/roadmap")
async def system_roadmap():
    """v6 — build progress: completed / pending / blocked phases + completion %."""
    from ..services import evolution
    return evolution.roadmap()


@router.get("/evolution/nightly")
async def evolution_nightly():
    """Phase 23 — the most recent nightly self-tuning audit (recommendations
    only; nothing auto-applied). Runs automatically at 23:59 IST."""
    from ..services import evolution
    return evolution.last_nightly()


@router.post("/evolution/run-nightly")
async def evolution_run_nightly():
    """Phase 23 — trigger the nightly audit on demand (human-initiated).
    Generates + archives the report; still applies nothing automatically."""
    from ..services import evolution
    return evolution.run_nightly()


@router.get("/weights")
async def weights_status():
    """Phase 22 — weight approval queue + applied weights + effective gate."""
    from ..services import weight_approval
    return weight_approval.status()


class WeightBody(BaseModel):
    weight_key: str


@router.post("/weights/queue")
async def weights_queue():
    """Build the approval queue from current engine reliability (evidence-gated)."""
    from ..services import weight_approval
    return weight_approval.build_queue()


@router.post("/weights/approve")
async def weights_approve(body: WeightBody):
    from ..services import weight_approval
    return weight_approval.approve(body.weight_key)


@router.post("/weights/simulate")
async def weights_simulate(body: WeightBody):
    from ..services import weight_approval
    return weight_approval.simulate(body.weight_key)


@router.post("/weights/apply")
async def weights_apply(body: WeightBody):
    from ..services import weight_approval
    return weight_approval.apply(body.weight_key)


@router.post("/weights/reject")
async def weights_reject(body: WeightBody):
    from ..services import weight_approval
    return weight_approval.reject(body.weight_key)


@router.post("/weights/revert")
async def weights_revert(body: WeightBody):
    from ..services import weight_approval
    return weight_approval.revert(body.weight_key)


@router.get("/dna")
async def market_dna_report():
    """Phase 20 — Market DNA: current setup matched against stored historical
    outcomes. Returns 'Insufficient DNA' until ≥10 comparable sessions exist."""
    return state.market_dna or {"status": "INSUFFICIENT_DNA", "ready": False,
                                "note": "No live analysis yet — connect and let the AI cycle run."}


@router.get("/future")
async def future_intelligence():
    """Forward Intelligence — scenarios, next-move probability, ETAs, war room."""
    return (state.intelligence.get("layers", {}) or {}).get("future", {})


@router.get("/exit")
async def exit_intelligence():
    """Exit Intelligence + trade management for the active trade (derivation-only)."""
    return state.exit_intel or {"active": False}


@router.get("/scalp")
async def scalp_radar():
    """Scalp Radar V3 — independent execution intelligence (separate from main)."""
    from ..services import scalp_state
    base = state.scalp or {"active": False, "scalp_score": 0, "direction": "NONE"}
    return {**base, "management": scalp_state.status(), "analytics": scalp_state.analytics()}


@router.get("/decision")
async def decision():
    """V10 ultra-simple decision view — the 3-second trader summary."""
    _require_connection()
    return state.decision


# (symbol, tf) -> (fetched_at, candles); fast switching without re-hitting broker
_candle_cache: dict[tuple[str, str], tuple[float, list]] = {}


@router.get("/market/candles/{tf}")
async def candles_tf(tf: str, symbol: str | None = None):
    """Validated, cached, retried OHLCV history for any supported symbol.
    Timeframes: 1m,3m,5m,15m,30m,1H,4H,1D — min 500 candles where history allows."""
    _require_connection()
    sym = (symbol or state.symbol).upper()
    try:
        inst = get_instrument(sym)
    except ValueError:
        raise HTTPException(400, "Invalid Symbol")
    if tf not in ("1s", "1m", "3m", "5m", "15m", "30m", "1H", "4H", "1D"):
        raise HTTPException(400, f"Invalid timeframe: {tf}")
    # Broker history is 1-minute minimum; 1s seeds from 1m and refines live.
    fetch_tf = "1m" if tf == "1s" else tf

    key, now = (sym, tf), time.time()
    cached = _candle_cache.get(key)
    ttl = 15.0 if tf in ("1m", "3m") else 60.0
    if cached and now - cached[0] < ttl:
        return cached[1]

    last_err: Exception | None = None
    for attempt in range(3):                      # retry transient broker failures
        try:
            candles = await service.client.get_tf_candles(inst, fetch_tf)
        except RateLimitError as e:
            if cached:
                return cached[1]                  # serve stale during cooldown
            raise HTTPException(429, str(e))      # never retry into a rate limit
        except BrokerError as e:
            last_err = e
            await asyncio.sleep(0.5 * (attempt + 1))
            continue
        # validate shape before the chart ever sees it
        candles = [c for c in candles
                   if all(isinstance(c.get(k), (int, float)) for k in ("time", "open", "high", "low", "close"))
                   and c["high"] >= c["low"] > 0]
        if not candles:
            raise HTTPException(404, "No Data Available")
        _candle_cache[key] = (now, candles)
        if len(_candle_cache) > 64:               # bound the cache
            _candle_cache.pop(next(iter(_candle_cache)))
        return candles
    if cached:
        return cached[1]                          # stale beats blank
    raise HTTPException(502, f"Chart data unavailable: {last_err}")


# ---------- stocks: search / watchlist / favorites ----------
@router.get("/stocks/search")
async def stock_search(q: str):
    _require_connection()
    if len(q.strip()) < 2:
        return []
    return service.client.search_stocks(q)


class StockBody(BaseModel):
    symbol: str
    security_id: int
    exchange: str = "NSE"


@router.post("/watchlist")
async def watchlist_add(body: StockBody):
    inst = register_stock(body.symbol, body.security_id, body.exchange)
    if inst.symbol not in state.watchlist:
        state.watchlist.append(inst.symbol)
    _save_watchlist()
    return {"ok": True, "watchlist": state.watchlist}


@router.delete("/watchlist/{symbol}")
async def watchlist_remove(symbol: str):
    s = symbol.upper()
    state.watchlist = [x for x in state.watchlist if x != s]
    state.favorites = [x for x in state.favorites if x != s]
    _save_watchlist()
    return {"ok": True, "watchlist": state.watchlist}


@router.get("/watchlist")
async def watchlist_get():
    from ..broker.instruments import DYNAMIC
    quotes = {}
    if state.connected and state.watchlist:
        ids = [DYNAMIC[s].security_id for s in state.watchlist if s in DYNAMIC]
        if ids:
            try:
                raw = await service.client.get_quotes_batch("NSE_EQ", ids)
                for s in state.watchlist:
                    inst = DYNAMIC.get(s)
                    if inst and str(inst.security_id) in raw:
                        q = raw[str(inst.security_id)]
                        o = (q.get("ohlc") or {}).get("open") or 0
                        ltp = float(q.get("last_price") or 0)
                        quotes[s] = {"ltp": ltp,
                                     "change_pct": round((ltp / o - 1) * 100, 2) if o else 0}
            except BrokerError:
                pass
    return {"watchlist": state.watchlist, "favorites": state.favorites, "quotes": quotes}


@router.post("/favorites/{symbol}")
async def favorite_toggle(symbol: str):
    s = symbol.upper()
    if s in state.favorites:
        state.favorites.remove(s)
    else:
        state.favorites.append(s)
    _save_watchlist()
    return {"favorites": state.favorites}


# ---------- scanner / alerts ----------
@router.get("/scanner")
async def scanner_results():
    from ..services import scanner
    return scanner.results


@router.get("/alerts")
async def alerts_feed():
    from ..services import alerts
    return alerts.feed()


class AlertConfigBody(BaseModel):
    telegram_bot_token: str = ""
    telegram_chat_id: str = ""
    smtp_host: str = ""
    smtp_port: str = "587"
    smtp_user: str = ""
    smtp_pass: str = ""
    email_to: str = ""


@router.put("/alerts/config")
async def alerts_config(body: AlertConfigBody):
    from ..services import alerts
    alerts.config.update({k: v for k, v in body.model_dump().items()})
    return {"ok": True,
            "telegram_enabled": bool(alerts.config["telegram_bot_token"]),
            "email_enabled": bool(alerts.config["smtp_host"])}


@router.post("/alerts/test")
async def alerts_test():
    from ..services import alerts
    return await alerts.send("SYSTEM", "Test alert", "Alert channels are working.", state.symbol)


# ---------- portfolio risk ----------
class RiskConfigBody(BaseModel):
    # RC1.4 sanity bounds — a ₹1-lakh-crore capital typo produced an
    # 82-lakh-lot position size on the dashboard. ₹10k … ₹100 crore.
    capital: float = Field(gt=9_999, le=1_000_000_000)
    risk_per_trade_pct: float = Field(gt=0.05, le=5)


@router.put("/portfolio/config")
async def portfolio_config(body: RiskConfigBody):
    settings.capital = body.capital
    settings.risk_per_trade_pct = body.risk_per_trade_pct
    return {"ok": True}


@router.get("/portfolio/risk")
async def portfolio_risk():
    from ..engines import portfolio_risk
    from ..services import paper
    pf = portfolio_risk.portfolio(paper.list_trades(), settings.capital, settings.risk_per_trade_pct)
    sizing = None
    sig = state.signal
    if sig and sig.get("signal") not in (None, "NO TRADE"):
        inst = get_instrument(state.symbol)
        sizing = portfolio_risk.position_size(
            settings.capital, settings.risk_per_trade_pct,
            sig["entry"], sig["stop_loss"], inst.lot_size)
        # ---- AI Execution Assistant (M9) ----
        prob = (state.intelligence.get("layers", {}).get("probability") or {})
        pos = float(prob.get("prob_success") or 50) / 100
        rr = float(sig.get("reward_risk") or 0)
        heat = float(pf.get("portfolio_heat_pct") or 0)
        suit = (float(sig.get("grade_score") or 0) * 0.5
                + pos * 100 * 0.3 + max(0, 100 - heat) * 0.2)
        sizing.update({
            "capital_allocation_pct": round(
                sizing["qty"] * sig["entry"] / settings.capital * 100, 1) if settings.capital else 0,
            "max_risk": round(settings.capital * settings.risk_per_trade_pct / 100, 0),
            "expected_drawdown": prob.get("expected_drawdown"),
            "risk_adjusted_reward": round(rr * pos, 2),
            "trade_suitability": round(min(suit, 100), 0),
            "suitability_note": ("Strong candidate" if suit >= 75 else
                                 "Acceptable with reduced size" if suit >= 60 else
                                 "Below suitability bar — consider skipping"),
        })
    return {**pf, "suggested_position": sizing}


@router.get("/health/system")
async def system_health():
    return service.health()


@router.get("/health/data")
async def data_health():
    """Data Quality Engine report: per-stream validation."""
    from ..services import data_quality
    return data_quality.report()


@router.get("/verdicts")
async def gate_verdicts():
    """V40.1/40.2 — blocked-decision verdicts + per-module gate efficiency."""
    from ..services import verdicts
    return verdicts.report()


@router.get("/historical-learning")
async def historical_learning_report():
    """V31 MODE-1 — historical KNOWLEDGE snapshot (separate from live validation)."""
    from ..services import historical_learning
    return historical_learning.report


@router.post("/historical-learning/run")
async def historical_learning_run():
    """Run the 3-year daily-setup backtest (5 broker calls, on demand)."""
    if not state.connected:
        raise HTTPException(409, "Not connected. Save credentials in Settings first.")
    from ..services import historical_learning
    return await historical_learning.run(service.client)


@router.get("/opportunities")
async def opportunities():
    """V26 — AI Market Opportunity Board (staged scan; cached, no extra calls)."""
    return state.opportunities or {"ready": False, "note": "First scan pending — connect during market hours."}


@router.get("/self-check")
async def self_check():
    """V23 — AI Self-Check: one consolidated startup/live readiness list across
    every subsystem, from state the platform already tracks. No fabrication —
    each row is a real reachability/freshness/heartbeat fact."""
    import time as _t
    from ..core.state import is_market_open
    from ..services import data_quality, persistence
    dq = data_quality.report()
    pz = persistence.status() if hasattr(persistence, "status") else {}
    closed = not is_market_open(state.market_type)
    checks: list[dict] = []

    def add(name: str, ok: bool | None, detail: str):
        checks.append({"name": name,
                       "status": "OK" if ok else "WAIT" if ok is None else "FAIL",
                       "detail": detail})

    from ..broker.dhan import DhanClient
    _cool = DhanClient.stats().get("cooldown_active", False)
    add("Broker", state.connected and not _cool,
        "rate-limit cooldown — data unreliable" if _cool
        else "connected" if state.connected else "not connected")
    # WS: a spot heartbeat within 15s means the live link is delivering.
    # When the market is closed, missing data is a PAUSE, not a failure.
    _hb = state.heartbeats or {}
    _spot_age = _t.time() - (state.spot.get("ts") or 0) if state.spot else 1e9
    add("WebSocket / Feed",
        None if closed else (state.connected and _spot_age < 15),
        "market closed — paused" if closed
        else f"{_spot_age:.0f}s since last tick" if state.connected else "idle")
    for key, label in (("quotes", "Quotes"), ("candles", "Candles"),
                       ("futures", "Futures"), ("option_chain", "Option Chain"),
                       ("greeks", "Greeks")):
        c = (dq.get("checks") or {}).get(key) or {}
        st = c.get("status")
        if st == "N/A":
            add(label, True, "n/a for this instrument")
        elif st != "OK" and closed:
            add(label, None, "market closed — resumes at open")
        else:
            add(label, st == "OK", c.get("detail") or (st or "").lower())
    add("AI Brain",
        None if closed or not state.connected
        else _t.time() - (_hb.get("signal_engine") or 0) < 420,
        "paused until market open" if closed
        else "cycling" if state.connected else "waiting for connect")
    add("Database / Memory", bool(pz.get("configured")),
        pz.get("database", "IN-MEMORY").lower() if pz else "in-memory")

    fails = [c for c in checks if c["status"] == "FAIL"]
    ready = state.connected and not fails and not closed
    return {"ready": ready, "checks": checks,
            "summary": "READY" if ready
            else "NOT CONNECTED" if not state.connected
            else "MARKET CLOSED — subsystems paused" if closed and not fails
            else f"{len(fails)} subsystem(s) need attention"}


# ---------- paper trading ----------
class PaperOpenBody(BaseModel):
    symbol: str
    side: str = Field(pattern="^(LONG|SHORT|long|short)$")
    qty: float = Field(gt=0)
    entry: float | None = None      # default: live spot
    stop_loss: float | None = None
    target: float | None = None


@router.get("/paper")
async def paper_list():
    from ..services import paper
    return {"stats": paper.stats(), "trades": paper.list_trades()}


@router.post("/paper/open")
async def paper_open(body: PaperOpenBody):
    _require_connection()
    from ..services import paper
    entry = body.entry or float(state.spot.get("ltp") or 0)
    if entry <= 0:
        raise HTTPException(400, "No live price available for entry")
    try:
        return paper.open_trade(
            body.symbol.upper(), body.side, body.qty, entry,
            body.stop_loss, body.target, state.intelligence,
        )
    except ValueError as e:                 # RC1.2 — qty sanity rejection
        raise HTTPException(422, str(e))


class PaperCloseBody(BaseModel):
    exit_price: float | None = None  # default: live spot


@router.post("/paper/close/{trade_id}")
async def paper_close(trade_id: str, body: PaperCloseBody):
    from ..services import paper
    px = body.exit_price or float(state.spot.get("ltp") or 0)
    if px <= 0:
        raise HTTPException(400, "No exit price available")
    t = paper.close_trade(trade_id, px)
    if not t:
        raise HTTPException(404, "Open trade not found")
    return t


# ---------- market replay / breadth / learning ----------
class ReplayBody(BaseModel):
    symbol: str
    date: str  # YYYY-MM-DD


@router.post("/replay")
async def market_replay(body: ReplayBody):
    _require_connection()
    from ..services import replay
    try:
        return await replay.build_session(service.client, body.symbol.upper(), body.date)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except BrokerError as e:
        raise HTTPException(502, str(e))


@router.get("/breadth")
async def market_breadth():
    from ..services import scanner
    return scanner.breadth()


@router.get("/learning")
async def learning_stats():
    """Self-learning memory: signal outcomes by regime."""
    from ..services import memory
    return memory.learning_stats()


@router.get("/analytics/performance")
async def analytics_performance():
    """Signal Performance Analytics — today / 7d / 30d, learning insights,
    validation. Analytics layer only; always returns valid JSON."""
    from ..services import analytics
    return analytics.performance()


@router.get("/audit")
async def audit_report():
    """Phase 3 Validation & Audit — how well existing decisions performed.
    Measurement only; always returns valid JSON."""
    from ..services import audit, analytics
    rep = audit.report()
    # Merge measurement-only learning layers the audit page renders
    # (calibration + Brier forecast quality + engine reliability weights).
    try:
        perf = analytics.performance()
        rep["calibration"] = perf.get("calibration")
        rep["engine_reliability"] = perf.get("engine_reliability")
        rep["execution_quality"] = perf.get("execution_quality")
        rep["kill_switch"] = state.kill_switch
    except Exception:
        pass
    return rep


# ---------- backtesting ----------
class BacktestBody(BaseModel):
    symbol: str
    year: int = Field(ge=2022, le=2025)


@router.post("/backtest")
async def run_backtest(body: BacktestBody):
    _require_connection()
    from ..services import backtest
    try:
        return await backtest.run(service.client, body.symbol.upper(), body.year)
    except ValueError as e:
        raise HTTPException(400, str(e))
    except BrokerError as e:
        raise HTTPException(502, str(e))


# ---------- journal ----------
class JournalBody(BaseModel):
    date: str | None = None
    time: str | None = None
    market: str
    signal: str
    entry: float | None = None
    exit: float | None = None
    stop_loss: float | None = None
    target: float | None = None
    pnl: float | None = None
    confidence: float | None = None
    notes: str = ""
    reason: str = ""
    grade: str = ""
    screenshot: str = ""  # data-URL or external URL


@router.get("/journal")
async def get_journal():
    return journal.list_entries()


@router.post("/journal")
async def add_journal(body: JournalBody):
    return journal.add_entry(body.model_dump())
