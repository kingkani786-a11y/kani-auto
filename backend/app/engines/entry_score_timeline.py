"""V26 §1 — Entry Score Timeline.

Tracks the entry/fire score over time so the trader instantly sees whether the
setup is STRENGTHENING toward an entry or FADING — not just a static number.
Derivation-only: reads the fire score the entry-checklist already computes, keeps
a short in-memory series per symbol. Probabilities, never certainty.
"""
from __future__ import annotations

import time
from collections import deque
from typing import Any

_history: dict[str, deque] = {}
_MAXLEN = 40
_FIRE_THRESHOLD = 80      # matches the strict execution bar


def update(symbol: str, decision: dict[str, Any]) -> dict[str, Any]:
    ec = decision.get("entry_checklist") or {}
    score = float(ec.get("fire_score") or 0)
    band = ec.get("fire_band") or "WAIT"
    now = time.time()

    hist = _history.setdefault(symbol, deque(maxlen=_MAXLEN))
    prev = hist[-1] if hist else None
    hist.append({"t": int(now), "s": round(score, 0)})
    delta = round(score - prev["s"], 0) if prev else 0

    # slope over the last ~4 samples → strengthening / fading / stable
    recent = [h["s"] for h in hist][-4:]
    slope = (recent[-1] - recent[0]) if len(recent) >= 2 else 0
    if slope > 4:
        trend = "STRENGTHENING"
    elif slope < -4:
        trend = "FADING"
    else:
        trend = "STABLE"

    # actionable stage
    if score >= _FIRE_THRESHOLD and trend != "FADING":
        stage = "ENTRY NOW"
    elif trend == "STRENGTHENING" and score >= 60:
        stage = "APPROACHING"
    elif trend == "FADING":
        stage = "WEAKENING"
    else:
        stage = "FORMING"

    series = [{"t": h["t"], "s": h["s"]} for h in hist]
    scores = [h["s"] for h in hist]
    return {
        "ready": bool(hist),
        "current": round(score, 0),
        "band": band,
        "delta": delta,
        "trend": trend,
        "stage": stage,
        "timeline": series,
        "high": max(scores) if scores else score,
        "low": min(scores) if scores else score,
        "samples": len(hist),
        "threshold": _FIRE_THRESHOLD,
        "note": "Entry-score over time — strengthening means an entry is approaching. "
                "Probabilities, not certainty.",
    }


def reset(symbol: str | None = None) -> None:
    if symbol:
        _history.pop(symbol, None)
    else:
        _history.clear()
