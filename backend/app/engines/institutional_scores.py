"""V11 institutional scoring engines.

All consume scores the confluence engine already produced (no new market
calls) plus the V11 context. Pure, testable functions.
"""
from __future__ import annotations

from typing import Any


def market_strength(layers: dict[str, Any], breadth: dict[str, Any] | None) -> dict[str, Any]:
    """0–100 strength from trend, volume, OI, breadth, liquidity, momentum."""
    trend = layers.get("trend", {})
    of = layers.get("order_flow", {})
    oi = layers.get("oi", {})
    dom = layers.get("dom", {})
    tech = layers.get("_tech", {})

    direction = trend.get("direction", "NEUTRAL")
    side = "score_bull" if direction == "BULL" else "score_bear"
    parts = {
        "trend": trend.get(side, 50),
        "volume": of.get("score", 50),
        "oi": oi.get(side, 50),
        "breadth": _breadth_score(breadth),
        "liquidity": dom.get("liquidity_score", 60) if dom.get("available") else 60,
        "momentum": min(100, 50 + abs(float(tech.get("momentum") or 0)) * 30),
    }
    score = sum(parts.values()) / len(parts)
    label = ("VERY_STRONG" if score >= 75 else "STRONG" if score >= 60
             else "MODERATE" if score >= 45 else "WEAK")
    return {"score": round(score, 0), "label": label, "components": {k: round(v, 0) for k, v in parts.items()},
            "direction": direction}


def _breadth_score(breadth: dict[str, Any] | None) -> float:
    if not breadth or not breadth.get("ratio"):
        return 50.0
    r = breadth["ratio"]
    return max(0.0, min(100.0, 50 + (r - 1) * 25))


def entry_probability(layers: dict[str, Any], vix_corr: dict[str, Any],
                      gift_corr: dict[str, Any], historical_accuracy: float | None,
                      session: dict[str, Any]) -> dict[str, Any]:
    """Institutional Entry Score 0–100 — multi-engine, never single-indicator."""
    direction = layers.get("trend", {}).get("direction", "NEUTRAL")
    side = "score_bull" if direction == "BULL" else "score_bear"
    g = lambda k, d=50: layers.get(k, {}).get(side, d)

    inputs = {
        "trend": g("trend"),
        "volume": layers.get("order_flow", {}).get("score", 50),
        "oi": g("oi"),
        "greeks": g("greeks"),
        "liquidity": layers.get("dom", {}).get("liquidity_score", 60)
        if layers.get("dom", {}).get("available") else 60,
        "structure": g("structure"),
        "mtf": layers.get("mtf", {}).get("alignment", 50),
        "vix": vix_corr.get("trend_reliability", 50),
        "gift": gift_corr.get("gap_confidence", 50) if gift_corr.get("available") else 50,
        "historical": historical_accuracy if historical_accuracy is not None else 55,
    }
    weights = {"trend": 0.16, "volume": 0.10, "oi": 0.14, "greeks": 0.10,
               "liquidity": 0.08, "structure": 0.14, "mtf": 0.12,
               "vix": 0.06, "gift": 0.04, "historical": 0.06}
    score = sum(inputs[k] * w for k, w in weights.items())
    if not session.get("favorable_for_entry", True):
        score -= 6                                  # poor session timing penalty
    score = max(0, min(100, score))

    band = ("INSTITUTIONAL" if score >= 91 else "HIGH" if score >= 76 else
            "MODERATE" if score >= 61 else "WAIT" if score >= 41 else "AVOID")
    label = {"INSTITUTIONAL": "91-100 Institutional Grade", "HIGH": "76-90 High Probability",
             "MODERATE": "61-75 Moderate", "WAIT": "41-60 Wait", "AVOID": "0-40 Avoid"}[band]
    return {"score": round(score, 0), "band": band, "label": label,
            "inputs": {k: round(v, 0) for k, v in inputs.items()}}


def trade_quality(grade: str, prob: float, dom: dict[str, Any],
                  historical_accuracy: float | None, mtf_alignment: float,
                  entry_band: str) -> dict[str, Any]:
    """A+ / A / B / C / Avoid from risk, probability, liquidity, history, MTF."""
    if grade in ("NO TRADE", ""):
        return {"grade": "Avoid", "reasons": ["No qualifying setup"]}
    score = 0.0
    score += {"A": 40, "B": 28, "C": 18}.get(grade, 0)
    score += min(prob, 100) * 0.25
    score += (historical_accuracy or 55) * 0.15
    score += min(mtf_alignment, 100) * 0.12
    if dom.get("available"):
        score += dom.get("liquidity_score", 60) * 0.08
    else:
        score += 50 * 0.08

    q = ("A+" if score >= 88 and entry_band in ("HIGH", "INSTITUTIONAL")
         else "A" if score >= 78 else "B" if score >= 65 else "C" if score >= 52 else "Avoid")
    reasons = [f"Prob {prob:.0f}%", f"MTF {mtf_alignment:.0f}%"]
    if historical_accuracy is not None:
        reasons.append(f"Hist {historical_accuracy:.0f}%")
    return {"grade": q, "score": round(score, 0), "reasons": reasons}


def institutional_activity(layers: dict[str, Any], analytics: dict[str, Any]) -> dict[str, Any]:
    """FII/DII bias is EOD-published (not in the realtime feed), so this is a
    DERIVED proxy from smart-money OI flow + order flow — labeled as such."""
    flow = layers.get("smart_money", {})
    of = layers.get("order_flow", {})
    score = 0
    acts = flow.get("activities", [])
    if "PUT_WRITING" in acts: score += 2
    if "CALL_WRITING" in acts: score -= 2
    if "SHORT_COVERING" in acts: score += 1
    if "LONG_UNWINDING" in acts: score -= 1
    if of.get("score", 50) > 60: score += 1
    elif of.get("score", 50) < 40: score -= 1
    pcr = analytics.get("pcr")
    if pcr and pcr > 1.2: score += 1
    elif pcr and pcr < 0.8: score -= 1

    bias = "BULLISH" if score >= 2 else "BEARISH" if score <= -2 else "NEUTRAL"
    pressure = min(100, abs(score) * 20)
    return {"bias": bias, "pressure": pressure, "source": "derived (OI flow + order flow)",
            "fii_bias": bias, "dii_bias": "NEUTRAL",
            "note": "Live FII/DII not in broker feed — derived from positioning"}


def future_path(layers: dict[str, Any], spot: float, levels: dict[str, Any]) -> dict[str, Any]:
    """Market Roadmap / Future Path — likely scenarios with concrete levels."""
    prob = layers.get("probability", {})
    struct = layers.get("structure", {})
    rng = prob.get("expected_range") or [None, None]
    res = struct.get("resistance") or levels.get("prev_day_high")
    sup = struct.get("support") or levels.get("prev_day_low")
    direction = layers.get("trend", {}).get("direction", "NEUTRAL")

    steps: list[str] = []
    if res and spot:
        steps.append(f"Above {res:,.0f} → momentum toward {(rng[1] or res):,.0f}")
    if sup and spot:
        steps.append(f"Below {sup:,.0f} → pressure toward {(rng[0] or sup):,.0f}")
    vwap = levels.get("vwap")
    if vwap:
        steps.append(f"VWAP {vwap:,.0f} is the intraday pivot — side of it sets the bias")

    primary = ("Higher — buyers in control" if direction == "BULL"
               else "Lower — sellers in control" if direction == "BEAR"
               else "Range-bound until a level breaks")
    return {"primary_path": primary, "scenarios": steps[:3],
            "expected_range": rng, "pivot": vwap}
