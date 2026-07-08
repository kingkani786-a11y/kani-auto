"""AI Market Path Predictor — fuses EXISTING engine outputs (structure S/R,
future scenarios, expected move, institutional levels, trend/bias) into one
answer to "where is price most likely to go next?": current bias, next touch
level + ETA, next 3 targets, failure level, bull/bear/range scenarios, per-
horizon (5/15/30/60m) direction probability, and a natural-language summary.

NOT a new engine — pure aggregation/derivation, no new data, no new calculation
beyond light level/ETA math. Probabilities, never certainty; recomputed each
cycle so the highest-probability path updates as conditions change.
"""
from __future__ import annotations

from typing import Any

_HORIZONS = [("5m", 1.00), ("15m", 0.90), ("30m", 0.80), ("60m", 0.70)]


def predict(layers: dict[str, Any], spot: float, levels: dict[str, Any] | None = None) -> dict[str, Any]:
    if not spot:
        return {"ready": False, "note": "No spot yet."}
    L = layers or {}
    structure = L.get("structure") or {}
    fut = (L.get("future") or {}).get("scenarios") or {}
    prob = L.get("probability") or {}
    trend = L.get("trend") or {}
    lv = levels or {}
    em = float(prob.get("expected_move") or 0) or spot * 0.004

    # ---- candidate levels (dedup, from what the platform already computes) ----
    cands: dict[float, str] = {}
    def addlvl(v, name):
        try:
            f = float(v)
            if f > 0 and abs(f - spot) / spot < 0.04:   # within 4% of spot only
                cands.setdefault(round(f, 1), name)
        except (TypeError, ValueError):
            pass
    addlvl(structure.get("resistance"), "Resistance")
    addlvl(structure.get("support"), "Support")
    addlvl(lv.get("vwap"), "VWAP")
    for k in ("pdh", "pdl", "prev_close", "r1", "r2", "r3", "s1", "s2", "s3",
              "poc", "vah", "val", "cpr_top", "cpr_bottom", "pivot"):
        addlvl(lv.get(k), k.upper())

    above = sorted([(p, n) for p, n in cands.items() if p > spot])
    below = sorted([(p, n) for p, n in cands.items() if p < spot], reverse=True)

    bull = float((fut.get("bullish") or {}).get("probability") or 33)
    bear = float((fut.get("bearish") or {}).get("probability") or 33)
    rng = float((fut.get("range") or {}).get("probability") or 34)
    bias = ("BULLISH" if bull >= max(bear, rng) else "BEARISH" if bear >= max(bull, rng) else "RANGE")

    def eta_min(dist: float) -> int:
        return max(1, min(120, round(dist / em * 30)))     # ~30 min per 1 expected-move

    def touch_prob(dist: float, favourable: bool) -> int:
        import math
        base = 100 * math.exp(-0.6 * dist / em)
        base *= (0.6 + 0.4 * (bull if favourable else bear) / 100)
        return int(max(8, min(94, base)))

    # next touch = nearest level either side
    nearest = None
    pool = []
    if above: pool.append((above[0][0] - spot, above[0], "up"))
    if below: pool.append((spot - below[0][0], below[0], "down"))
    if pool:
        dist, (lvl, name), side = min(pool, key=lambda x: x[0])
        nearest = {"level": lvl, "name": name, "side": side, "distance": round(dist, 1),
                   "eta_min": eta_min(dist), "touch_prob": touch_prob(dist, (side == "up") == (bias == "BULLISH"))}

    # next 3 targets in the bias direction; failure = opposite first level
    discovery = None
    if bias == "BEARISH":
        targets = [{"level": p, "name": n, "prob": touch_prob(spot - p, True)} for p, n in below[:3]]
        failure = ({"level": above[0][0], "name": above[0][1]} if above else None)
        if not targets:
            discovery = "Price below all tracked supports — price discovery mode"
    else:
        targets = [{"level": p, "name": n, "prob": touch_prob(p - spot, True)} for p, n in above[:3]]
        failure = ({"level": below[0][0], "name": below[0][1]} if below else None)
        if not targets:
            discovery = "Price above tracked resistance — price discovery mode"

    # per-horizon directional probability (uncertainty grows with time)
    horizons = []
    for h, f in _HORIZONS:
        up = round(50 + (bull - 50) * f, 0)
        dn = round(50 + (bear - 50) * f, 0)
        horizons.append({"horizon": h, "up": up, "down": dn,
                         "lean": "UP" if up > dn + 3 else "DOWN" if dn > up + 3 else "FLAT"})

    scenarios = {
        "bullish": {"probability": round(bull, 0), "path": [t["level"] for t in
                    ([{"level": p} for p, n in above[:3]])]},
        "bearish": {"probability": round(bear, 0), "path": [p for p, n in below[:3]]},
        "range": {"probability": round(rng, 0),
                  "band": [below[0][0] if below else round(spot - em * 0.4, 1),
                           above[0][0] if above else round(spot + em * 0.4, 1)]},
        "primary": bias.lower(),
    }

    # ---- natural-language summary ----
    if nearest:
        nl = (f"{bias.title()} bias. Most likely to test {nearest['name']} {nearest['level']} "
              f"(~{nearest['touch_prob']}%) within ~{nearest['eta_min']} min.")
        if targets:
            nl += f" Above/through it, next {targets[0]['name']} {targets[0]['level']}."
        if failure:
            nl += f" A break of {failure['level']} cancels this {bias.lower()} path."
    else:
        nl = f"{bias.title()} bias; no clear level within range yet."

    # ---- confidence reasoning (why this bias?) — from the decision matrix ----
    rows = ((L.get("intelligence") or {}).get("decision_matrix") or {}).get("rows", [])
    contribs = []
    for r in rows:
        c = round((float(r.get("score", 50)) - 50) / 3.0)   # readable points ±
        if abs(c) >= 2:
            contribs.append({"layer": r.get("layer"), "contribution": c,
                             "reason": r.get("reason", "")})
    contribs.sort(key=lambda x: x["contribution"], reverse=True)
    reasoning = [c for c in contribs if c["contribution"] > 0][:3] + \
                [c for c in contribs if c["contribution"] < 0][-2:]
    # "Layer Support" — NOT conviction/confidence (kept separate on purpose):
    # averaged so it can't saturate at 100 just because many layers lean one way.
    layer_support = int(max(0, min(100, 50 + (sum(c["contribution"] for c in contribs)
                                              / max(1, len(contribs))) * 4)))

    # institutional-style rollups (derivation from the same probabilities)
    dir_prob = bull if bias == "BULLISH" else bear if bias == "BEARISH" else rng
    opp_prob = bear if bias == "BULLISH" else bull if bias == "BEARISH" else rng
    breakout_probability = int(round(max(8, min(92, dir_prob * 0.9 + 8))))
    reversal_probability = int(round(max(8, min(80, opp_prob * 0.8 + rng * 0.3))))

    return {
        "ready": True,
        "spot": round(spot, 1),
        "bias": bias,
        "overall_direction": {"up": round(bull, 0), "down": round(bear, 0), "range": round(rng, 0)},
        "breakout_probability": breakout_probability,
        "reversal_probability": reversal_probability,
        "reasoning": reasoning,
        "layer_support": layer_support,
        "confidence_source": layer_support,   # back-compat alias
        "discovery": discovery,
        "live_note": "Confidence updates live if Structure / OI / Institutional Flow changes.",
        "expected_move": round(em, 1),
        "next_touch": nearest,
        "targets": targets,
        "failure_level": failure,
        "horizons": horizons,
        "scenarios": scenarios,
        "summary": nl,
        "note": "Highest-probability path from fused engine state — updates as conditions change. "
                "Probabilities, not certainty; not a prediction of the future.",
    }
