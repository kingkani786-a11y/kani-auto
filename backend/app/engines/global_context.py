"""Global Context, VIX Correlation, and GIFT NIFTY Correlation engines (V11).

These read India VIX + GIFT + the existing layer scores and produce a
top-down market backdrop. All degrade to NEUTRAL when a feed is missing —
they never block trading on data the broker can't supply, and never fabricate.
"""
from __future__ import annotations

from typing import Any


def vix_correlation(spot_trend: str, vix: dict[str, Any], adx: float) -> dict[str, Any]:
    """Volatility risk / expected move / trend reliability from India VIX."""
    v = vix.get("value")
    if v is None:
        return {"available": False, "volatility_risk": 50, "expected_move_score": 50,
                "trend_reliability": 50, "vix": None, "note": "India VIX unavailable"}

    prev = vix.get("prev") or v
    rising = v > prev * 1.02
    falling = v < prev * 0.98

    # higher VIX -> higher volatility risk and bigger expected move
    volatility_risk = max(0, min(100, (v - 10) / 25 * 100))      # 10→0, 35→100
    expected_move_score = volatility_risk
    # trend reliability: best when VIX is low/compressing and ADX strong
    trend_reliability = max(0, min(100, 60 + (adx - 20) * 1.5 - (volatility_risk - 50) * 0.4))
    if rising:
        trend_reliability -= 10
    elif falling:
        trend_reliability += 8

    state = "VIX_EXPANSION" if rising else "VIX_COMPRESSION" if falling else "VIX_STABLE"
    notes = []
    if v > 20 and rising:
        notes.append(f"India VIX {v} and rising — elevated risk, widen stops / reduce size")
    elif v < 13 and falling:
        notes.append(f"India VIX {v} and compressing — calm tape, trends more reliable")
    return {
        "available": True, "vix": v, "state": state,
        "volatility_risk": round(volatility_risk, 0),
        "expected_move_score": round(expected_move_score, 0),
        "trend_reliability": round(max(0, min(100, trend_reliability)), 0),
        "notes": notes,
    }


def gift_correlation(gift: dict[str, Any], spot_dir: str) -> dict[str, Any]:
    """Gap confidence / opening direction / opening risk from GIFT NIFTY.
    Reported unavailable when there's no feed — pre-open only signal anyway."""
    if not gift.get("available") or gift.get("value") is None:
        return {"available": False, "gap_confidence": 50, "opening_direction": "NEUTRAL",
                "opening_risk": 50, "note": "GIFT NIFTY feed not available via broker"}
    val, prev = gift["value"], gift.get("prev_close") or gift["value"]
    gap_pct = (val / prev - 1) * 100 if prev else 0.0
    direction = "BULLISH" if gap_pct > 0.15 else "BEARISH" if gap_pct < -0.15 else "NEUTRAL"
    gap_confidence = min(100, abs(gap_pct) * 40 + 40)
    opening_risk = min(100, abs(gap_pct) * 30)
    return {
        "available": True, "gap_pct": round(gap_pct, 2),
        "gap_confidence": round(gap_confidence, 0),
        "opening_direction": direction,
        "opening_risk": round(opening_risk, 0),
    }


def global_context(vix_corr: dict[str, Any], gift_corr: dict[str, Any],
                   layer_dir: str, regime: str) -> dict[str, Any]:
    """Top-down verdict: Bullish/Bearish/Neutral + Favorable/Risky/Neutral."""
    bias = "NEUTRAL"
    if gift_corr.get("available") and gift_corr["opening_direction"] != "NEUTRAL":
        bias = gift_corr["opening_direction"]
    elif layer_dir in ("BULL", "BULLISH"):
        bias = "BULLISH"
    elif layer_dir in ("BEAR", "BEARISH"):
        bias = "BEARISH"

    vol_risk = vix_corr.get("volatility_risk", 50)
    open_risk = gift_corr.get("opening_risk", 0) if gift_corr.get("available") else 0
    risk_level = max(vol_risk, open_risk)
    condition = ("RISKY" if risk_level > 70 or regime in ("VOLATILE", "EXPIRY_PINNING")
                 else "FAVORABLE" if risk_level < 45 and regime in ("TRENDING", "HIGH_MOMENTUM")
                 else "NEUTRAL")

    notes = list(vix_corr.get("notes", []))
    if gift_corr.get("available") and gift_corr["opening_direction"] != "NEUTRAL":
        notes.append(f"GIFT NIFTY points to a {gift_corr['opening_direction'].lower()} open "
                     f"({gift_corr['gap_pct']:+.2f}%)")
    return {
        "bias": bias,
        "condition": condition,
        "risk_level": round(risk_level, 0),
        "expected_move_score": vix_corr.get("expected_move_score", 50),
        "notes": notes[:3],
    }
