"""Phase 28 — Probability Ladder Engine.

Derivation-only: turns the already-computed expected move + edge into the
probability of *reaching* each target (T1/T2/T3) and of hitting the stop first.
No new data, no broker calls. These are touch-probabilities (reaching T2 implies
reaching T1, so they are NOT mutually exclusive and do not sum to 100). Edge,
not certainty.
"""
from __future__ import annotations

import math
from typing import Any


def _band(p: float) -> str:
    return ("VERY HIGH" if p >= 70 else "HIGH" if p >= 55
            else "MEDIUM" if p >= 40 else "LOW")


def compute(entry: float, stop: float, targets: list[float], direction: str,
            expected_move: float, prob_success: float) -> dict[str, Any]:
    """entry/stop/targets in price; expected_move ~1σ favourable session move;
    prob_success = overall edge (0-100) from the probability engine."""
    if not entry or not expected_move or expected_move <= 0:
        return {"ready": False, "note": "INSUFFICIENT DATA — no entry/expected move yet"}

    edge = max(0.05, min(0.95, prob_success / 100.0))
    d = 1 if direction == "BULL" else -1

    rungs = []
    for i, tgt in enumerate(targets, 1):
        if tgt is None:
            continue
        dist = (tgt - entry) * d            # favourable distance
        if dist <= 0:
            continue
        norm = dist / expected_move
        # touch probability: 100% at entry, decays with distance/σ, scaled by edge
        touch = 100.0 * math.exp(-0.6 * norm) * (0.55 + 0.45 * edge)
        touch = round(max(3.0, min(96.0, touch)), 0)
        rungs.append({"level": f"T{i}", "price": tgt, "distance": round(dist, 1),
                      "probability": touch, "band": _band(touch)})

    # keep monotonic (reaching a farther target can't be more likely than a nearer one)
    for i in range(1, len(rungs)):
        rungs[i]["probability"] = min(rungs[i]["probability"], rungs[i - 1]["probability"])
        rungs[i]["band"] = _band(rungs[i]["probability"])

    # stop-loss probability: closer stop + weaker edge ⇒ more likely to hit first
    sl_prob = None
    if stop is not None:
        s = abs(entry - stop)
        if s > 0:
            norm_s = s / expected_move
            sl = 100.0 * math.exp(-0.6 * norm_s) * (0.55 + 0.45 * (1 - edge))
            sl_prob = round(max(3.0, min(96.0, sl)), 0)

    return {
        "ready": True,
        "rungs": rungs,
        "stop_loss": ({"price": stop, "probability": sl_prob, "band": _band(sl_prob)}
                      if sl_prob is not None else None),
        "expected_move": round(expected_move, 1),
        "edge": round(prob_success, 1),
        "note": "Touch-probabilities (not mutually exclusive). Probabilities, not certainty.",
    }
