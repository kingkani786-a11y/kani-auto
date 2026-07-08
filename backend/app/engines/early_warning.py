"""Early Warning System — flags setups FORMING before they confirm.

A setup is 'forming' when several layers lean one way but the mandatory
gate hasn't passed yet (e.g. price coiling under resistance with put
writing building). Preparation = how much of the gate is satisfied;
confidence = strength of the leaning layers.
"""
from __future__ import annotations

from typing import Any


def analyze(
    layers: dict[str, Any], win_dir: str, win_score: float,
    threshold: float, was_vetoed: bool,
) -> dict[str, Any]:
    if not was_vetoed:
        return {"setup": "NONE", "preparation": 0, "confidence": 0, "notes": []}

    score_key = "score_bull" if win_dir == "BULL" else "score_bear"
    directional = ("trend", "structure", "oi", "mtf", "smart_money", "greeks", "volume_profile")
    leaning = [n for n in directional if layers[n][score_key] >= 55]
    strong = [n for n in directional if layers[n][score_key] >= 65]

    if len(leaning) < 3 or win_score < threshold * 0.72:
        return {"setup": "NONE", "preparation": 0, "confidence": 0, "notes": []}

    preparation = round(min(95, len(leaning) / len(directional) * 70 + win_score * 0.3), 0)
    confidence = round(min(90, sum(layers[n][score_key] for n in leaning) / len(leaning)), 0)
    setup = "BULLISH_FORMING" if win_dir == "BULL" else "BEARISH_FORMING"

    notes = [f"{len(leaning)}/7 layers leaning {'bullish' if win_dir == 'BULL' else 'bearish'}"]
    for n in strong[:2]:
        ln = layers[n].get("notes") or []
        if ln:
            notes.append(ln[0])

    return {"setup": setup, "preparation": preparation, "confidence": confidence, "notes": notes}
