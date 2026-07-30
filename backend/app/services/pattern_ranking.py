"""V8 Phase 3C — Pattern Ranking + Research Candidate Queue (v8-dev, 2026-07-30).

Pipeline position (owner, 2026-07-30):
    3A Extractor -> 3B Statistics -> Evidence Validator (+ Core Signature
    Validator) -> 3C RANKING (THIS FILE) -> Research Candidate Queue ->
    Walk-Forward -> Monte Carlo -> Proposal Engine -> Human Approval

Computes a Pattern Quality Index (PQI, 0-100) per pattern and a star
classification, then a short Research Candidate Queue (top N) — so
everything downstream (Walk-Forward, Monte Carlo, and eventually the
Proposal Engine) only ever has to look at a handful of patterns instead of
every one ever seen. PQI answers "how much should a human trust this
pattern's evidence" — it is NOT a trading signal, NOT a BUY/SELL call, and
NOT a threshold/weight recommendation. Those stay out of scope through
Walk-Forward and Monte Carlo too; only the (not-yet-built) Proposal Engine
ever produces that kind of text, and even then only as a proposal awaiting
human approval — never applied by this or any other module.

DESIGN DECISION (stated here, not hidden): PQI ranks CORE patterns
(pattern_extractor.core_pattern_id), not pattern_id. pattern_id bakes
REGIME_*/SESSION_* into its own identity, so two of the owner's own PQI
columns — Cross Regime, Cross Session — would be trivially zero/undefined
for every single pattern_id-level entry (each one's evidence is, by
construction, always 100% one regime and one session — see
evidence_validator.py's own caveat). Ranking the core pattern is the only
choice under which those two weights mean anything. Per-regime/per-session
slices remain fully available via evidence_validator.validate_pattern()
for anyone who wants that narrower view; this file doesn't replace it.
"""
from __future__ import annotations

from typing import Any

from . import pattern_extractor as pext
from . import pattern_stats as pstats
from . import evidence_validator as ev

# ── PQI weights (owner's table, 2026-07-30) — sums to 100 ───────────────────
WEIGHTS: dict[str, float] = {
    "sample_size": 20, "days_observed": 15, "win_stability": 20,
    "cross_regime": 15, "cross_session": 10, "mfe_mae_ratio": 10,
    "drawdown_consistency": 10,
}
assert abs(sum(WEIGHTS.values()) - 100) < 1e-9

# ── declared reference scales for each sub-score (unvalidated, same
# declared-not-fitted convention as every other threshold in V8 — these set
# WHERE a metric saturates to 0 or 100, not whether the metric itself is
# meaningful) ────────────────────────────────────────────────────────────────
SAMPLE_SIZE_IDEAL = 200          # occurrences at/above this -> full marks
DAYS_OBSERVED_IDEAL = 15         # distinct days at/above this -> full marks
MFE_MAE_RATIO_FLOOR = 1.0        # MFE:MAE at/below this -> 0 (no asymmetric edge)
MFE_MAE_RATIO_IDEAL = 3.0        # MFE:MAE at/above this -> full marks
MAE_STDEV_WORST_PCT = 30.0       # MAE% stdev at/above this -> 0 (unpredictable downside)

CANDIDATE_QUEUE_SIZE = 10
MIN_SAMPLE_FOR_QUEUE = pstats.MIN_SAMPLE_SIZE  # reused, not redeclared


def _scale(value: float | None, floor: float, ideal: float) -> float:
    """Linear 0-100 between floor and ideal; None -> 0 (never guessed)."""
    if value is None:
        return 0.0
    if ideal == floor:
        return 100.0 if value >= ideal else 0.0
    span = (value - floor) / (ideal - floor)
    return round(max(0.0, min(1.0, span)) * 100, 1)


def _core_stats(core_pid: str, recs: list[dict[str, Any]]) -> dict[str, Any]:
    """Reuses pattern_stats' own per-group calculator (it only needs a list
    of records — it doesn't care whether the grouping key was pattern_id or
    core_pattern_id), then relabels signature/tags to the CORE ones so the
    output doesn't misleadingly show one arbitrary member's full (regime-
    specific) signature."""
    s = pstats._pattern_stats_one(core_pid, recs)
    s["pattern_id"] = core_pid
    s["signature"] = pext.core_signature(recs[0]) if recs else ""
    s["tags"] = pext.core_tags(recs[0]) if recs else []
    return s


def _drawdown_stdev(recs: list[dict[str, Any]]) -> float | None:
    import statistics
    mae_vals = [(r.get("outcome_join") or {}).get("mae_pct") for r in recs]
    mae_vals = [v for v in mae_vals if v is not None]
    return round(statistics.pstdev(mae_vals), 1) if len(mae_vals) >= 2 else None


def classify(pqi: float) -> dict[str, str]:
    if pqi >= 90:
        return {"stars": "★★★★★", "label": "Institution Grade"}
    if pqi >= 80:
        return {"stars": "★★★★☆", "label": "High Confidence"}
    if pqi >= 70:
        return {"stars": "★★★☆☆", "label": "Needs Observation"}
    if pqi >= 60:
        return {"stars": "★★☆☆☆", "label": "Weak Evidence"}
    return {"stars": "☆☆☆☆☆", "label": "Research Only"}


def pattern_quality_index(core_pid: str, recs: list[dict[str, Any]]) -> dict[str, Any]:
    """PQI + component breakdown + classification for ONE core pattern.
    Every component is independently computed and reported — nothing here
    is hidden inside the final number."""
    stats = _core_stats(core_pid, recs)
    core_val = ev.validate_core_pattern(core_pid, recs)

    sample_size_score = _scale(stats["occurrences"], 0, SAMPLE_SIZE_IDEAL)
    days_observed_score = _scale(stats["days_observed"], 0, DAYS_OBSERVED_IDEAL)

    win_rates = list(stats["win_rate_by_day"].values())
    win_spread = round(max(win_rates) - min(win_rates), 1) if len(win_rates) >= 2 else None
    win_stability_score = max(0.0, 100 - win_spread) if win_spread is not None else 0.0

    # diverse-but-inconsistent is real negative evidence (the logic does NOT
    # generalize) and scores lower than "not enough evidence either way" —
    # deliberately not the same as 0, so the two cases stay distinguishable
    # in the breakdown even though both currently score low.
    if not core_val["regime_diversity_sufficient"]:
        cross_regime_score = 0.0
    else:
        cross_regime_score = 100.0 if core_val["regime_consistent"] else 10.0
    if not core_val["session_diversity_sufficient"]:
        cross_session_score = 0.0
    else:
        cross_session_score = 100.0 if core_val["session_consistent"] else 10.0

    mfe, mae = stats["avg_mfe_pct"], stats["avg_mae_pct"]
    ratio = (mfe / mae) if (mfe is not None and mae) else None
    mfe_mae_score = _scale(ratio, MFE_MAE_RATIO_FLOOR, MFE_MAE_RATIO_IDEAL) if ratio is not None else 0.0

    mae_stdev = _drawdown_stdev(recs)
    drawdown_score = (max(0.0, 100 - (mae_stdev / MAE_STDEV_WORST_PCT * 100))
                       if mae_stdev is not None else 0.0)

    components = {
        "sample_size": sample_size_score, "days_observed": days_observed_score,
        "win_stability": win_stability_score, "cross_regime": cross_regime_score,
        "cross_session": cross_session_score, "mfe_mae_ratio": mfe_mae_score,
        "drawdown_consistency": drawdown_score,
    }
    pqi = round(sum(components[k] * WEIGHTS[k] / 100 for k in WEIGHTS), 1)

    return {
        "pattern_id": core_pid,
        "signature": stats["signature"],
        "occurrences": stats["occurrences"],
        "days_observed": stats["days_observed"],
        "pqi": pqi,
        **classify(pqi),
        "components": components,
        # raw inputs behind each component, for anyone auditing the score
        "raw": {
            "win_rate_spread_pct": win_spread,
            "regime_diversity_sufficient": core_val["regime_diversity_sufficient"],
            "regime_consistent": core_val["regime_consistent"],
            "session_diversity_sufficient": core_val["session_diversity_sufficient"],
            "session_consistent": core_val["session_consistent"],
            "avg_mfe_pct": mfe, "avg_mae_pct": mae, "mfe_mae_ratio": (
                round(ratio, 2) if ratio is not None else None),
            "mae_stdev_pct": mae_stdev,
        },
    }


def rank_patterns(records: list[dict[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
    """PQI for every core pattern found. Plain dict keyed by core_pattern_id —
    NOT sorted; use research_candidate_queue() for the ordered top-N."""
    recs = records if records is not None else pstats.load_records()
    groups = pext.group_by_core(recs)
    return {cpid: pattern_quality_index(cpid, g) for cpid, g in groups.items()}


def research_candidate_queue(records: list[dict[str, Any]] | None = None,
                              size: int = CANDIDATE_QUEUE_SIZE) -> list[dict[str, Any]]:
    """Top-N core patterns by PQI, filtered to a minimum sample size first —
    this is the ONLY list that should ever reach Walk-Forward/Monte
    Carlo/the Proposal Engine; everything else stays in the full ranking
    for transparency but isn't a candidate for anything yet."""
    ranked = rank_patterns(records)
    eligible = [r for r in ranked.values() if r["occurrences"] >= MIN_SAMPLE_FOR_QUEUE]
    eligible.sort(key=lambda r: r["pqi"], reverse=True)
    return eligible[:size]
