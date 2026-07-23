"""Weekly/Monthly pivot cache (owner, 2026-07-23 — S/R Phase 2).

Weekly/Monthly pivots only change once their period rolls, so a long TTL
(6h) keeps this to one broker call every few hours per symbol — negligible
against Dhan's rate limits, same "cache-gated, refresh lazily" style as
global_feed.py's 180s cache (this just needs a much longer one, since the
underlying data itself changes far less often).
"""
from __future__ import annotations

import datetime
import logging
import time
from typing import Any

from ..engines import support_resistance

log = logging.getLogger(__name__)

_TTL_S = 6 * 3600
_DAYS_BACK = 100     # comfortably covers >=2 complete months
_cache: dict[str, dict[str, Any]] = {}   # symbol -> {"ts": float, "weekly": {}, "monthly": {}}


def get(symbol: str) -> dict[str, Any]:
    c = _cache.get(symbol)
    return {"weekly": c["weekly"], "monthly": c["monthly"]} if c else {"weekly": {}, "monthly": {}}


def stale(symbol: str) -> bool:
    c = _cache.get(symbol)
    return not c or (time.time() - c["ts"]) > _TTL_S


async def refresh(client, inst) -> None:
    if not stale(inst.symbol):
        return
    try:
        today = datetime.date.today()
        daily = await client.get_daily_candles(
            inst, (today - datetime.timedelta(days=_DAYS_BACK)).isoformat(), today.isoformat())
        _cache[inst.symbol] = {
            "ts": time.time(),
            "weekly": support_resistance.period_pivots(daily, "W"),
            "monthly": support_resistance.period_pivots(daily, "M"),
        }
    except Exception as e:
        log.warning("period pivot refresh failed for %s: %s", inst.symbol, e)
        # keep serving the old cache (or empty) rather than crash the caller
        _cache.setdefault(inst.symbol, {"ts": time.time(), "weekly": {}, "monthly": {}})
