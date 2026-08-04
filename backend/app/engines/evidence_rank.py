"""Evidence Ranking + Contradiction — V7.1 Trade Explorer Phase 2
(owner, 2026-08-04).

THE PROBLEM THIS SOLVES. Today seven directional layers are multiplied by
fixed weights and summed into one composite. That composite decides, but it
cannot say WHY: a 72 built from Trend+Structure and a 72 built from OI+MTF
look identical to the trader. The owner's framing:

    "எல்லா indicators-ஐ சமமாக கலந்து ஒரு opaque score கொடுக்கக்கூடாது...
     எந்த காரணத்தால் entry உருவாகிறதோ, அந்த காரணமே முதலில் காட்டப்பட வேண்டும்."

So this module re-reads the SAME layer scores the composite already used and
answers a different question: *which layer is actually driving this, which
ones merely agree, and which one disagrees?*

WHAT IT IS NOT:
  * It computes NO new score and changes NO existing one. It is a classifier
    over numbers `confluence.run()` has already produced. Remove it and the
    decision is byte-identical.
  * It never vetoes, never gates, never adds a threshold to the decision path.
  * It attaches no probability. A layer being PRIMARY means it is the
    strongest supporting evidence *right now*, NOT that the trade will work —
    the same discipline as candles.py, and for the same reason (RVE-001/002:
    named features that looked predictive were spurious once controlled).

RELATIONSHIP TO OBS-15: that observation recorded that per-trade vetoes
(Premium, Greeks) could be active while no panel explained them. The
CONTRADICTORY bucket here is the general form of that fix — any layer
leaning against the chosen direction is named, not silently averaged away.
"""
from __future__ import annotations

from typing import Any

# The seven weighted directional layers, plus the two observational ones that
# carry a readable directional lean. Labels are the trader-facing names.
_DIRECTIONAL = {
    "trend": "Trend",
    "structure": "Price Action / Structure",
    "oi": "Open Interest",
    "mtf": "Multi-Timeframe",
    "smart_money": "Smart Money",
    "greeks": "Greeks",
    "volume_profile": "Volume Profile",
}

# DECLARED classification bands — conventions for reading existing scores,
# not fitted values, and not thresholds on the decision path.
THRESHOLD_REGISTRY = {
    "SUPPORT_MIN": (55.0, "score at/above this in the chosen direction = supporting"),
    "CONTRADICT_MIN": (55.0, "score at/above this in the OPPOSITE direction = contradicting"),
    "PRIMARY_GAP": (8.0, "top layer must lead the 2nd by this much to be a clear sole driver"),
    "INSUFFICIENT_BAND": (5.0, "within this of 50 = no usable directional read"),
}
SUPPORT_MIN = 55.0
CONTRADICT_MIN = 55.0
PRIMARY_GAP = 8.0
INSUFFICIENT_BAND = 5.0


def analyze(layers: dict[str, Any], win_dir: str,
            candles_layer: dict[str, Any] | None = None) -> dict[str, Any]:
    """Classify every directional layer against the chosen direction.

    `win_dir` is confluence's OWN winner ("BULL"/"BEAR") — this module never
    picks a direction, it only explains the one already chosen.
    """
    if win_dir not in ("BULL", "BEAR"):
        return {"ready": False, "primary": None, "confirming": [],
                "contradicting": [], "insufficient": [], "conclusion": "",
                "note": "No directional read to explain."}

    key = "score_bull" if win_dir == "BULL" else "score_bear"
    opp = "score_bear" if win_dir == "BULL" else "score_bull"

    supporting: list[dict] = []
    contradicting: list[dict] = []
    insufficient: list[dict] = []

    for lk, label in _DIRECTIONAL.items():
        lay = layers.get(lk) or {}
        s = lay.get(key)
        o = lay.get(opp)
        if s is None or o is None:
            insufficient.append({"layer": lk, "label": label,
                                 "reason": "layer not available for this instrument"})
            continue
        try:
            s, o = float(s), float(o)
        except (TypeError, ValueError):
            insufficient.append({"layer": lk, "label": label,
                                 "reason": "unreadable score"})
            continue

        detail = (lay.get("trend") or lay.get("event") or lay.get("state")
                  or lay.get("verdict") or lay.get("summary") or "")
        row = {"layer": lk, "label": label, "score": round(s, 1),
               "opposite": round(o, 1), "detail": str(detail)[:80]}

        if abs(s - 50.0) <= INSUFFICIENT_BAND and abs(o - 50.0) <= INSUFFICIENT_BAND:
            insufficient.append({**row, "reason": "flat — no usable directional read"})
        elif s >= SUPPORT_MIN:
            supporting.append(row)
        elif o >= CONTRADICT_MIN:
            contradicting.append({**row,
                                  "leans": "BEAR" if win_dir == "BULL" else "BULL"})
        else:
            insufficient.append({**row, "reason": "below the supporting bar, not opposing"})

    # ---- candle layer joins as evidence when it has a readable lean ----
    # NOTE, load-bearing: the candle layer has NO comparable 0-100 directional
    # score — its output is a detection, not a weighted score. An earlier draft
    # gave it a synthetic 100 so it would sort high; that was wrong, because it
    # made Candle Pattern outrank a genuinely stronger layer (e.g. Structure at
    # 91) purely on an invented number — a fabricated ranking, the exact thing
    # this engine exists to avoid. It is therefore recorded as supporting or
    # contradicting evidence but is NOT eligible to be named PRIMARY: there is
    # no principled way to rank a detection against a weighted score. It can
    # become rankable later, once per-pattern outcome statistics exist.
    cd = candles_layer or {}
    if cd.get("ready") and cd.get("count"):
        cb = cd.get("bias")
        crow = {"layer": "candles", "label": "Candle Pattern",
                "score": None, "opposite": None, "rankable": False,
                "detail": str(cd.get("summary") or "")[:80]}
        if cb == win_dir:
            supporting.append(crow)
        elif cb in ("BULL", "BEAR"):
            contradicting.append({**crow, "leans": cb})
        else:
            insufficient.append({**crow, "reason": "candles read neutral"})

    # Rankable (scored) layers sort by score and compete for PRIMARY;
    # unrankable evidence is listed after them and never becomes PRIMARY.
    rankable = [r for r in supporting if r.get("score") is not None]
    unrankable = [r for r in supporting if r.get("score") is None]
    rankable.sort(key=lambda r: r["score"], reverse=True)
    supporting = rankable + unrankable
    contradicting.sort(key=lambda r: (r.get("opposite") is not None,
                                      r.get("opposite") or 0), reverse=True)

    primary = rankable[0] if rankable else None
    rest = [r for r in supporting if r is not primary]

    # A sole clear driver, or several sharing the lead?
    sole = False
    if primary and rest:
        top, second = primary.get("score") or 0, rest[0].get("score") or 0
        sole = (top - second) >= PRIMARY_GAP
    elif primary:
        sole = True

    # ---- plain-language conclusion, built from what was actually found ----
    if not primary:
        conclusion = ("No layer clears the supporting bar for this direction — "
                      "the read is weak on its own terms.")
    else:
        driver = primary["label"]
        if sole:
            conclusion = f"{driver} is the dominant evidence"
        else:
            joint = ", ".join([primary["label"]] + [r["label"] for r in rest[:1]])
            conclusion = f"{joint} lead jointly"
        if rest:
            conclusion += f", confirmed by {len(rest)} other layer{'s' if len(rest) > 1 else ''}"
        conclusion += "."
        if contradicting:
            names = ", ".join(c["label"] for c in contradicting[:2])
            conclusion += (f" {names} lean{'s' if len(contradicting) == 1 else ''} "
                           f"the other way — the thesis is contested.")

    return {
        "ready": True,
        "direction": win_dir,
        "primary": primary,
        "primary_is_sole_driver": sole,
        "confirming": rest,
        "contradicting": contradicting,
        "insufficient": insufficient,
        "counts": {"supporting": len(supporting), "contradicting": len(contradicting),
                   "insufficient": len(insufficient)},
        "contested": bool(contradicting),
        "conclusion": conclusion,
        "note": ("Classification of scores confluence already computed — no new "
                 "score, no threshold, no veto, and no effect on the decision. "
                 "PRIMARY means strongest supporting evidence right now, NOT "
                 "that the trade will work; no probability is attached."),
        "thresholds_declared": {k: v[0] for k, v in THRESHOLD_REGISTRY.items()},
    }
