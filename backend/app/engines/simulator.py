"""Phase 29 — Today + Tomorrow Simulator.

Projects the session/next-session into discrete scenarios (Bull / Bear / Range /
Gap-Up / Gap-Down) with probability, expected move, target zone and risk, then
ranks Most-Likely / Second-Likely / Worst-Case. Derivation-only: reuses the
existing future-scenario layer, regime, expected move and VIX. Probabilities,
never certainty.
"""
from __future__ import annotations

from typing import Any


def _risk(regime_score: float, vix: float | None) -> str:
    if vix and vix >= 18:
        return "HIGH"
    if regime_score < 40 or (vix and vix >= 15):
        return "MODERATE"
    return "LOW"


def simulate(layers: dict[str, Any], spot: float, vix: float | None = None) -> dict[str, Any]:
    if not spot:
        return {"ready": False, "note": "INSUFFICIENT DATA — no spot yet"}

    fut = layers.get("future") or {}
    sc = fut.get("scenarios") or {}
    prob = layers.get("probability") or {}
    regime = layers.get("regime") or {}
    gctx = layers.get("global_context") or {}
    em = float(prob.get("expected_move") or 0) or (spot * 0.004)
    rscore = float(regime.get("score") or 50)

    p_bull = float((sc.get("bullish") or {}).get("probability") or 33)
    p_bear = float((sc.get("bearish") or {}).get("probability") or 33)
    p_range = float((sc.get("range") or {}).get("probability") or 34)

    def zone(lo: float, hi: float) -> list[float]:
        return [round(lo, 1), round(hi, 1)]

    today = [
        {"scenario": "BULL", "probability": round(p_bull, 0),
         "expected_move": round(em, 1), "target_zone": zone(spot, spot + em),
         "risk": _risk(rscore, vix)},
        {"scenario": "BEAR", "probability": round(p_bear, 0),
         "expected_move": round(em, 1), "target_zone": zone(spot - em, spot),
         "risk": _risk(rscore, vix)},
        {"scenario": "RANGE", "probability": round(p_range, 0),
         "expected_move": round(em * 0.4, 1),
         "target_zone": zone(spot - em * 0.4, spot + em * 0.4), "risk": "LOW"},
    ]

    # Tomorrow gap scenarios — overnight risk scales with VIX; direction leans on
    # the standing global bias. Honestly modest (gaps are low-probability events).
    gap_base = 12.0 + (min(vix, 30) if vix else 12) * 0.6   # ~12–30%
    bias = gctx.get("bias")
    gap_up = gap_base * (1.25 if bias == "BULLISH" else 0.8 if bias == "BEARISH" else 1.0)
    gap_dn = gap_base * (1.25 if bias == "BEARISH" else 0.8 if bias == "BULLISH" else 1.0)
    gap_em = em * 1.4
    tomorrow = [
        {"scenario": "GAP UP", "probability": round(min(45, gap_up), 0),
         "expected_move": round(gap_em, 1), "target_zone": zone(spot, spot + gap_em),
         "risk": _risk(rscore, vix)},
        {"scenario": "GAP DOWN", "probability": round(min(45, gap_dn), 0),
         "expected_move": round(gap_em, 1), "target_zone": zone(spot - gap_em, spot),
         "risk": _risk(rscore, vix)},
        {"scenario": "FLAT / IN-LINE", "probability": round(max(10, 100 - gap_up - gap_dn), 0),
         "expected_move": round(em * 0.5, 1),
         "target_zone": zone(spot - em * 0.5, spot + em * 0.5), "risk": "LOW"},
    ]

    ranked = sorted(today, key=lambda s: s["probability"], reverse=True)
    return {
        "ready": True,
        "today": today,
        "tomorrow": tomorrow,
        "most_likely": ranked[0],
        "second_likely": ranked[1] if len(ranked) > 1 else None,
        "worst_case": min(today, key=lambda s: s["probability"]),
        "tomorrow_bias": bias or "NEUTRAL",
        "note": "Scenario probabilities from the future + regime layers; gaps are low-probability estimates.",
    }
