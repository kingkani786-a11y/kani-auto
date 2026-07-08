"""Phase 1/5/13 — Decision Intelligence Engine.

A single institutional decision synthesised from the outputs the platform ALREADY
computes (decision matrix, confluence, DNA, capital protection, premium forecast,
probability ladder). Derivation-only — no new data, no duplicated calculation, no
new API calls. Adds: one final decision + conviction, a 0–1000 Trade Quality score
(Phase 5), and a governance / devil's-advocate layer (Phase 13). Trade quality over
quantity; every output is explainable; never fabricates confidence.
"""
from __future__ import annotations

from typing import Any

# decision-matrix layer name -> the trade-quality component it feeds
_COMPONENT_OF = {
    "Trend": "structure_score", "Structure": "structure_score",
    "MTF": "structure_score",
    "OI": "institution_score", "Institutional": "institution_score",
    "Smart Money": "institution_score",
    "Greeks": "greeks_score",
    "Volume Profile": "volume_score", "Liquidity": "liquidity_score",
}


def synthesize(layers: dict[str, Any], signal: dict[str, Any],
               decision: dict[str, Any], market_dna: dict[str, Any] | None = None) -> dict[str, Any]:
    L = layers or {}
    if not L:
        return {"ready": False, "note": "No live analysis yet — connect and let the AI cycle run."}

    sig = signal or {}
    dec = decision or {}
    rows = ((L.get("intelligence") or {}).get("decision_matrix") or {}).get("rows", [])
    # V15 instrument-aware: N/A rows (option-only layers on chain-less
    # instruments) are excluded from components and agreement, not counted 50.
    rows = [r for r in rows if r.get("verdict") != "N/A"]
    no_chain = bool((L.get("_instrument_mode") or {}).get("excluded"))
    dna = market_dna or {}
    cap = L.get("capital_protection") or {}
    conf = int(sig.get("dynamic_confidence") or sig.get("confidence") or 0)
    direction = sig.get("direction") or "NEUTRAL"

    # ---- component scores (0-100) averaged from the matrix rows ----
    buckets: dict[str, list[float]] = {}
    for r in rows:
        comp = _COMPONENT_OF.get(r.get("layer"))
        if comp:
            buckets.setdefault(comp, []).append(float(r.get("score", 50)))
    comp = {k: round(sum(v) / len(v), 0) for k, v in buckets.items()}
    comp.setdefault("structure_score", 50); comp.setdefault("institution_score", 50)
    comp.setdefault("greeks_score", 50); comp.setdefault("volume_score", 50)
    comp.setdefault("liquidity_score", 50)
    comp["dna_score"] = float(dna.get("match_score") or 50) if dna.get("ready") else 50.0
    pf = dec.get("premium_forecast") or {}
    comp["premium_score"] = float(pf.get("probability") or 50) if pf.get("ready") else 50.0
    catmap = {"SAFE": 85, "LOW": 80, "MODERATE": 60, "MEDIUM": 60, "ELEVATED": 40,
              "HIGH": 30, "CRITICAL": 15, "DANGER": 15}
    comp["risk_score"] = float(catmap.get((cap.get("category") or "").upper(), 55))

    # ---- Phase 5 — Trade Quality 0-1000 (weighted) ----
    weights = {"institution_score": 0.20, "structure_score": 0.18, "greeks_score": 0.12,
               "volume_score": 0.10, "liquidity_score": 0.10, "dna_score": 0.12,
               "premium_score": 0.08, "risk_score": 0.10}
    if no_chain:
        # option-only components don't exist here — grade the applicable ones
        for k in ("institution_score", "greeks_score", "premium_score"):
            weights.pop(k)
            comp.pop(k, None)
        _tot = sum(weights.values())
        weights = {k: w / _tot for k, w in weights.items()}
    agree = (len([r for r in rows if r.get("verdict") == "PASS"]) / len(rows)) if rows else 0.5
    base = sum(comp[k] * w for k, w in weights.items())          # 0-100
    trade_score = int(round(base * 10 * (0.7 + 0.3 * agree)))    # 0-1000, agreement-boosted
    trade_score = max(0, min(1000, trade_score))
    grade = ("ELITE" if trade_score >= 850 else "HIGH PROBABILITY" if trade_score >= 700
             else "MEDIUM" if trade_score >= 550 else "LOW" if trade_score >= 400 else "NO TRADE")

    # ---- final institutional decision ----
    is_trade = bool(dec.get("is_trade")) and grade not in ("LOW", "NO TRADE")
    if not is_trade:
        final = "WAIT" if (dec.get("primary_action") not in ("NO TRADE",)) else "NO TRADE"
    else:
        final = "BUY CALL" if direction == "BULL" else "BUY PUT" if direction == "BEAR" else "WAIT"
    conviction = int(round(conf * (0.6 + 0.4 * agree)))

    # ---- Phase 13 — governance / devil's advocate ----
    passes = [r for r in rows if r.get("verdict") == "PASS"]
    fails = [r for r in rows if r.get("verdict") == "FAIL"]
    bull = max(passes, key=lambda r: r.get("score", 0)) if passes else None
    bear = min(fails, key=lambda r: r.get("score", 100)) if fails else None
    vetoes = sig.get("vetoes") or sig.get("warnings") or []
    largest_risk = (cap.get("category") and f"Capital risk {cap['category']}") or \
                   (vetoes[0] if vetoes else "Momentum could fade at the next level")
    devil = ("Even with confluence, a single institutional reversal or IV crush can invalidate this — "
             "size small." if is_trade else
             "Waiting has a cost too: if confluence confirms, a clean entry may be missed. Watch for maturity.")
    governance = {
        "why": dec.get("reason", ""),
        "strongest_bull": (f"{bull['layer']}: {bull.get('reason','')}" if bull else "No strong bullish layer"),
        "strongest_bear": (f"{bear['layer']}: {bear.get('reason','')}" if bear else "No strong bearish layer"),
        "largest_risk": largest_risk,
        "devils_advocate": devil,
        "final_verdict": f"{final} — {grade} ({conviction}% conviction)",
    }

    return {
        "ready": True,
        "final_decision": final,
        "conviction": conviction,
        "trade_quality": {"score": trade_score, "grade": grade,
                          "engine_agreement_pct": round(agree * 100, 0)},
        "components": {k: int(v) for k, v in comp.items()},
        "governance": governance,
        "disclaimer": "One synthesised institutional view from existing engines. Quality over quantity; "
                      "probabilities, never certainty.",
    }
