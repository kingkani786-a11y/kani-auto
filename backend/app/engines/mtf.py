"""Layer 7 — Multi-Timeframe Engine.

Resamples 1-minute candles into 1/3/5/15/30/60-minute series and grades
trend agreement across them. Higher timeframes carry more weight.
"""
from __future__ import annotations

from typing import Any

from .technicals import ema

TIMEFRAMES = [1, 3, 5, 15, 30, 60]
TF_WEIGHT = {1: 0.8, 3: 0.9, 5: 1.0, 15: 1.2, 30: 1.2, 60: 1.3}


def resample(candles_1m: list[dict], tf_min: int) -> list[dict]:
    if tf_min == 1:
        return candles_1m
    out: list[dict] = []
    bucket = None
    cur: dict | None = None
    for c in candles_1m:
        b = int(c["time"]) // (tf_min * 60)
        if b != bucket:
            if cur:
                out.append(cur)
            bucket = b
            cur = dict(c)
        else:
            assert cur is not None
            cur["high"] = max(cur["high"], c["high"])
            cur["low"] = min(cur["low"], c["low"])
            cur["close"] = c["close"]
            cur["volume"] = cur.get("volume", 0) + c.get("volume", 0)
    if cur:
        out.append(cur)
    return out


def _tf_trend(closes: list[float]) -> str:
    if len(closes) < 25:
        return "NEUTRAL"
    e20, e50 = ema(closes, 20)[-1], ema(closes, min(50, len(closes)))[-1]
    last = closes[-1]
    if e20 > e50 and last > e20:
        return "BULL"
    if e20 < e50 and last < e20:
        return "BEAR"
    return "NEUTRAL"


def analyze(candles_1m: list[dict]) -> dict[str, Any]:
    if len(candles_1m) < 60:
        return {"direction": "NEUTRAL", "score_bull": 50, "score_bear": 50,
                "alignment": 0, "frames": {}, "notes": []}

    frames: dict[str, str] = {}
    bull_w = bear_w = tot_w = 0.0
    for tf in TIMEFRAMES:
        series = resample(candles_1m, tf)
        t = _tf_trend([c["close"] for c in series])
        frames[f"{tf}m"] = t
        w = TF_WEIGHT[tf]
        tot_w += w
        if t == "BULL":
            bull_w += w
        elif t == "BEAR":
            bear_w += w

    bull = bull_w / tot_w * 100
    bear = bear_w / tot_w * 100
    alignment = round(max(bull, bear), 0)
    direction = "BULL" if bull - bear >= 20 else "BEAR" if bear - bull >= 20 else "NEUTRAL"

    notes: list[str] = []
    if direction != "NEUTRAL":
        agreeing = [tf for tf, t in frames.items() if t == direction]
        notes.append(f"{', '.join(agreeing)} aligned {'bullish' if direction == 'BULL' else 'bearish'} — alignment {alignment:.0f}%")
    else:
        notes.append("Timeframes disagree — no dominant direction")

    return {
        "direction": direction,
        "score_bull": round(50 + (bull - bear) / 2, 1),
        "score_bear": round(50 + (bear - bull) / 2, 1),
        "alignment": alignment,
        "frames": frames,
        "notes": notes,
    }
