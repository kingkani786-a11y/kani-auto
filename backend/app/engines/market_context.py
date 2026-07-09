"""V11 institutional data layer + Market Session Engine.

Everything here is derived from candles the platform ALREADY fetches each AI
cycle (zero extra broker calls) plus an optional India VIX reading. Previous-day
levels, session VWAP, and the opening-range breakout are computed locally.
GIFT NIFTY has no reliable Dhan data feed, so it is reported as unavailable and
the dependent engines fall back to neutral rather than inventing numbers.
"""
from __future__ import annotations

import datetime
from typing import Any

from ..core.clock import IST


def session_now(market_type: str = "INDEX", is_expiry: bool = False) -> dict[str, Any]:
    """Market Session Engine — classify the trading session by IST clock."""
    now = datetime.datetime.now(IST)
    t = now.time()
    H = lambda h, m=0: datetime.time(h, m)

    if market_type == "COMMODITY":
        # MCX runs 09:00–23:30; coarse buckets
        if t < H(9): phase = "PRE_MARKET"
        elif t < H(11): phase = "MORNING_TREND"
        elif t < H(17): phase = "AFTERNOON_TREND"
        elif t < H(23, 30): phase = "EVENING_SESSION"
        else: phase = "CLOSED"
    else:
        if t < H(9, 15): phase = "PRE_MARKET"
        elif t < H(9, 45): phase = "OPENING_DRIVE"
        elif t < H(11, 30): phase = "MORNING_TREND"
        elif t < H(13): phase = "LUNCH_SESSION"
        elif t < H(14, 30): phase = "AFTERNOON_TREND"
        elif is_expiry and t >= H(14, 30): phase = "EXPIRY_POWER_HOUR"
        elif t <= H(15, 30): phase = "CLOSING_SESSION"
        else: phase = "CLOSED"

    # entry-timing guidance per session (used to validate entries)
    favorable = phase in ("OPENING_DRIVE", "MORNING_TREND", "AFTERNOON_TREND",
                          "EXPIRY_POWER_HOUR", "EVENING_SESSION")
    caution = phase in ("LUNCH_SESSION", "PRE_MARKET", "CLOSING_SESSION")
    return {
        "session": phase,
        "label": phase.replace("_", " ").title(),
        "favorable_for_entry": favorable,
        "caution": caution,
        "ist_time": now.strftime("%H:%M"),
    }


def institutional_levels(candles_1m: list[dict]) -> dict[str, Any]:
    """Previous-day OHLC, session VWAP, and opening-range breakout — all local."""
    if len(candles_1m) < 30:
        return {}

    # group candles by IST date
    by_day: dict[datetime.date, list[dict]] = {}
    for c in candles_1m:
        d = datetime.datetime.fromtimestamp(c["time"], IST).date()
        by_day.setdefault(d, []).append(c)
    days = sorted(by_day)
    today = days[-1]
    today_candles = by_day[today]

    out: dict[str, Any] = {}

    # previous day H/L/C
    if len(days) >= 2:
        prev = by_day[days[-2]]
        out["prev_day_high"] = round(max(c["high"] for c in prev), 2)
        out["prev_day_low"] = round(min(c["low"] for c in prev), 2)
        out["prev_day_close"] = round(prev[-1]["close"], 2)

    # session VWAP (volume-weighted; typical-price mean fallback for indices)
    pv = vol = 0.0
    for c in today_candles:
        tp = (c["high"] + c["low"] + c["close"]) / 3.0
        v = max(float(c.get("volume", 0)), 0.0)
        pv += tp * v; vol += v
    out["vwap"] = round(pv / vol, 2) if vol else round(
        sum((c["high"] + c["low"] + c["close"]) / 3 for c in today_candles) / len(today_candles), 2)

    # opening range (first 15 min) + breakout state
    orb = today_candles[:15]
    if orb:
        orh = round(max(c["high"] for c in orb), 2)
        orl = round(min(c["low"] for c in orb), 2)
        close = today_candles[-1]["close"]
        out["orb_high"], out["orb_low"] = orh, orl
        out["orb_state"] = ("BREAKOUT_UP" if close > orh else
                            "BREAKDOWN" if close < orl else "INSIDE")

    out["spot"] = round(today_candles[-1]["close"], 2)
    out["day_open"] = round(today_candles[0]["open"], 2)   # RC — Layer-4 gap scoring
    return out


# ---- India VIX / GIFT holders (set by market_service; graceful when absent) ----
_vix: dict[str, Any] = {"value": None, "prev": None, "ts": 0.0}
_gift: dict[str, Any] = {"available": False, "value": None, "prev_close": None}


def set_vix(value: float) -> None:
    import time
    if value and value > 0:
        if _vix["value"] is not None and abs(_vix["value"] - value) > 1e-9:
            _vix["prev"] = _vix["value"]
        _vix["value"] = round(value, 2)
        _vix["ts"] = time.time()


def get_vix() -> dict[str, Any]:
    return dict(_vix)


def get_gift() -> dict[str, Any]:
    return dict(_gift)
