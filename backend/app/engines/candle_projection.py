"""AI Layer 6 — Probability Candle Projection.

Projects the next few candles FORWARD ONLY (never repaints completed candles)
from the already-computed expected move + scenario probabilities + trend. Gives
an expected path, a failure path, and a pullback path, each probability-tagged.
Derivation-only — no new data, no new indicators. Probabilities, never certainty.
"""
from __future__ import annotations

import math
from typing import Any


def project(spot: float, layers: dict[str, Any], tf_min: int = 5, n: int = 3) -> dict[str, Any]:
    if not spot:
        return {"ready": False, "note": "No spot yet."}
    L = layers or {}
    prob = L.get("probability") or {}
    trend = L.get("trend") or {}
    fut = (L.get("future") or {}).get("scenarios") or {}

    em = float(prob.get("expected_move") or 0) or spot * 0.004   # session expected move
    direction = trend.get("direction") or "NEUTRAL"
    d = 1 if direction == "BULL" else -1 if direction == "BEAR" else 0
    band = em * 0.18                                             # per-candle range band

    p_primary = float((fut.get("bullish" if d >= 0 else "bearish") or {}).get("probability") or 50)
    p_fail = float((fut.get("bearish" if d >= 0 else "bullish") or {}).get("probability") or 25)
    p_alt = float((fut.get("range") or {}).get("probability") or 25)

    candles = []
    cone = []                                        # ★ Probability Cone (95% band)
    prev_c = spot
    for i in range(1, n + 1):
        cum = em * math.sqrt(i / n)                  # diminishing increments (sqrt-time)
        exp_close = round(spot + d * cum, 1)
        fail_close = round(spot - d * cum * 0.6, 1)  # failure path: opposite, smaller
        pull_close = round(spot + d * cum * 0.4, 1)  # pullback: partial follow-through
        # statistical cone: symmetric range that widens with time (~±1.4σ ≈ 95%)
        spread = em * math.sqrt(i / n) * 1.4
        cone.append({"i": i, "eta_min": tf_min * i,
                     "upper": round(spot + spread, 1), "lower": round(spot - spread, 1),
                     "mid": round(spot + d * cum, 1)})
        candles.append({
            "i": i, "eta_min": tf_min * i,
            "expected": {"open": round(prev_c, 1), "close": exp_close,
                         "high": round(max(prev_c, exp_close) + band, 1),
                         "low": round(min(prev_c, exp_close) - band, 1)},
            "failure_close": fail_close,
            "pullback_close": pull_close,
        })
        prev_c = exp_close

    return {
        "ready": d != 0,
        "direction": direction,
        "no_repaint": True,
        "spot": round(spot, 1),
        "expected_move": round(em, 1),
        "candles": candles,
        "cone": cone,
        "cone_95_range": ([cone[-1]["lower"], cone[-1]["upper"]] if cone else None),
        "paths": {
            "primary": {"probability": round(p_primary, 0), "target": candles[-1]["expected"]["close"]},
            "alternative": {"probability": round(p_alt, 0), "target": round(spot, 1)},
            "failure": {"probability": round(p_fail, 0), "target": candles[-1]["failure_close"]},
        },
        "note": "Forward-only projection from expected move + scenarios; ghost candles never repaint. "
                "Probabilities, not certainty.",
    }
