"""Phase 27 — Entry Zone Engine.

Classifies the *quality of entering right now* into BEST / GOOD / LATE / AVOID
from already-computed state (trend, VWAP distance, structure room, entry
readiness). Derivation-only — no new data. It rates the entry timing, not the
direction (direction is the confluence engine's job). Edge, not certainty.
"""
from __future__ import annotations

from typing import Any


def classify(layers: dict[str, Any], signal: dict[str, Any], spot: float) -> dict[str, Any]:
    trend = layers.get("trend") or {}
    structure = layers.get("structure") or {}
    entryp = layers.get("entry_probability") or {}
    direction = signal.get("direction") or trend.get("direction") or "NEUTRAL"

    if not spot or direction == "NEUTRAL" or signal.get("signal") in (None, "NO TRADE"):
        return {"zone": "AVOID ENTRY", "score": 0,
                "reason": "No qualifying directional setup — wait for confluence.",
                "factors": [], "ready": True}

    score = 50.0
    factors: list[str] = []
    d = 1 if direction == "BULL" else -1

    # 1) trend alignment
    if trend.get("direction") == direction:
        score += 14; factors.append("Trend aligned (+)")
    elif trend.get("direction") in ("BULL", "BEAR"):
        score -= 16; factors.append("Against trend (−)")

    # 2) VWAP distance — entering near VWAP on the right side is a better price;
    #    far-extended from VWAP = chasing (LATE).
    vwap = float(trend.get("vwap") or 0)
    atr = float((signal.get("tech") or {}).get("atr") or 0)
    if vwap and atr:
        ext = (spot - vwap) * d / atr          # extension in ATRs in trade direction
        if ext <= 0.3:
            score += 16; factors.append("Near VWAP — good price (+)")
        elif ext <= 1.0:
            score += 6; factors.append("Mild extension (+)")
        elif ext <= 2.0:
            score -= 10; factors.append("Extended from VWAP — chasing (−)")
        else:
            score -= 20; factors.append("Very extended — late (−)")

    # 3) structure room to the next barrier (more room = better entry)
    barrier = structure.get("resistance") if direction == "BULL" else structure.get("support")
    try:
        room = abs(float(barrier) - spot)
        if atr and room / atr >= 1.5:
            score += 12; factors.append("Room to target (+)")
        elif atr and room / atr < 0.6:
            score -= 14; factors.append("Barrier overhead — little room (−)")
    except (TypeError, ValueError):
        pass

    # 4) entry readiness (institutional entry-probability layer)
    escore = float(entryp.get("score") or 0)
    if escore:
        if escore >= 70:
            score += 12; factors.append("High entry readiness (+)")
        elif escore < 45:
            score -= 10; factors.append("Low entry readiness (−)")

    score = max(0.0, min(100.0, score))
    zone = ("BEST ENTRY" if score >= 75 else "GOOD ENTRY" if score >= 58
            else "LATE ENTRY" if score >= 42 else "AVOID ENTRY")
    pos = [f for f in factors if f.endswith("(+)")]
    neg = [f for f in factors if f.endswith("(−)")]
    reason = (("; ".join(p[:-4] for p in pos[:2]) or "neutral setup")
              + (" — but " + "; ".join(n[:-4] for n in neg[:2]) if neg else ""))
    return {"zone": zone, "score": round(score, 0), "reason": reason,
            "factors": factors, "ready": True}
