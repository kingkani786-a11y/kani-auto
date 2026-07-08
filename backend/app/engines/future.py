"""Forward Intelligence (Layers 9/10/11/6) — derivation-only, probability-based.

Scenario Simulation, Next-Move Probability, Time-to-Event, and the Buyer-vs-
Seller War Room. Everything is derived from layers the platform already
computed (regime, trend, structure, order flow, smart money, probability) —
no new market data, no new signal logic. Outputs are ALWAYS probabilities /
confidence / time-windows, never guarantees of direction, tops or bottoms.
"""
from __future__ import annotations

from typing import Any


def _norm3(bull: float, rng: float, bear: float) -> tuple[int, int, int]:
    tot = bull + rng + bear or 1
    b, r, s = round(bull / tot * 100), round(rng / tot * 100), round(bear / tot * 100)
    # fix rounding drift to sum 100
    d = 100 - (b + r + s)
    r += d
    return b, r, s


def scenarios(layers: dict[str, Any], spot: float) -> dict[str, Any]:
    trend = layers.get("trend", {})
    struct = layers.get("structure", {})
    regime = layers.get("regime", {}).get("regime", "")
    adx = float(trend.get("adx") or 0)
    bull_s = float(layers.get("trend", {}).get("score_bull") or 50)
    bear_s = float(layers.get("trend", {}).get("score_bear") or 50)

    # range weight rises in low-ADX / range regimes, falls in trends
    range_w = 60 if regime in ("RANGE_BOUND", "LOW_MOMENTUM") else 40 if adx < 20 else 20
    bull = bull_s * (0.6 if regime in ("RANGE_BOUND",) else 1.0)
    bear = bear_s * (0.6 if regime in ("RANGE_BOUND",) else 1.0)
    b, r, s = _norm3(bull, range_w, bear)

    conf = round(min(90, 45 + abs(b - s) * 0.5 + max(adx - 18, 0)), 0)
    res, sup = struct.get("resistance"), struct.get("support")
    return {
        "bullish": {"probability": b, "confidence": conf,
                    "invalidation": sup, "note": "Holds above support, reclaims VWAP"},
        "range": {"probability": r, "confidence": conf,
                  "invalidation": "Break of either S/R", "note": "Rotates between S/R"},
        "bearish": {"probability": s, "confidence": conf,
                    "invalidation": res, "note": "Holds below resistance, loses VWAP"},
        "primary": "bullish" if b >= max(r, s) else "bearish" if s >= max(b, r) else "range",
    }


def next_move(layers: dict[str, Any]) -> dict[str, Any]:
    trend = layers.get("trend", {})
    adx = float(trend.get("adx") or 0)
    direction = trend.get("direction", "NEUTRAL")
    of = float(layers.get("order_flow", {}).get("score") or 50)
    lean = 1 if direction == "BULL" else -1 if direction == "BEAR" else 0
    # shorter horizons: more range/noise; longer: trend asserts (if ADX strong)
    out = {}
    for label, horizon_w in (("5m", 0.4), ("15m", 0.7), ("30m", 1.0), ("60m", 1.3)):
        trend_push = lean * (adx / 30) * horizon_w * 40 + (of - 50) * 0.3
        bull = 50 + trend_push
        bear = 50 - trend_push
        rng = max(10, 45 - max(adx - 18, 0) * horizon_w)   # range shrinks as trend strengthens
        b, r, sx = _norm3(max(bull, 1), rng, max(bear, 1))
        out[label] = {"bullish": b, "range": r, "bearish": sx}
    return out


def time_to_event(layers: dict[str, Any], spot: float, signal: dict[str, Any]) -> dict[str, Any]:
    atr = float((signal.get("tech") or {}).get("atr") or 0)
    # 1m pace proxy: ATR(5m) / 5 ≈ points per minute (very rough)
    ppm = max(atr / 5, spot * 0.00005) if atr else spot * 0.00005
    struct = layers.get("structure", {})
    res, sup = struct.get("resistance"), struct.get("support")
    direction = layers.get("trend", {}).get("direction", "NEUTRAL")
    target_level = res if direction == "BULL" else sup if direction == "BEAR" else None

    def eta(level):
        if not level or not spot or ppm <= 0:
            return None
        return round(abs(level - spot) / ppm, 0)

    rev_risk = layers.get("capital_protection", {}).get("reversal_risk", 0)
    phases = layers.get("regime", {}).get("phases", [])
    return {
        "breakout": {"eta_min": eta(res if direction != "BEAR" else sup),
                     "confidence": round(min(80, 40 + max(float(layers.get('trend',{}).get('adx') or 0) - 18, 0) * 2), 0)},
        "profit_booking": {"eta_min": eta(target_level), "confidence": 55},
        "reversal": {"eta_min": (round(20 + (100 - rev_risk) * 0.5, 0) if rev_risk else None),
                     "confidence": round(min(75, rev_risk), 0)},
        "trend_exhaustion": {"likely": "TREND_EXHAUSTION" in phases or rev_risk >= 60,
                             "confidence": round(min(80, rev_risk + 10), 0)},
    }


def war_room(layers: dict[str, Any]) -> dict[str, Any]:
    of = layers.get("order_flow", {})
    sm = layers.get("smart_money", {})
    trend = layers.get("trend", {})
    oi = layers.get("oi", {})
    ofs = float(of.get("score") or 50)
    acts = sm.get("activities", [])
    events = sm.get("events", [])

    buyer = 50 + (ofs - 50)
    if trend.get("direction") == "BULL":
        buyer += 12
    if "PUT_WRITING" in acts:
        buyer += 10
    if "INSTITUTIONAL_BUYING" in events:
        buyer += 10
    seller = 100 - buyer
    if "CALL_WRITING" in acts:
        seller += 8; buyer -= 8
    buyer = max(0, min(100, buyer)); seller = max(0, min(100, 100 - buyer))

    dominance = "BUYERS" if buyer - seller >= 15 else "SELLERS" if seller - buyer >= 15 else "BALANCED"
    trapped = None
    if "LIQUIDITY_SWEEP_HIGH" in events:
        trapped = "Breakout buyers trapped (swept highs, rejected)"
    elif "LIQUIDITY_SWEEP_LOW" in events:
        trapped = "Breakdown sellers trapped (swept lows, reclaimed)"
    absorption = "ABSORPTION" in events
    exhaustion = any("EXHAUSTION" in e for e in events)
    return {
        "buyer_strength": round(buyer, 0),
        "seller_strength": round(seller, 0),
        "dominance": dominance,
        "winning": dominance, "losing": "SELLERS" if dominance == "BUYERS" else "BUYERS" if dominance == "SELLERS" else "—",
        "trapped": trapped or "None detected",
        "absorption": absorption,
        "exhaustion": exhaustion,
        "delta_imbalance": of.get("delta_imbalance", 0),
        "pcr": oi.get("pcr"),
    }


def roadmap(layers: dict[str, Any], spot: float, signal: dict[str, Any], nm: dict[str, Any]) -> list[dict]:
    """Per-horizon projected price + probability (M2 probability tree). The
    projection is expected-move-scaled by horizon and lean — a probabilistic
    path, never a guaranteed price."""
    atr = float((signal.get("tech") or {}).get("atr") or 0)
    direction = layers.get("trend", {}).get("direction", "NEUTRAL")
    d = 1 if direction == "BULL" else -1 if direction == "BEAR" else 0
    out = []
    for label, mult in (("5m", 0.35), ("15m", 0.6), ("30m", 0.9), ("60m", 1.3)):
        hb = (nm.get(label) or {})
        lean_prob = max(hb.get("bullish", 33), hb.get("bearish", 33))
        proj = round(spot + d * atr * mult, 1) if (spot and atr) else None
        out.append({"horizon": label, "projected": proj, "probability": lean_prob,
                    "bias": "up" if d > 0 else "down" if d < 0 else "flat"})
    return out


def analyze(layers: dict[str, Any], spot: float, signal: dict[str, Any]) -> dict[str, Any]:
    nm = next_move(layers)
    return {
        "scenarios": scenarios(layers, spot),
        "next_move": nm,
        "roadmap": roadmap(layers, spot, signal, nm),
        "time_to_event": time_to_event(layers, spot, signal),
        "war_room": war_room(layers),
    }
