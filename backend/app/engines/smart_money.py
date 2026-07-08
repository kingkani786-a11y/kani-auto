"""Smart-money flow classification from price + OI deltas.

Futures/underlying:        price up  + OI up   -> LONG_BUILDUP
                           price dn  + OI up   -> SHORT_BUILDUP
                           price up  + OI dn   -> SHORT_COVERING
                           price dn  + OI dn   -> LONG_UNWINDING
Options (per side): OI up + premium dn -> writing (CE writing bearish,
PE writing bullish); OI dn + premium up on the dominant side -> covering.
"""
from __future__ import annotations

from typing import Any


def classify_underlying(price_chg_pct: float, oi_chg_pct: float) -> str:
    if abs(price_chg_pct) < 0.02 and abs(oi_chg_pct) < 0.1:
        return "NEUTRAL"
    if price_chg_pct >= 0 and oi_chg_pct >= 0:
        return "LONG_BUILDUP"
    if price_chg_pct < 0 and oi_chg_pct >= 0:
        return "SHORT_BUILDUP"
    if price_chg_pct >= 0 and oi_chg_pct < 0:
        return "SHORT_COVERING"
    return "LONG_UNWINDING"


def analyze_option_flow(analytics: dict[str, Any]) -> dict[str, Any]:
    """Detect call/put writing and unwinding from chain-level OI shifts."""
    if not analytics:
        return {"activities": [], "bias": "NEUTRAL"}

    ce_chg = analytics.get("call_oi_change", 0.0)
    pe_chg = analytics.get("put_oi_change", 0.0)
    call_oi = max(analytics.get("call_oi", 1.0), 1.0)
    put_oi = max(analytics.get("put_oi", 1.0), 1.0)

    activities: list[str] = []
    score = 0  # + bullish / - bearish

    if pe_chg > 0.005 * put_oi:
        activities.append("PUT_WRITING")          # sellers confident of support
        score += 2
    if ce_chg > 0.005 * call_oi:
        activities.append("CALL_WRITING")         # sellers capping upside
        score -= 2
    if ce_chg < -0.005 * call_oi:
        activities.append("SHORT_COVERING")       # call shorts exiting
        score += 1
    if pe_chg < -0.005 * put_oi:
        activities.append("LONG_UNWINDING")       # put shorts exiting / support fading
        score -= 1

    pcr = analytics.get("pcr", 1.0)
    if pcr > 1.2:
        score += 1
    elif pcr < 0.8:
        score -= 1

    bias = "BULLISH" if score >= 2 else "BEARISH" if score <= -2 else "NEUTRAL"
    return {"activities": activities, "bias": bias, "score": score}


def analyze_tape(candles: list[dict], structure: dict[str, Any]) -> dict[str, Any]:
    """Layer 4 tape-reading: institutional prints, absorption, exhaustion,
    liquidity sweeps and false breakouts from candle/volume behaviour."""
    if len(candles) < 30:
        return {"events": [], "score_bull": 50, "score_bear": 50, "notes": []}

    vols = [max(float(c.get("volume", 0)), 0.0) for c in candles]
    avg_vol = sum(vols[-30:]) / 30 or 1.0
    events: list[str] = []
    notes: list[str] = []
    bull = bear = 50.0

    last5 = candles[-5:]
    for c in last5:
        v = max(float(c.get("volume", 0)), 0.0)
        rng = max(c["high"] - c["low"], 1e-9)
        body = c["close"] - c["open"]
        big = v > 2.2 * avg_vol

        if big and body > 0.55 * rng:
            if "INSTITUTIONAL_BUYING" not in events:
                events.append("INSTITUTIONAL_BUYING")
                notes.append("Heavy volume with strong closes — institutional buying prints")
            bull += 7
        elif big and body < -0.55 * rng:
            if "INSTITUTIONAL_SELLING" not in events:
                events.append("INSTITUTIONAL_SELLING")
                notes.append("Heavy volume with weak closes — institutional selling prints")
            bear += 7
        elif big and abs(body) < 0.25 * rng:
            # huge effort, no result = absorption at this level
            if "ABSORPTION" not in events:
                events.append("ABSORPTION")
                notes.append("High volume absorbed without price progress")

    # Exhaustion: extended move + climax volume + reversal bar
    closes = [c["close"] for c in candles]
    run = (closes[-1] / closes[-12] - 1) * 100 if closes[-12] else 0.0
    last = candles[-1]
    rng = max(last["high"] - last["low"], 1e-9)
    if run > 0.6 and vols[-1] > 2.5 * avg_vol and (last["high"] - last["close"]) / rng > 0.6:
        events.append("EXHAUSTION_TOP")
        bear += 10
        notes.append("Up-move exhaustion: climax volume with rejection wick")
    if run < -0.6 and vols[-1] > 2.5 * avg_vol and (last["close"] - last["low"]) / rng > 0.6:
        events.append("EXHAUSTION_BOTTOM")
        bull += 10
        notes.append("Down-move exhaustion: climax volume with demand wick")

    # Liquidity sweep / false breakout vs structure levels
    res = structure.get("resistance") or 0
    sup = structure.get("support") or 0
    if res and last["high"] > res and last["close"] < res:
        events.append("LIQUIDITY_SWEEP_HIGH")
        bear += 9
        notes.append(f"Liquidity sweep above {round(res, 1)} then rejection — false breakout")
    if sup and last["low"] < sup and last["close"] > sup:
        events.append("LIQUIDITY_SWEEP_LOW")
        bull += 9
        notes.append(f"Liquidity sweep below {round(sup, 1)} then reclaim — false breakdown")

    bull, bear = max(0, min(100, bull)), max(0, min(100, bear))
    return {"events": events, "score_bull": round(bull, 1), "score_bear": round(bear, 1), "notes": notes}
