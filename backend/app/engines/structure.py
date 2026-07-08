"""Layer 2 — Market Structure Engine.

Swing-pivot detection (fractals) -> HH/HL/LH/LL labeling, support/
resistance, breakout/breakdown, and liquidity zones (clustered equal
highs/lows that attract stop hunts).
"""
from __future__ import annotations

from typing import Any


def find_pivots(candles: list[dict], span: int = 2) -> tuple[list[tuple[int, float]], list[tuple[int, float]]]:
    highs: list[tuple[int, float]] = []
    lows: list[tuple[int, float]] = []
    for i in range(span, len(candles) - span):
        window = candles[i - span : i + span + 1]
        h, l = candles[i]["high"], candles[i]["low"]
        if h == max(c["high"] for c in window):
            highs.append((i, h))
        if l == min(c["low"] for c in window):
            lows.append((i, l))
    return highs, lows


def _liquidity_zones(pivots: list[tuple[int, float]], tol: float) -> list[float]:
    """Clusters of near-equal pivot prices = resting liquidity."""
    zones: list[float] = []
    prices = sorted(p for _, p in pivots)
    i = 0
    while i < len(prices) - 1:
        cluster = [prices[i]]
        j = i + 1
        while j < len(prices) and prices[j] - cluster[0] <= tol:
            cluster.append(prices[j])
            j += 1
        if len(cluster) >= 2:
            zones.append(round(sum(cluster) / len(cluster), 2))
        i = j
    return zones[-4:]


def analyze(candles: list[dict], atr_v: float) -> dict[str, Any]:
    if len(candles) < 20:
        return {"direction": "NEUTRAL", "score_bull": 50, "score_bear": 50, "notes": []}

    close = candles[-1]["close"]
    highs, lows = find_pivots(candles)
    notes: list[str] = []
    bull = bear = 50.0

    # ---- swing sequence: HH/HL vs LH/LL ----
    labels: list[str] = []
    if len(highs) >= 2:
        labels.append("HH" if highs[-1][1] > highs[-2][1] else "LH")
    if len(lows) >= 2:
        labels.append("HL" if lows[-1][1] > lows[-2][1] else "LL")
    if labels == ["HH", "HL"]:
        bull += 22; bear -= 18
        notes.append("Structure printing higher highs and higher lows")
    elif labels == ["LH", "LL"]:
        bear += 22; bull -= 18
        notes.append("Structure printing lower highs and lower lows")
    elif "HL" in labels:
        bull += 8
    elif "LH" in labels:
        bear += 8

    # ---- support / resistance from last pivots ----
    resistance = highs[-1][1] if highs else max(c["high"] for c in candles[-20:])
    support = lows[-1][1] if lows else min(c["low"] for c in candles[-20:])

    # ---- breakout / breakdown (ATR-buffered to avoid wick fakes) ----
    event = "NONE"
    buf = 0.15 * atr_v
    prior_res = highs[-2][1] if len(highs) >= 2 else resistance
    prior_sup = lows[-2][1] if len(lows) >= 2 else support
    if close > prior_res + buf:
        event = "BREAKOUT"
        bull += 15
        notes.append(f"Breakout above {round(prior_res, 1)} confirmed")
    elif close < prior_sup - buf:
        event = "BREAKDOWN"
        bear += 15
        notes.append(f"Breakdown below {round(prior_sup, 1)} confirmed")

    # ---- liquidity zones ----
    tol = max(0.0005 * close, 0.2 * atr_v)
    liq_above = _liquidity_zones([p for p in highs if p[1] > close], tol)
    liq_below = _liquidity_zones([p for p in lows if p[1] < close], tol)

    # proximity context: hugging support is constructive, hugging resistance caps
    if atr_v > 0:
        if 0 < (close - support) < 0.8 * atr_v and event == "NONE":
            bull += 5
            notes.append(f"Price basing just above support {round(support, 1)}")
        if 0 < (resistance - close) < 0.8 * atr_v and event == "NONE":
            bear += 5
            notes.append(f"Price pressing into resistance {round(resistance, 1)}")

    bull, bear = max(0, min(100, bull)), max(0, min(100, bear))
    direction = "BULL" if bull - bear >= 10 else "BEAR" if bear - bull >= 10 else "NEUTRAL"
    return {
        "direction": direction,
        "score_bull": round(bull, 1),
        "score_bear": round(bear, 1),
        "swing": "/".join(labels) or "—",
        "support": round(support, 2),
        "resistance": round(resistance, 2),
        "event": event,
        "liquidity_above": liq_above,
        "liquidity_below": liq_below,
        "notes": notes,
    }
