"""1-Hour candle cache — bug fix, V7.0 observation phase (2026-07-27).

Step 10's mtf_confluence.py originally resampled 1H bars from state.candles
(the live 1-minute feed, hard-capped at 600 bars / 10h in market_service.py).
A 1H timeframe needs 30 complete bars to satisfy _MIN_BARS — that's 1800
minutes (30h) of 1-minute history, 3x more than the 600-bar cap can ever
hold. 1H was therefore structurally unable to ever become "ready" through
that path, confirmed live on 2026-07-27 (Hero's MTF row silently never
showed 1H). Fixed the same way 4H already handles this: a real, direct
broker fetch, cached and refreshed at a low frequency rather than resampled
from the capped short-window buffer.
"""
from __future__ import annotations

import logging
import time
from typing import Any

log = logging.getLogger(__name__)

_TTL_S = 10 * 60   # 10 min — a 1H bar closes far more often than 4H's 6x/day,
                   # so this needs a shorter TTL to catch bar closes promptly,
                   # while still staying far below the live feed's 30s cadence.
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
        candles = await client.get_tf_candles(inst, "1H", min_candles=60)
        _cache[inst.symbol] = {"ts": time.time(), "candles": candles}
    except Exception as e:
        log.warning("1H candle refresh failed for %s: %s", inst.symbol, e)
        _cache.setdefault(inst.symbol, {"ts": time.time(), "candles": []})
