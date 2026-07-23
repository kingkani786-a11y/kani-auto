"""Layer 2 — Market Structure Engine.

Swing-pivot detection (fractals) -> HH/HL/LH/LL labeling, support/
resistance, breakout/breakdown, and liquidity zones (clustered equal
highs/lows that attract stop hunts).

Phase 3 additions (owner, 2026-07-24 — "Institutional AI Market Intelligence"
priority list, Module 3): BOS/CHOCH labeling, Buy/Sell-side liquidity framing
+ Stop Hunt detection, Auto Fibonacci + Golden Zone, and Auto Trendline —
every one of these is a deterministic classification or fixed formula over
data this file ALREADY computes (labels, event, liquidity_above/below,
pivots). No new indicator, no new "tune from evidence" threshold beyond what
analyze() already declares.
"""
from __future__ import annotations

from typing import Any

FIB_RATIOS = (0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0)
GOLDEN_ZONE = (0.618, 0.65)   # the band traders call the "golden pocket"
STOP_HUNT_LOOKBACK = 5        # candles examined for a sweep-and-reject


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


def _bos_choch(labels: list[str], event: str) -> str | None:
    """BOS (Break of Structure) = the break CONFIRMS the prevailing HH/HL or
    LH/LL sequence — continuation. CHOCH (Change of Character) = the break
    goes AGAINST that sequence — the first sign of a possible reversal.
    Deterministic from labels+event, already computed above; no new indicator."""
    if event == "NONE":
        return None
    uptrend = labels == ["HH", "HL"]
    downtrend = labels == ["LH", "LL"]
    if event == "BREAKOUT":
        return "BOS" if uptrend else "CHOCH" if downtrend else None
    if event == "BREAKDOWN":
        return "BOS" if downtrend else "CHOCH" if uptrend else None
    return None


def _stop_hunt(candles: list[dict], liq_above: list[float], liq_below: list[float]) -> list[dict[str, Any]]:
    """Sweep-and-reject: a candle's wick clears a liquidity zone but its
    close rejects back to the original side, within the SAME candle — the
    classic 'stop hunt' pattern (resting stops filled, then price reverses)."""
    hunts: list[dict[str, Any]] = []
    window = candles[-STOP_HUNT_LOOKBACK:]
    for c in window:
        for zone in liq_above:
            if c["high"] > zone and c["close"] < zone:
                hunts.append({"zone": zone, "side": "ABOVE", "type": "BUY_SIDE_SWEEP"})
        for zone in liq_below:
            if c["low"] < zone and c["close"] > zone:
                hunts.append({"zone": zone, "side": "BELOW", "type": "SELL_SIDE_SWEEP"})
    return hunts[-4:]


def fibonacci(highs: list[tuple[int, float]], lows: list[tuple[int, float]]) -> dict[str, Any]:
    """Retracement over the most recent swing leg (whichever pivot — the last
    high or the last low — came later defines the leg's direction). Fixed
    ratios (FIB_RATIOS), not fitted — same declared-constant discipline as
    the rest of this file."""
    if not highs or not lows:
        return {}
    idx_h, price_h = highs[-1]
    idx_l, price_l = lows[-1]
    if price_h == price_l:
        return {}
    up_leg = idx_h > idx_l   # the high came later -> this leg ran low-to-high
    rng = price_h - price_l
    levels = {}
    for pct in FIB_RATIOS:
        level = (price_h - pct * rng) if up_leg else (price_l + pct * rng)
        levels[f"{round(pct * 1000) / 10:g}"] = round(level, 2)
    golden_lo = (price_h - GOLDEN_ZONE[1] * rng) if up_leg else (price_l + GOLDEN_ZONE[0] * rng)
    golden_hi = (price_h - GOLDEN_ZONE[0] * rng) if up_leg else (price_l + GOLDEN_ZONE[1] * rng)
    return {
        "direction": "UP_LEG" if up_leg else "DOWN_LEG",
        "swing_high": round(price_h, 2), "swing_low": round(price_l, 2),
        "levels": levels,
        "golden_zone": [round(min(golden_lo, golden_hi), 2), round(max(golden_lo, golden_hi), 2)],
    }


def trendline(highs: list[tuple[int, float]], lows: list[tuple[int, float]],
              candles: list[dict]) -> dict[str, Any]:
    """Two-point trendline through the last 2 swing highs (resistance/down-
    trendline candidate) and last 2 swing lows (support/up-trendline
    candidate), each anchor tagged with the candle's own 'time' when present
    (falls back to the bar index) so the frontend chart can plot it directly —
    no linear-regression fit invented beyond the two real pivot points."""
    def _anchor(idx: int, price: float) -> dict[str, Any]:
        t = candles[idx].get("time", idx) if 0 <= idx < len(candles) else idx
        return {"time": t, "price": round(price, 2)}

    def _line(pivots: list[tuple[int, float]]) -> dict[str, Any] | None:
        if len(pivots) < 2:
            return None
        (i1, p1), (i2, p2) = pivots[-2], pivots[-1]
        if i2 == i1:
            return None
        slope = (p2 - p1) / (i2 - i1)
        last_idx = len(candles) - 1
        projected = p2 + slope * (last_idx - i2)
        return {"points": [_anchor(i1, p1), _anchor(i2, p2)],
                "projected_current": round(projected, 2)}

    return {"resistance_trendline": _line(highs), "support_trendline": _line(lows)}


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
        # Phase 3 additions (owner, 2026-07-24, Module 3) — additive, backward
        # compatible; confluence.py only reads the keys above, unaffected.
        "bos_choch": _bos_choch(labels, event),
        "buy_side_liquidity": liq_above,      # ICT framing: resting stops ABOVE price
        "sell_side_liquidity": liq_below,     # ICT framing: resting stops BELOW price
        "stop_hunts": _stop_hunt(candles, liq_above, liq_below),
        "fibonacci": fibonacci(highs, lows),
        "trendline": trendline(highs, lows, candles),
    }
