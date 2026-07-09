"""Market Profile Engine — Initial Balance, day type, auction structure."""
from __future__ import annotations

import datetime
from typing import Any

from ..core.clock import IST


def analyze(candles_1m: list[dict], vp: dict[str, Any]) -> dict[str, Any]:
    """Uses today's 1m candles + the volume-profile value area."""
    today = datetime.datetime.now(IST).date()
    todays = [c for c in candles_1m
              if datetime.datetime.fromtimestamp(c["time"], IST).date() == today]
    if len(todays) < 15:
        return {"day_type": "FORMING", "notes": []}

    # Initial Balance = first 60 minutes
    ib = todays[:60]
    ib_high = max(c["high"] for c in ib)
    ib_low = min(c["low"] for c in ib)
    ib_range = ib_high - ib_low or 1e-9
    day_high = max(c["high"] for c in todays)
    day_low = min(c["low"] for c in todays)
    close = todays[-1]["close"]
    ext_up = max(day_high - ib_high, 0) / ib_range
    ext_dn = max(ib_low - day_low, 0) / ib_range

    notes: list[str] = []
    if ext_up > 1.0 and ext_dn < 0.25 and close > ib_high:
        day_type = "TREND_DAY_UP"
        notes.append("Trend day up: sustained range extension above the initial balance")
    elif ext_dn > 1.0 and ext_up < 0.25 and close < ib_low:
        day_type = "TREND_DAY_DOWN"
        notes.append("Trend day down: sustained range extension below the initial balance")
    elif ext_up > 0.25 and ext_dn > 0.25:
        day_type = "NEUTRAL_DAY"
        notes.append("Neutral day: both sides of the initial balance explored — responsive trade")
    elif ext_up > 0.25 or ext_dn > 0.25:
        day_type = "NORMAL_VARIATION"
        notes.append("Normal-variation day: one-sided extension beyond the initial balance")
    else:
        day_type = "BALANCED_DAY"
        notes.append("Balanced day: auction contained inside the initial balance")

    auction = "ONE_TIMEFRAMING_UP" if all(
        todays[i]["low"] >= todays[i - 30]["low"] for i in range(len(todays) - 1, max(len(todays) - 90, 30), -30)
    ) else "ONE_TIMEFRAMING_DOWN" if all(
        todays[i]["high"] <= todays[i - 30]["high"] for i in range(len(todays) - 1, max(len(todays) - 90, 30), -30)
    ) else "TWO_SIDED"
    if auction != "TWO_SIDED":
        notes.append(f"Auction is {auction.replace('_', ' ').lower()} — strong directional conviction")

    return {
        "ib_high": round(ib_high, 2),
        "ib_low": round(ib_low, 2),
        "day_type": day_type,
        "auction": auction,
        "value_area": [vp.get("val"), vp.get("vah")],
        "poc": vp.get("poc"),
        "notes": notes,
    }
