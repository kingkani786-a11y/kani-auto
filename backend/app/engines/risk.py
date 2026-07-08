"""Risk Engine — qualifies every signal and warns on hostile conditions."""
from __future__ import annotations

from typing import Any


def assess(
    signal: dict[str, Any],
    tech: dict[str, Any],
    data_quality: str,
    spot: float,
) -> dict[str, Any]:
    confidence = float(signal.get("confidence") or 0)
    adx_v = float(tech.get("adx") or 0)
    atr_v = float(tech.get("atr") or 0)
    atr_pct = (atr_v / spot * 100) if spot else 0.0

    volatility = "HIGH" if atr_pct > 0.9 else "ELEVATED" if atr_pct > 0.45 else "NORMAL"
    trend_strength = "STRONG" if adx_v >= 25 else "MODERATE" if adx_v >= 18 else "WEAK"

    warnings: list[str] = []
    if adx_v < 18:
        warnings.append("Market is choppy (ADX < 18) — trend signals unreliable")
    if data_quality != "GOOD":
        warnings.append(f"Data quality is {data_quality} — treat all metrics with caution")
    if 0 < confidence < 60:
        warnings.append("Confidence is low — consider standing aside")
    if volatility == "HIGH":
        warnings.append("Volatility is high — widen stops or reduce size")

    if signal.get("signal") == "NO TRADE":
        level = "NONE"
    elif confidence >= 80 and trend_strength == "STRONG" and not warnings:
        level = "LOW"
    elif confidence >= 70 and adx_v >= 20:
        level = "MEDIUM"
    else:
        level = "HIGH"

    return {
        "risk_level": level,
        "confidence": confidence,
        "trend_strength": trend_strength,
        "adx": round(adx_v, 1),
        "volatility": volatility,
        "atr_pct": round(atr_pct, 2),
        "data_quality": data_quality,
        "warnings": warnings,
    }
