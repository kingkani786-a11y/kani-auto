"""Global Market Context Feed — OWNER-LOCKED DOCTRINE:

    Global Context is NEVER a hard gate. It is context only:
    a ±3 adjustment to dynamic confidence. It never overrides Trend,
    never vetoes, never fabricates. (docs/PROPOSALS.md, locked 2026-07-08)

Source: Yahoo Finance public chart endpoint (UNOFFICIAL, best-effort — see
KNOWN_LIMITATIONS). On any failure the feed reports available=False and the
dashboard honestly shows "Waiting for Data Source". Cache 180s; ~7 requests
per refresh — negligible.
Its real value is MEASURED: the weekly digest compares outcomes with vs
without the adjustment (contribution report).
"""
from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import httpx

log = logging.getLogger(__name__)

_SYMBOLS = {
    "NQ=F": "Nasdaq Fut", "ES=F": "S&P Fut", "CL=F": "Crude WTI",
    "GC=F": "Gold", "DX-Y.NYB": "DXY", "^VIX": "US VIX", "USDINR=X": "USDINR",
}
# Layer-2 (owner's 3-layer clock): Europe joins the fetch only in its window
_EUROPE = {"^GDAXI": "DAX", "^FTSE": "FTSE"}
_INTERVAL = 180.0
_cache: dict[str, Any] = {"ts": 0.0, "data": {"available": False,
                                              "note": "Waiting for Data Source"}}


async def _quote(client: httpx.AsyncClient, sym: str) -> dict | None:
    try:
        r = await client.get(
            f"https://query1.finance.yahoo.com/v8/finance/chart/{sym}",
            params={"interval": "1d", "range": "2d"},
            headers={"User-Agent": "Mozilla/5.0"}, timeout=6.0)
        m = r.json()["chart"]["result"][0]["meta"]
        px, pc = float(m["regularMarketPrice"]), float(m["chartPreviousClose"])
        return {"name": _SYMBOLS.get(sym) or _EUROPE.get(sym, sym), "price": round(px, 2),
                "chg_pct": round((px / pc - 1) * 100, 2) if pc else 0.0}
    except Exception as e:
        log.debug("global quote failed %s: %s", sym, e)
        return None


def _score(q: dict[str, dict]) -> tuple[float, str, list[str]]:
    """Transparent vote system → adjustment in [-3, +3]. Every vote is listed."""
    votes, why = 0.0, []

    def v(sym, up_thr, dn_thr, up_pts, dn_pts, up_msg, dn_msg):
        nonlocal votes
        c = q.get(sym, {}).get("chg_pct")
        if c is None:
            return
        if c >= up_thr:
            votes += up_pts
            why.append(f"{up_msg} ({c:+.1f}%)")
        elif c <= dn_thr:
            votes += dn_pts
            why.append(f"{dn_msg} ({c:+.1f}%)")

    v("ES=F", 0.3, -0.3, +1, -1, "S&P futures up", "S&P futures down")
    v("NQ=F", 0.3, -0.3, +1, -1, "Nasdaq futures up", "Nasdaq futures down")
    v("^VIX", 3.0, -3.0, -0.5, +0.5, "US VIX spiking", "US VIX cooling")
    v("DX-Y.NYB", 0.3, -0.3, -0.5, +0.5, "Dollar strengthening", "Dollar easing")
    v("USDINR=X", 0.25, -0.25, -0.5, +0.5, "INR weakening", "INR strengthening")
    v("CL=F", 2.0, -2.0, -0.5, +0.5, "Crude surge (India import risk)", "Crude easing")

    adj = max(-3.0, min(3.0, round(votes)))
    state = "RISK_ON" if adj >= 1 else "RISK_OFF" if adj <= -1 else "NEUTRAL"
    return adj, state, why[:4]


def _clock() -> dict[str, Any]:
    """Owner's 3-layer clock, DST-safe: US open computed from America/New_York
    09:30 local (auto 6:30/8:00 PM IST), never hardcoded."""
    import datetime, zoneinfo
    ist = datetime.datetime.now(zoneinfo.ZoneInfo("Asia/Kolkata"))
    ny = ist.astimezone(zoneinfo.ZoneInfo("America/New_York"))
    us_open = datetime.time(9, 30) <= ny.time() <= datetime.time(16, 0) and ny.weekday() < 5
    mins_since_us_open = ((ny.hour - 9) * 60 + ny.minute - 30) if us_open else None
    t = ist.time()
    if datetime.time(8, 30) <= t <= datetime.time(11, 0):
        phase = "MORNING (US-close bias)"
    elif datetime.time(12, 30) <= t <= datetime.time(17, 0):
        phase = "AFTERNOON (Europe layer)"
    elif us_open:
        phase = "US OPEN REACTION"
    else:
        phase = "OFF-HOURS"
    return {"phase": phase, "us_open": us_open,
            "us_open_ist": ny.replace(hour=9, minute=30, second=0).astimezone(
                zoneinfo.ZoneInfo("Asia/Kolkata")).strftime("%H:%M IST"),
            "mins_since_us_open": mins_since_us_open, "ist": ist.strftime("%H:%M")}


# Layer-3 → next-morning handoff: last US-open reaction snapshot (persisted)
_overnight: dict[str, Any] = {}


def _gap_band(mag: float) -> str:
    """Declared bands (like the ladder's time bands) — NOT a calibrated
    probability; real gap% arrives once validated overnight data accumulates."""
    return "HIGH" if mag >= 1.0 else "MEDIUM" if mag >= 0.4 else "LOW"


def _next_session(quotes: dict, adj: float, state: str, clock: dict) -> dict | None:
    """Layer-3 — Next Session Preparation (NOT an entry engine)."""
    es = quotes.get("ES=F", {}).get("chg_pct")
    nq = quotes.get("NQ=F", {}).get("chg_pct")
    if es is None and nq is None:
        return None
    composite = ((es or 0) + (nq or 0)) / (2 if es is not None and nq is not None else 1)
    vix = quotes.get("^VIX", {}).get("chg_pct") or 0
    crude = quotes.get("CL=F", {}).get("chg_pct") or 0
    return {
        "captured_at": clock["ist"], "phase": clock["phase"],
        "us_composite_pct": round(composite, 2),
        "tomorrow_bias": "BEARISH" if composite <= -0.4 else "BULLISH" if composite >= 0.4 else "NEUTRAL",
        "gap_likelihood": _gap_band(abs(composite)),
        "overnight_risk": ("ELEVATED" if vix >= 8 or abs(crude) >= 3 else "NORMAL"),
        "holding_note": ("Overnight holds carry elevated event risk tonight"
                         if vix >= 8 or abs(crude) >= 3 else
                         "No unusual overnight risk flags from global feed"),
        "note": "Preparation context for the NEXT session — never an entry signal. "
                "Gap likelihood is a declared band, not a calibrated probability yet.",
    }


def _persist_overnight(snap: dict) -> None:
    try:
        from .journal import _sb
        if _sb:
            _sb.table("evolution_reports").insert(
                {"period": "overnight_prep", "report": snap}).execute()
    except Exception:
        pass


async def refresh() -> dict[str, Any]:
    now = time.time()
    if now - _cache["ts"] < _INTERVAL:
        return _cache["data"]
    _cache["ts"] = now
    clock = _clock()
    syms = dict(_SYMBOLS)
    if "AFTERNOON" in clock["phase"]:
        syms.update(_EUROPE)                       # Layer-2: Europe window only
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*(_quote(client, s) for s in syms))
    quotes = {}
    for s, r in zip(syms, results):
        if r:
            r = dict(r)
            r.setdefault("name", _EUROPE.get(s, _SYMBOLS.get(s, s)))
            quotes[s] = r
    if len(quotes) < 3:                       # too little to say anything
        _cache["data"] = {"available": False,
                          "note": "Waiting for Data Source (global feed unreachable)"}
        return _cache["data"]
    adj, state, why = _score(quotes)

    # Layer-3 — during the US session, keep the freshest reaction snapshot for
    # tomorrow morning; persist once per evening (first capture ≥15 min in)
    if clock["us_open"] and (clock["mins_since_us_open"] or 0) >= 15:
        snap = _next_session(quotes, adj, state, clock)
        if snap:
            import datetime as _dt
            today = _dt.date.today().isoformat()
            first_today = _overnight.get("date") != today
            _overnight.update({"date": today, **snap})
            if first_today:
                _persist_overnight(dict(_overnight))

    _cache["data"] = {
        "available": True, "quotes": quotes, "clock": clock,
        "risk_state": state, "adjust": adj, "reasons": why,
        # Morning handoff: yesterday evening's US-open reaction (if captured)
        "next_session": dict(_overnight) if _overnight else None,
        "source": "Yahoo Finance chart API (unofficial, best-effort)",
        "doctrine": "Context only — ±3 confidence adjustment; never a gate, never overrides Trend. "
                    "Next-session block is PREPARATION, not an entry signal.",
        "ts": now,
    }
    return _cache["data"]


def rehydrate_overnight() -> None:
    """Boot: restore last evening's US-reaction snapshot for the morning bias."""
    try:
        from .journal import _sb
        if _sb:
            rows = (_sb.table("evolution_reports").select("report")
                    .eq("period", "overnight_prep").order("id", desc=True)
                    .limit(1).execute().data or [])
            if rows and isinstance(rows[0].get("report"), dict):
                _overnight.update(rows[0]["report"])
                log.info("overnight prep restored: %s", _overnight.get("date"))
    except Exception as e:
        log.debug("overnight rehydrate skipped: %s", e)


def snapshot() -> dict[str, Any]:
    """Last refreshed data without network (for the sync confluence path)."""
    return _cache["data"]
