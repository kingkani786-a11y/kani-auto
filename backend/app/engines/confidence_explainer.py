"""AI Confidence Explainer.

Decomposes the confluence confidence into each directional engine's exact
contribution (toward the chosen side), so "58%" becomes "Trend +12, OI +10,
Greeks +8, Risk −4". Derivation-only — reads the same layer scores and weights
the gate already used.
"""
from __future__ import annotations

from typing import Any

from .confluence import WEIGHTS


def explain(layers: dict[str, Any], signal: dict[str, Any]) -> dict[str, Any]:
    direction = signal.get("direction") or "NEUTRAL"
    # WAIT/NO-TRADE signals carry direction "NONE" — fall back to the dominant
    # side, otherwise every contribution silently flips to the bear column
    if direction not in ("BULL", "BEAR"):
        direction = ("BULL" if float(signal.get("bull_score") or 0)
                     >= float(signal.get("bear_score") or 0) else "BEAR")
    if direction == "NEUTRAL" or not layers:
        return {"ready": False, "note": "No directional signal to explain yet"}

    key = "score_bull" if direction == "BULL" else "score_bear"
    try:
        from ..services import weight_approval
        mult = weight_approval.effective_multipliers()
    except Exception:
        mult = {}

    # V15 instrument-aware: option-only layers are excluded on chain-less
    # instruments — showing them as "+0" rows is noise, not explanation
    excluded = set((layers.get("_instrument_mode") or {}).get("excluded") or [])
    comps = []
    for eng, w in WEIGHTS.items():
        if eng in excluded:
            continue
        layer = layers.get(eng) or {}
        score = float(layer.get(key, 50))
        eff_w = w * mult.get(eng, 1.0)
        # contribution = how far this engine pushes the chosen side off neutral,
        # scaled so a strong layer reads ±5..10 (was /5 → unreadable ±0.x)
        contribution = round((score - 50) * eff_w * 2.0, 1)
        comps.append({"engine": eng, "score": round(score, 0),
                      "contribution": contribution,
                      "weight": round(eff_w, 3)})
    comps.sort(key=lambda c: c["contribution"], reverse=True)
    total = round(sum(c["contribution"] for c in comps), 1)
    return {
        "ready": True,
        "direction": direction,
        "confidence": int(signal.get("dynamic_confidence") or signal.get("confidence") or 0),
        "components": comps,
        "net_contribution": total,
        "note": "Per-engine push toward the chosen side (weighted). Positive = supports, negative = opposes.",
    }
