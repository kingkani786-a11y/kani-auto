"""Layer 8 — Market Regime Engine.

Classifies the tape so the confluence engine knows whether conditions
even permit a trade. Regime score is a QUALITY multiplier, not a
direction: trending/high-momentum markets score high, chop scores low.
"""
from __future__ import annotations

import datetime
from typing import Any


def analyze(
    adx_v: float,
    atr_pct: float,
    momentum_pct: float,
    alignment: float,
    expiry: str | None,
    spot: float,
    max_pain: float | None,
) -> dict[str, Any]:
    notes: list[str] = []

    # Expiry pinning: expiry day + price gravitating to max pain
    pinning = False
    if expiry and max_pain and spot:
        try:
            if datetime.date.fromisoformat(expiry) == datetime.date.today() and \
               abs(spot - max_pain) / spot < 0.004:
                pinning = True
        except ValueError:
            pass

    if pinning:
        regime, score = "EXPIRY_PINNING", 30
        notes.append(f"Expiry day with price pinned near max pain {max_pain} — theta game, avoid directional trades")
    elif adx_v >= 28 and abs(momentum_pct) > 0.25:
        regime, score = "HIGH_MOMENTUM", 90
        notes.append("High-momentum regime — strong directional follow-through likely")
    elif adx_v >= 22:
        regime, score = "TRENDING", 80
        notes.append("Trending regime — pullback entries favored")
    elif atr_pct > 0.9:
        regime, score = "VOLATILE", 45
        notes.append("Volatile regime — wide swings without direction, size down")
    elif adx_v < 17 and abs(momentum_pct) < 0.1:
        regime, score = "LOW_MOMENTUM", 35
        notes.append("Low-momentum chop — signals unreliable")
    else:
        regime, score = "RANGE_BOUND", 50
        notes.append("Range-bound regime — fade extremes, skip breakout chases")

    # MTF agreement nudges quality
    score = max(10, min(100, score + (alignment - 60) * 0.2))

    return {"regime": regime, "score": round(score, 1), "notes": notes}


def phases(candles: list[dict], flow: dict, iv: float, iv_prev: float,
           adx_v: float, atr_now: float, atr_prev: float) -> list[str]:
    """Advanced Market Regime AI (V7.5): Wyckoff-style phase detection.
    Returns every phase currently in evidence — informational layer."""
    out: list[str] = []
    if len(candles) < 40:
        return out
    closes = [c["close"] for c in candles]
    vols = [max(float(c.get("volume", 0)), 0.0) for c in candles]
    run20 = (closes[-1] / closes[-20] - 1) * 100 if closes[-20] else 0.0
    run5 = (closes[-1] / closes[-5] - 1) * 100 if closes[-5] else 0.0
    rng20 = max(c["high"] for c in candles[-20:]) - min(c["low"] for c in candles[-20:])
    avg_vol = sum(vols[-40:]) / 40 or 1.0
    recent_vol = sum(vols[-5:]) / 5

    # trend expansion / exhaustion
    if adx_v > 25 and abs(run5) > abs(run20) / 3 and recent_vol > avg_vol:
        out.append("TREND_EXPANSION")
    if abs(run20) > 1.2 and abs(run5) < abs(run20) / 8:
        out.append("TREND_EXHAUSTION")

    # markup / markdown (directional trending phases)
    if adx_v > 22 and run20 > 0.5:
        out.append("MARKUP")
    elif adx_v > 22 and run20 < -0.5:
        out.append("MARKDOWN")

    # accumulation / distribution: tight range + volume character
    tight = rng20 / closes[-1] < 0.006 if closes[-1] else False
    up_vol = sum(v for c, v in zip(candles[-20:], vols[-20:]) if c["close"] >= c["open"])
    dn_vol = sum(v for c, v in zip(candles[-20:], vols[-20:]) if c["close"] < c["open"])
    if tight and up_vol > dn_vol * 1.3:
        out.append("ACCUMULATION")
    elif tight and dn_vol > up_vol * 1.3:
        out.append("DISTRIBUTION")

    # flow-driven phases
    acts = flow.get("activities", []) if flow else []
    if "SHORT_COVERING" in acts:
        out.append("SHORT_COVERING")
    if "LONG_UNWINDING" in acts:
        out.append("LONG_LIQUIDATION")

    # volatility states
    if atr_prev > 0:
        if atr_now > atr_prev * 1.35:
            out.append("VOLATILITY_EXPANSION")
        elif atr_now < atr_prev * 0.7:
            out.append("VOLATILITY_COMPRESSION")

    # gamma squeeze: IV rising fast + accelerating price
    if iv_prev > 0 and iv > iv_prev * 1.12 and abs(run5) > 0.5 and "TREND_EXPANSION" in out:
        out.append("GAMMA_SQUEEZE")

    return out
