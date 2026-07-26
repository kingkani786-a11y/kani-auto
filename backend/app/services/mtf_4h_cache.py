"""4-Hour candle cache — owner Step 10 (MTF Confluence Engine, 2026-07-27).

A 4H candle only closes 6x/day, so refetching every 30s AI cycle would be
pure waste and would compete with the shared broker rate budget the live
spot/option feed depends on. Same "cache-gated, refresh lazily" discipline
as period_pivot_cache.py, just a shorter TTL since 4H is more active than
weekly/monthly pivots but still far slower than the 1-minute feed.
"""
from __future__ import annotations

import logging
import time
from typing import Any

log = logging.getLogger(__name__)

_TTL_S = 20 * 60   # 20 min — a 4H bar is "in progress" for up to 4h; this is
                   # frequent enough to catch a bar close without hammering
                   # the broker anywhere near per-cycle (30s) frequency.
_cache: dict[str, dict[str, Any]] = {}   # symbol -> {"ts": float, "candles": [...]}


def get(symbol: str) -> list[dict]:
    c = _cache.get(symbol)
    return c["candles"] if c else []


def stale(symbol: str) -> bool:
    c = _cache.get(symbol)
    return not c or (time.time() - c["ts"]) > _TTL_S


async def refresh(client, inst) -> None:
    if not stale(inst.symbol):
        return
    try:
        candles = await client.get_tf_candles(inst, "4H", min_candles=60)
        _cache[inst.symbol] = {"ts": time.time(), "candles": candles}
    except Exception as e:
        log.warning("4H candle refresh failed for %s: %s", inst.symbol, e)
        _cache.setdefault(inst.symbol, {"ts": time.time(), "candles": []})
