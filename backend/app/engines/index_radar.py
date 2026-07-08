"""V13 — AI Index Selector (momentum radar).

Ranks the five supported indices from ONE existing batch-quote call per
minute (the same endpoint the stock scanner already uses — minimal feed
impact). HONEST SCOPE: this is a momentum / range-position ranking derived
from live quotes only; it is labelled as such. A full institutional ranking
(liquidity, OI flow) would need per-index option chains, which are
deliberately NOT fetched to protect broker rate limits.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from ..broker.instruments import INSTRUMENTS

log = logging.getLogger(__name__)

_INDICES = ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX"]
_INTERVAL = 60.0            # one batch call per minute, max
_cache: dict[str, Any] = {"ts": 0.0, "data": None}


async def build(client, current_symbol: str) -> dict[str, Any] | None:
    now = time.time()
    if now - _cache["ts"] < _INTERVAL:
        return _cache["data"]
    _cache["ts"] = now      # set first so failures don't hammer the API

    ids = [INSTRUMENTS[s].security_id for s in _INDICES]
    by_id = {str(INSTRUMENTS[s].security_id): s for s in _INDICES}
    try:
        quotes = await client.get_quotes_batch("IDX_I", ids)
    except Exception as e:
        log.warning("index radar batch failed: %s", e)
        return _cache["data"]

    rows: list[dict[str, Any]] = []
    for sid, q in (quotes or {}).items():
        sym = by_id.get(str(sid))
        if not sym or not isinstance(q, dict):
            continue
        ltp = float(q.get("last_price") or 0)
        if ltp <= 0:
            continue
        ohlc = q.get("ohlc") or {}
        o = float(ohlc.get("open") or ltp)
        h = float(ohlc.get("high") or ltp)
        low = float(ohlc.get("low") or ltp)
        chg = (ltp / o - 1) * 100 if o else 0.0
        rng = h - low
        pos = (ltp - low) / rng if rng > 0 else 0.5      # 1 = at day high
        drive = abs(pos - 0.5) * 2                       # conviction within range
        # momentum score (0-100) — quote-derived only, labelled as such
        score = round(min(100.0, abs(chg) * 30 + drive * 40 + (rng / ltp * 100) * 8), 0)
        rows.append({
            "symbol": sym, "ltp": round(ltp, 2), "change_pct": round(chg, 2),
            "range_pos": round(pos * 100, 0), "score": score,
            "bias": "BULL" if chg > 0.05 else "BEAR" if chg < -0.05 else "FLAT",
        })

    if not rows:
        return _cache["data"]
    rows.sort(key=lambda r: r["score"], reverse=True)
    best = rows[0]
    data = {
        "ready": True, "ranking": rows,
        "best": best["symbol"],
        "best_reason": f"{best['change_pct']:+.2f}% today · at {best['range_pos']:.0f}% of day range",
        "current": current_symbol,
        "note": "Momentum ranking from live quotes (1 batch call/min). "
                "Liquidity/institutional ranking would need per-index option "
                "chains — not fetched, protecting feed limits.",
        "ts": now,
    }
    _cache["data"] = data
    return data
