"""Phase 20 — Market DNA Engine (historical similarity).

Compares the CURRENT setup against every stored historical outcome and answers:
have we seen this before, what happened next, which strike worked, how much did
premium expand, what's the highest-probability outcome.

Derivation-only: reads the outcomes the platform already records (no new market
data, no broker calls). Probabilities, never certainty. Needs ≥10 comparable
sessions or it honestly returns "Insufficient DNA".
"""
from __future__ import annotations

import time
from typing import Any

from ..core.clock import today_str

MIN_SAMPLES = 10
MATCH_THRESHOLD = 55          # a stored session counts as "similar" at/above this

# How each feature contributes to the 0-100 similarity score.
_CATEGORICAL = {"direction": 25, "regime": 20, "session": 8, "animal": 9, "expansion_class": 8}
_NUMERIC = {  # weight, tolerance (full credit within ±tol, zero past 3×tol)
    "pcr": (12, 0.25),
    "adx": (8, 8.0),
    "atr_pct": (6, 0.4),
    "vix": (4, 2.0),
}


def snapshot(layers: dict[str, Any], analytics: dict[str, Any],
             atr_pct: float | None = None, vix: float | None = None) -> dict[str, Any]:
    """Build the DNA feature snapshot for the current setup (or to persist at
    signal time). Pure read of already-computed state."""
    trend = layers.get("trend") or {}
    regime = layers.get("regime") or {}
    intel = layers.get("intelligence") or {}
    an = intel.get("market_animal") or {}
    ex = intel.get("expansion") or {}
    sess = layers.get("session") or {}
    return {
        "direction": trend.get("direction"),
        "regime": regime.get("regime"),
        "session": sess.get("session"),
        "animal": an.get("animal"),
        "expansion_class": ex.get("class"),
        "pcr": _f((analytics or {}).get("pcr")),
        "adx": _f(trend.get("adx")),
        "atr_pct": _f(atr_pct),
        "vix": _f(vix),
    }


def _f(v: Any) -> float | None:
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def _similarity(cur: dict, hist: dict) -> float:
    """0-100 similarity between two DNA snapshots over shared features."""
    if not hist:
        return 0.0
    score = 0.0
    possible = 0.0
    for k, w in _CATEGORICAL.items():
        cv, hv = cur.get(k), hist.get(k)
        if cv is None or hv is None:
            continue
        possible += w
        if cv == hv:
            score += w
    for k, (w, tol) in _NUMERIC.items():
        cv, hv = cur.get(k), hist.get(k)
        if cv is None or hv is None:
            continue
        possible += w
        diff = abs(cv - hv)
        # full credit within tol, linear decay to 0 at 3×tol
        score += w * max(0.0, 1.0 - diff / (3 * tol)) if tol else 0.0
    if possible < 30:           # too few shared features to trust the match
        return 0.0
    return round(score / possible * 100, 1)


def _verdict(match: float, n: int) -> str:
    if n < MIN_SAMPLES:
        return "NO MATCH"
    return ("VERY STRONG MATCH" if match >= 85 else "STRONG MATCH" if match >= 72
            else "MODERATE MATCH" if match >= 60 else "WEAK MATCH" if match >= 50 else "NO MATCH")


def analyze(current: dict[str, Any], outcomes: list[dict]) -> dict[str, Any]:
    """Compare `current` snapshot against stored `outcomes` (each may carry a
    `dna` snapshot recorded at signal time)."""
    scored = []
    for o in outcomes:
        dna = o.get("dna")
        if not dna:
            continue
        sim = _similarity(current, dna)
        if sim > 0:
            scored.append((sim, o))
    scored.sort(key=lambda x: x[0], reverse=True)
    similar = [(s, o) for s, o in scored if s >= MATCH_THRESHOLD]

    if len(similar) < MIN_SAMPLES:
        return {"status": "INSUFFICIENT_DNA", "verdict": "NO MATCH",
                "samples": len(similar), "min_required": MIN_SAMPLES,
                "note": f"Only {len(similar)} comparable sessions stored — need ≥{MIN_SAMPLES}. "
                        "DNA grows as the system runs (persists with Supabase).",
                "ready": False}

    matched = [o for _, o in similar]
    wins = [o for o in matched if o.get("win")]
    win_rate = round(len(wins) / len(matched) * 100, 1)
    avg_match = round(sum(s for s, _ in similar) / len(similar), 1)

    # premium expansion (planned, from stored strike premiums) — honestly labelled
    pexp = [o["premium_expansion_pct"] for o in matched if o.get("premium_expansion_pct") is not None]
    avg_pexp = round(sum(pexp) / len(pexp), 1) if pexp else None

    durations = [(o["closed"] - o["opened"]) / 60 for o in matched
                 if o.get("closed") and o.get("opened")]
    avg_dur = round(sum(durations) / len(durations), 0) if durations else None

    # best / worst strike by realised r-multiple
    by_strike: dict[str, list[float]] = {}
    for o in matched:
        st = o.get("strike")
        if st is None:
            continue
        by_strike.setdefault(str(st), []).append(o.get("r_multiple", 0))
    strike_perf = {k: round(sum(v) / len(v), 2) for k, v in by_strike.items() if v}
    best_strike = max(strike_perf, key=strike_perf.get) if strike_perf else None
    worst_strike = min(strike_perf, key=strike_perf.get) if strike_perf else None

    most_common = "WIN" if win_rate >= 50 else "LOSS"
    avg_r = round(sum(o.get("r_multiple", 0) for o in matched) / len(matched), 2)
    risk = ("LOW" if win_rate >= 65 and avg_r > 0 else "HIGH" if win_rate < 45 or avg_r < 0
            else "MODERATE")

    # similar-days table (top 10)
    similar_days = [{
        "date": _date(o), "match": s, "result": "WIN" if o.get("win") else "LOSS",
        "premium_expansion": o.get("premium_expansion_pct"),
        "r_multiple": o.get("r_multiple"), "regime": o.get("regime"),
        "outcome": f"{o.get('pnl','—')} pts",
    } for s, o in similar[:10]]

    # prediction — majority direction of the matched winners
    dirs = [o.get("direction") for o in wins if o.get("direction")]
    exp_dir = max(set(dirs), key=dirs.count) if dirs else current.get("direction")
    moves = [abs(o.get("pnl", 0)) for o in matched if o.get("pnl")]
    exp_range = round(sum(moves) / len(moves), 0) if moves else None

    return {
        "status": "OK", "ready": True,
        "match_score": avg_match,
        "verdict": _verdict(avg_match, len(similar)),
        "samples": len(similar),
        "historical_win_rate": win_rate,
        "avg_premium_expansion_pct": avg_pexp,
        "avg_duration_min": avg_dur,
        "best_strike": best_strike,
        "worst_strike": worst_strike,
        "strike_performance": strike_perf,
        "most_common_outcome": most_common,
        "avg_r_multiple": avg_r,
        "risk_rating": risk,
        "similar_days": similar_days,
        "prediction": {
            "expected_direction": exp_dir,
            "expected_range_pts": exp_range,
            "expected_premium_expansion_pct": avg_pexp,
            "expected_duration_min": avg_dur,
            "expected_probability": win_rate,
        },
        "note": "Planned premium expansion (from stored strike premiums); probabilities, not certainty.",
        "ts": time.time(),
    }


def _date(o: dict) -> str:
    ts = o.get("closed") or o.get("opened")
    return today_str(ts) if ts else "—"
