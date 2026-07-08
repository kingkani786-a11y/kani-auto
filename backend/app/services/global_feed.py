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
        return {"name": _SYMBOLS[sym], "price": round(px, 2),
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


async def refresh() -> dict[str, Any]:
    now = time.time()
    if now - _cache["ts"] < _INTERVAL:
        return _cache["data"]
    _cache["ts"] = now
    async with httpx.AsyncClient() as client:
        results = await asyncio.gather(*(_quote(client, s) for s in _SYMBOLS))
    quotes = {s: r for s, r in zip(_SYMBOLS, results) if r}
    if len(quotes) < 3:                       # too little to say anything
        _cache["data"] = {"available": False,
                          "note": "Waiting for Data Source (global feed unreachable)"}
        return _cache["data"]
    adj, state, why = _score(quotes)
    _cache["data"] = {
        "available": True, "quotes": quotes,
        "risk_state": state, "adjust": adj, "reasons": why,
        "source": "Yahoo Finance chart API (unofficial, best-effort)",
        "doctrine": "Context only — ±3 confidence adjustment; never a gate, never overrides Trend.",
        "ts": now,
    }
    return _cache["data"]


def snapshot() -> dict[str, Any]:
    """Last refreshed data without network (for the sync confluence path)."""
    return _cache["data"]
