"""No-Trade-Zone + Trap Detection engines (V13).

Both are protective/informational layers built from signals the platform
already computes (structure, order flow, smart money, regime, volume
profile). They make hostile conditions explicit so the trader — and the
safety gate — can stand aside.
"""
from __future__ import annotations

from typing import Any


def no_trade_zone(layers: dict[str, Any], spot: float) -> dict[str, Any]:
    """ACTIVE when conditions are structurally untradeable."""
    reasons: list[str] = []
    regime = (layers.get("regime") or {}).get("regime", "")
    of = layers.get("order_flow") or {}
    trend = layers.get("trend") or {}
    vp = layers.get("volume_profile") or {}

    # low volume / no participation
    if "LIQUIDITY_VACUUM" in of.get("events", []):
        reasons.append("Liquidity vacuum — thin participation")
    # VWAP chop: price hugging VWAP with weak ADX
    vwap = float(trend.get("vwap") or 0)
    adx = float(trend.get("adx") or 0)
    if vwap and spot and abs(spot - vwap) / spot < 0.0008 and adx < 18:
        reasons.append("Price pinned to VWAP with weak ADX — chop")
    # mixed delta / order flow (no conviction)
    if of.get("delta_imbalance") is not None and abs(of["delta_imbalance"]) < 0.05:
        reasons.append("Mixed order flow — buyers and sellers balanced")
    # mixed/neutral trend
    if trend.get("direction") == "NEUTRAL" and adx < 18:
        reasons.append("No trend — directionless tape")
    # sideways regime
    if regime in ("RANGE_BOUND", "LOW_MOMENTUM"):
        reasons.append("Range-bound regime")
    # value-area rotation (gamma/compression proxy)
    if vp.get("state") == "INSIDE_VALUE" and adx < 18:
        reasons.append("Rotating inside value area — compression")

    active = len(reasons) >= 2          # need ≥2 corroborating conditions
    return {
        "status": "ACTIVE" if active else "INACTIVE",
        "active": active,
        "reasons": reasons[:4] if active else [],
        "reason": reasons[0] if active else "Conditions tradeable",
    }


def traps(layers: dict[str, Any], spot: float) -> dict[str, Any]:
    """Detect bull/bear traps, liquidity traps, false breakouts, fake gamma."""
    sm = layers.get("smart_money") or {}
    struct = layers.get("structure") or {}
    of = layers.get("order_flow") or {}
    events = sm.get("events", [])

    found: list[str] = []
    score = 0.0

    if "LIQUIDITY_SWEEP_HIGH" in events:
        found.append("BEAR_TRAP"); found.append("FALSE_BREAKOUT"); score += 35
    if "LIQUIDITY_SWEEP_LOW" in events:
        found.append("BULL_TRAP"); found.append("FALSE_BREAKOUT"); score += 35
    # exhaustion right at a breakout = trap risk
    if struct.get("event") == "BREAKOUT" and "EXHAUSTION_TOP" in events:
        found.append("BULL_TRAP"); score += 25
    if struct.get("event") == "BREAKDOWN" and "EXHAUSTION_BOTTOM" in events:
        found.append("BEAR_TRAP"); score += 25
    # liquidity trap: vacuum + sweep
    if "LIQUIDITY_VACUUM" in of.get("events", []) and any("SWEEP" in e for e in events):
        found.append("LIQUIDITY_TRAP"); score += 20
    # fake gamma expansion: gamma-squeeze phase but flow not confirming
    phases = (layers.get("regime") or {}).get("phases", [])
    if "GAMMA_SQUEEZE" in phases and of.get("score", 50) < 55:
        found.append("FAKE_GAMMA_EXPANSION"); score += 20

    score = min(100.0, score)
    confidence = min(100.0, score * 1.1) if found else 0.0
    uniq = sorted(set(found))
    return {
        "traps": uniq,
        "trap_score": round(score, 0),
        "trap_confidence": round(confidence, 0),
        "detected": bool(uniq),
        "summary": ", ".join(t.replace("_", " ").title() for t in uniq) if uniq else "No traps detected",
    }
