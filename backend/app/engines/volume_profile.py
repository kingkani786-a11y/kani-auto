"""Layer 6 — Volume Profile Engine: POC, VAH, VAL, acceptance/rejection."""
from __future__ import annotations

from typing import Any

BINS = 24
VALUE_AREA = 0.70


def analyze(candles: list[dict]) -> dict[str, Any]:
    if len(candles) < 20:
        return {"direction": "NEUTRAL", "score_bull": 50, "score_bear": 50, "notes": []}

    lo = min(c["low"] for c in candles)
    hi = max(c["high"] for c in candles)
    if hi <= lo:
        return {"direction": "NEUTRAL", "score_bull": 50, "score_bear": 50, "notes": []}

    width = (hi - lo) / BINS
    vols = [0.0] * BINS
    for c in candles:
        tp = (c["high"] + c["low"] + c["close"]) / 3.0
        idx = min(int((tp - lo) / width), BINS - 1)
        vols[idx] += max(float(c.get("volume", 0)), 1.0)  # indices: count-weighted

    total = sum(vols)
    poc_i = max(range(BINS), key=lambda i: vols[i])
    # expand value area around POC until 70% of volume captured
    lo_i = hi_i = poc_i
    acc = vols[poc_i]
    while acc < VALUE_AREA * total and (lo_i > 0 or hi_i < BINS - 1):
        nxt_lo = vols[lo_i - 1] if lo_i > 0 else -1
        nxt_hi = vols[hi_i + 1] if hi_i < BINS - 1 else -1
        if nxt_hi >= nxt_lo:
            hi_i += 1; acc += max(nxt_hi, 0)
        else:
            lo_i -= 1; acc += max(nxt_lo, 0)

    center = lambda i: lo + (i + 0.5) * width
    poc, val, vah = center(poc_i), lo + lo_i * width, lo + (hi_i + 1) * width
    close = candles[-1]["close"]

    notes: list[str] = []
    bull = bear = 50.0
    if close > vah:
        bull += 18; bear -= 12
        state = "ACCEPTANCE_ABOVE"
        notes.append("Price accepted above value area — initiative buying")
    elif close < val:
        bear += 18; bull -= 12
        state = "ACCEPTANCE_BELOW"
        notes.append("Price accepted below value area — initiative selling")
    else:
        state = "INSIDE_VALUE"
        if close > poc:
            bull += 6
        else:
            bear += 6
        notes.append("Price rotating inside value area")

    # rejection wick off VAH/VAL on the latest bar
    last = candles[-1]
    rng = max(last["high"] - last["low"], 1e-9)
    if last["high"] > vah and (last["high"] - close) / rng > 0.6:
        bear += 8; state = "REJECTION_AT_VAH"
        notes.append("Rejection wick at VAH")
    if last["low"] < val and (close - last["low"]) / rng > 0.6:
        bull += 8; state = "REJECTION_AT_VAL"
        notes.append("Rejection wick at VAL")

    bull, bear = max(0, min(100, bull)), max(0, min(100, bear))
    direction = "BULL" if bull - bear >= 10 else "BEAR" if bear - bull >= 10 else "NEUTRAL"
    return {
        "direction": direction,
        "score_bull": round(bull, 1),
        "score_bear": round(bear, 1),
        "poc": round(poc, 2),
        "vah": round(vah, 2),
        "val": round(val, 2),
        "state": state,
        "notes": notes,
    }
