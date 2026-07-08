"""Market Replay Engine.

Serves a historical session's 1-minute candles plus AI decision markers so
the frontend can step through the day minute-by-minute. Markers are
computed every 15 minutes from the candle-only layers (trend, structure,
MTF, regime) — option-chain history replays too when the market-memory
table has snapshots for that day.
"""
from __future__ import annotations

import datetime
from typing import Any

from ..broker.dhan import DhanClient
from ..broker.instruments import get_instrument
from ..engines import mtf, structure
from ..engines.technicals import adx, atr, momentum, trend_state

from . import memory


async def build_session(client: DhanClient, symbol: str, date: str) -> dict[str, Any]:
    inst = get_instrument(symbol)
    day = datetime.date.fromisoformat(date)
    # pull a window ending on the requested day (includes warm-up history)
    frm = day - datetime.timedelta(days=6)
    candles = await client._intraday_window(inst, "1", frm, day)
    day_start = datetime.datetime.combine(day, datetime.time.min).timestamp()
    day_end = day_start + 86400
    session = [c for c in candles if day_start <= c["time"] < day_end]
    if not session:
        raise ValueError(f"No session data for {symbol} on {date} (holiday or out of history range)")
    warmup = [c for c in candles if c["time"] < day_start][-240:]

    # decision markers every 15 minutes, computed only from data visible then
    markers: list[dict] = []
    for i in range(15, len(session) + 1, 15):
        visible = warmup + session[:i]
        closes = [c["close"] for c in visible]
        if len(closes) < 60:
            continue
        c5 = mtf.resample(visible, 5)
        atr_v = atr(c5)
        st = structure.analyze(c5, atr_v)
        ts_block = trend_state(closes)
        adx_v = adx(c5)
        m = mtf.analyze(visible)
        bull = st["score_bull"] * 0.4 + m["score_bull"] * 0.4 + (70 if ts_block["trend"] == "BULLISH" else 30 if ts_block["trend"] == "BEARISH" else 50) * 0.2
        decision = ("BULLISH" if bull >= 62 and adx_v >= 20
                    else "BEARISH" if bull <= 38 and adx_v >= 20 else "NO TRADE")
        markers.append({
            "time": session[i - 1]["time"],
            "decision": decision,
            "score": round(bull, 1),
            "trend": ts_block["trend"],
            "structure_event": st.get("event"),
            "alignment": m["alignment"],
            "adx": round(adx_v, 1),
            "momentum": round(momentum(closes), 2),
        })

    # option-chain replay from stored market memory (if recorded that day)
    chain_history = [r for r in memory.history(inst.symbol, limit=2000)
                     if str(r.get("ts", "")).startswith(date)]

    return {
        "symbol": inst.symbol,
        "date": date,
        "candles": session,
        "markers": markers,
        "chain_history": chain_history,
        "note": ("Markers use candle-visible layers only (trend/structure/MTF/regime). "
                 "OI/PCR replay appears when market memory has snapshots for this date."),
    }
