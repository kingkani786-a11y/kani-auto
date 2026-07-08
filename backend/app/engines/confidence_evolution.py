"""Module 9 — AI Confidence Evolution.

Tracks how confidence changes cycle-to-cycle and attributes each move to the
layer that actually shifted — so the trader sees *why* confidence rose or fell,
not just a static number. Derivation-only: reads confidence + the existing
decision-matrix layer scores, keeps a short in-memory series. Probabilities,
never certainty.
"""
from __future__ import annotations

import time
from collections import deque
from typing import Any

_history: dict[str, deque] = {}   # symbol -> deque[{ts, confidence, scores}]
_MAXLEN = 40


def update(symbol: str, signal: dict[str, Any], layers: dict[str, Any]) -> dict[str, Any]:
    L = layers or {}
    rows = ((L.get("intelligence") or {}).get("decision_matrix") or {}).get("rows", [])
    conf = int(signal.get("dynamic_confidence") or signal.get("confidence") or 0)
    scores = {r.get("layer"): float(r.get("score", 50)) for r in rows}
    now = time.time()

    hist = _history.setdefault(symbol, deque(maxlen=_MAXLEN))
    prev = hist[-1] if hist else None
    hist.append({"ts": now, "confidence": conf, "scores": scores})

    delta = 0
    responsible = None
    reason = "First reading"
    if prev:
        delta = conf - prev["confidence"]
        # attribute to the layer whose score moved most in the delta's direction
        moves = []
        for layer, sc in scores.items():
            psc = prev["scores"].get(layer)
            if psc is not None:
                moves.append((layer, sc - psc))
        if moves:
            if delta >= 0:
                responsible, mv = max(moves, key=lambda x: x[1])
                if mv > 0.5:
                    reason = f"{responsible} strengthened (+{mv:.0f}) to {scores[responsible]:.0f}"
                else:
                    responsible, mv = max(moves, key=lambda x: abs(x[1])) if moves else (None, 0)
                    reason = "Broad confluence held" if abs(delta) < 1 else f"{responsible} shifted"
            else:
                responsible, mv = min(moves, key=lambda x: x[1])
                reason = f"{responsible} weakened ({mv:.0f}) to {scores[responsible]:.0f}"

    direction = "increased" if delta > 0 else "decreased" if delta < 0 else "stable"
    series = [{"t": int(h["ts"]), "c": h["confidence"]} for h in hist]
    confs = [h["confidence"] for h in hist]

    return {
        "ready": bool(hist),
        "current": conf,
        "delta": delta,
        "direction": direction,
        "responsible_layer": responsible,
        "reason": reason,
        "why": (f"Confidence {direction} — {reason}" if prev else "Confidence tracking started"),
        # V20-P1 — action-oriented hint, not just the number
        "action_hint": ("BUY probability increasing" if delta >= 2
                        else "Risk increasing — be patient" if delta <= -2 else "Stable"),
        "timeline": series,
        "high": max(confs) if confs else conf,
        "low": min(confs) if confs else conf,
        "samples": len(hist),
        "note": "Per-minute confidence evolution with layer attribution. Probabilities, not certainty.",
    }


def reset(symbol: str | None = None) -> None:
    if symbol:
        _history.pop(symbol, None)
    else:
        _history.clear()
