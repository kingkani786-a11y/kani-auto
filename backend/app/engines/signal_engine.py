"""AI Signal Engine — weighted multi-factor scoring.

A signal is NEVER produced from a single indicator. Seven factor scores
(each 0–100) are blended with fixed weights for a bullish and a bearish
composite; a signal fires only when the winning composite clears the
configurable confidence threshold AND beats the opposing composite by a
margin. Each factor also emits a human-readable reason for the
AI Explanation panel.
"""
from __future__ import annotations

from typing import Any

from ..config import settings

WEIGHTS = {
    "greeks": 0.25,
    "oi": 0.20,
    "pcr": 0.15,
    "trend": 0.15,
    "vwap": 0.10,
    "adx": 0.10,
    "volume": 0.05,
}


def _clamp(x: float, lo: float = 0.0, hi: float = 100.0) -> float:
    return max(lo, min(hi, x))


def score_factors(
    spot: float,
    analytics: dict[str, Any],      # option-chain digest (may be {} for commodities)
    tech: dict[str, Any],           # ema/vwap/adx/atr/momentum block
    smart: dict[str, Any],
) -> tuple[dict, dict, list[str], list[str]]:
    bull: dict[str, float] = {}
    bear: dict[str, float] = {}
    bull_why: list[str] = []
    bear_why: list[str] = []

    # ---- Greeks (25%): ATM delta balance + theta pressure ----
    g = analytics.get("greeks", {})
    ce_d = abs(float(g.get("ce", {}).get("delta") or 0.5))
    pe_d = abs(float(g.get("pe", {}).get("delta") or 0.5))
    skew = ce_d - pe_d  # >0: market pricing upside
    bull["greeks"] = _clamp(50 + skew * 250)
    bear["greeks"] = _clamp(50 - skew * 250)
    if skew > 0.04:
        bull_why.append("Positive delta skew — calls pricing in upside")
    elif skew < -0.04:
        bear_why.append("Negative delta skew — puts pricing in downside")

    # ---- OI (20%): writing/build-up structure ----
    s = smart.get("score", 0)
    bull["oi"] = _clamp(50 + s * 12)
    bear["oi"] = _clamp(50 - s * 12)
    if "PUT_WRITING" in smart.get("activities", []):
        bull_why.append("Put writing active — strong support being defended")
    if "CALL_WRITING" in smart.get("activities", []):
        bear_why.append("Call writing active — upside being capped")
    if "SHORT_COVERING" in smart.get("activities", []):
        bull_why.append("Short covering detected in calls")
    if smart.get("underlying") in ("LONG_BUILDUP",):
        bull_why.append("Long build-up: price and OI rising together")
    if smart.get("underlying") in ("SHORT_BUILDUP",):
        bear_why.append("Short build-up: price falling on rising OI")

    # ---- PCR (15%) ----
    pcr = float(analytics.get("pcr") or 1.0)
    bull["pcr"] = _clamp((pcr - 0.6) / 0.8 * 100)   # 0.6→0, 1.4→100
    bear["pcr"] = 100 - bull["pcr"]
    if pcr > 1.1:
        bull_why.append(f"PCR elevated at {pcr:.2f} — put base building")
    elif pcr < 0.9:
        bear_why.append(f"PCR depressed at {pcr:.2f} — call-heavy positioning")

    # ---- Trend (15%): EMA regime ----
    trend = tech.get("trend", "NEUTRAL")
    bull["trend"] = 80.0 if trend == "BULLISH" else 20.0 if trend == "BEARISH" else 50.0
    bear["trend"] = 100 - bull["trend"]
    if trend == "BULLISH":
        bull_why.append("EMA trend aligned bullish (9 over 21, price above)")
    elif trend == "BEARISH":
        bear_why.append("EMA trend aligned bearish (9 under 21, price below)")

    # ---- VWAP (10%) ----
    vwap_v = float(tech.get("vwap") or 0)
    if vwap_v > 0 and spot > 0:
        dist = (spot - vwap_v) / vwap_v * 100
        bull["vwap"] = _clamp(50 + dist * 40)
        bear["vwap"] = _clamp(50 - dist * 40)
        if dist > 0.05:
            bull_why.append("Price holding above VWAP — buyers in control")
        elif dist < -0.05:
            bear_why.append("Price rejected below VWAP — sellers in control")
    else:
        bull["vwap"] = bear["vwap"] = 50.0

    # ---- ADX (10%): strength amplifies the trend side only ----
    adx_v = float(tech.get("adx") or 0)
    strength = _clamp((adx_v - 15) / 25 * 100)
    if trend == "BULLISH":
        bull["adx"], bear["adx"] = strength, 100 - strength
        if adx_v > 25:
            bull_why.append(f"ADX {adx_v:.0f} — trend strength increasing")
    elif trend == "BEARISH":
        bear["adx"], bull["adx"] = strength, 100 - strength
        if adx_v > 25:
            bear_why.append(f"ADX {adx_v:.0f} — downtrend gathering strength")
    else:
        bull["adx"] = bear["adx"] = 35.0  # choppy: penalize both sides

    # ---- Volume (5%) ----
    mom = float(tech.get("momentum") or 0)
    vol_exp = bool(tech.get("volume_expansion"))
    base = 65.0 if vol_exp else 45.0
    bull["volume"] = _clamp(base + mom * 10) if mom >= 0 else _clamp(45 + mom * 10)
    bear["volume"] = 100 - bull["volume"]
    if vol_exp and mom > 0:
        bull_why.append("Volume expansion on up-move detected")
    elif vol_exp and mom < 0:
        bear_why.append("Volume expansion on down-move detected")

    return bull, bear, bull_why, bear_why


def generate_signal(
    spot: float,
    market_type: str,
    analytics: dict[str, Any],
    tech: dict[str, Any],
    smart: dict[str, Any],
    threshold: float | None = None,
) -> dict[str, Any]:
    threshold = threshold if threshold is not None else settings.confidence_threshold
    bull, bear, bull_why, bear_why = score_factors(spot, analytics, tech, smart)

    bull_score = sum(bull[k] * w for k, w in WEIGHTS.items())
    bear_score = sum(bear[k] * w for k, w in WEIGHTS.items())

    direction, confidence, reasons = "NONE", 0.0, []
    if bull_score >= threshold and bull_score - bear_score >= 10:
        direction, confidence, reasons = "BULL", bull_score, bull_why
    elif bear_score >= threshold and bear_score - bull_score >= 10:
        direction, confidence, reasons = "BEAR", bear_score, bear_why

    atr_v = max(float(tech.get("atr") or 0), spot * 0.0015)

    if direction == "NONE":
        return {
            "signal": "NO TRADE",
            "confidence": round(max(bull_score, bear_score), 1),
            "bull_score": round(bull_score, 1),
            "bear_score": round(bear_score, 1),
            "factors": {"bull": bull, "bear": bear},
            "reasons": ["Confluence below threshold — capital protection mode"],
        }

    # V25 — capability-based, never market-type based: options wherever a chain exists
    if market_type == "INDEX" or (analytics or {}).get("chain"):
        sig = "BUY CE" if direction == "BULL" else "BUY PE"
    else:
        sig = "BUY FUTURES" if direction == "BULL" else "SELL FUTURES"

    # Underlying-level levels (option entry premium shown separately by UI)
    if direction == "BULL":
        entry, sl = spot, spot - 1.2 * atr_v
        targets = [spot + r * atr_v for r in (1.5, 2.5, 4.0)]
    else:
        entry, sl = spot, spot + 1.2 * atr_v
        targets = [spot - r * atr_v for r in (1.5, 2.5, 4.0)]

    risk = abs(entry - sl)
    rr = abs(targets[1] - entry) / risk if risk else 0.0

    return {
        "signal": sig,
        "direction": direction,
        "entry": round(entry, 2),
        "stop_loss": round(sl, 2),
        "target1": round(targets[0], 2),
        "target2": round(targets[1], 2),
        "target3": round(targets[2], 2),
        "confidence": round(confidence, 1),
        "bull_score": round(bull_score, 1),
        "bear_score": round(bear_score, 1),
        "reward_risk": round(rr, 2),
        "factors": {"bull": {k: round(v, 1) for k, v in bull.items()},
                    "bear": {k: round(v, 1) for k, v in bear.items()}},
        "reasons": reasons,
    }
