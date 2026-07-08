"""V29 §1/2/3/7 — Alpha Detection & Execution Optimization.

Composes an Alpha Score (earliest favourable edge), a ranked Opportunity Queue,
an Entry-Timing Gauge, and a per-domain Confidence Distribution — all from
outputs the platform already computes. Derivation-only; prioritises execution
quality over trade quantity. Probabilities, never certainty.
"""
from __future__ import annotations

from typing import Any


def _alpha_category(score: float) -> str:
    return ("Institutional Alpha" if score >= 85 else "Strong Edge" if score >= 70
            else "Moderate Edge" if score >= 55 else "Low Edge" if score >= 40 else "No Edge")


def build(layers: dict[str, Any], signal: dict[str, Any], decision: dict[str, Any],
          market_dna: dict[str, Any] | None = None) -> dict[str, Any]:
    di = decision.get("intelligence_synthesis") or {}
    ec = decision.get("entry_checklist") or {}
    est = decision.get("entry_score_timeline") or {}
    card = decision.get("execution_card") or {}
    sm = decision.get("signal_maturity") or {}
    dna = market_dna or {}
    rows = {r.get("layer"): float(r.get("score", 50))
            for r in ((layers.get("intelligence") or {}).get("decision_matrix") or {}).get("rows", [])}

    trade_q = float((di.get("trade_quality") or {}).get("score") or 0) / 10.0   # 0-100
    conviction = float(di.get("conviction") or 0)
    rr = float((signal.get("reward_risk") or signal.get("rr") or 0))
    dna_match = float(dna.get("match_score") or 50) if dna.get("ready") else 50.0
    rr_score = min(100.0, rr / 3.0 * 100) if rr else 50.0
    rising_bonus = 10.0 if est.get("trend") == "STRENGTHENING" else 0.0

    alpha = round(min(100.0, max(0.0,
        trade_q * 0.40 + conviction * 0.20 + dna_match * 0.15 + rr_score * 0.15 + rising_bonus)), 0)

    # §7 — confidence distribution (per domain, from matrix)
    conf_dist = {
        "trend": round(rows.get("Trend", 50), 0),
        "options": round((rows.get("OI", 50) + rows.get("Greeks", 50)) / 2, 0),
        "futures": round(rows.get("Futures", 50), 0),
        "institutional": round(rows.get("Institutional", 50), 0),
        "execution": round(float(ec.get("fire_score") or 0), 0),
    }

    # §3 — entry timing gauge
    stage = est.get("stage")
    if stage == "ENTRY NOW":
        timing = "Ideal"
    elif stage == "APPROACHING" or stage == "FORMING":
        timing = "Too Early"
    elif stage == "WEAKENING":
        timing = "Avoid"
    else:
        et = (sm.get("entry_trigger") or {})
        timing = ("Late" if et.get("status") == "ENTRY CLOSED" else "Too Early")

    # §2 — opportunity queue (rank existing radar tiers by probability)
    radar = card.get("opportunity_radar") or []
    buy_allowed = bool(sm.get("buy_allowed"))
    def status_for(o):
        if o["mode"] in ("QUICK", "FAST") and buy_allowed:
            return "Ready"
        if (est.get("trend") == "STRENGTHENING"):
            return "Preparing"
        return "Watching"
    queue = sorted(
        [{"type": o["mode"], "points": o["expected_points"], "probability": o["probability"],
          "status": status_for(o)} for o in radar],
        key=lambda r: r["probability"], reverse=True)
    for i, r in enumerate(queue, 1):
        r["rank"] = i

    return {
        "ready": bool(rows),
        "alpha_score": alpha,
        "category": _alpha_category(alpha),
        "edge": ("High" if alpha >= 70 else "Medium" if alpha >= 50 else "Low"),
        "expected_reward_risk": rr or None,
        "historical_similarity": dna_match,
        "confidence_distribution": conf_dist,
        "entry_timing": timing,
        "opportunity_queue": queue,
        "note": "Alpha = earliest favourable edge, quality over quantity. Probabilities, not certainty.",
    }
