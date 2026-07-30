"""V8 Research Dashboard (v8-dev, 2026-07-30) — the ONE exception to the
v8-dev code freeze the owner explicitly carved out (see docs/V8_STATUS.md):
a read-only aggregation of the already-built pipeline's own outputs, so
research PROGRESS is visible during the 2-4 week live-data-collection
window without building any new pipeline logic, threshold, gate, or
statistical method. Every number below is computed by calling an existing
module's existing function — this file adds zero new evidence math.

Explicitly NOT a trading surface: no BUY/SELL, no decision, no proposal.
Measures how much evidence exists and how it's trending, nothing else.

Metrics (owner's list, 2026-07-30):
  - Total Patterns / Total Core Patterns  — pattern_extractor grouping counts
  - Validated Patterns                    — evidence_validator VALIDATED count
  - PQI Distribution                      — pattern_ranking star-band counts
  - Walk-Forward PASS %                   — over the Candidate Queue only
                                             (walk-forward never runs on
                                             anything else — see
                                             walk_forward_patterns.py)
  - Promotion Rate                        — over the Candidate Queue only
  - Evidence Growth                       — cumulative record count by day
  - Regime Coverage / Session Coverage    — composition across ALL records
"""
from __future__ import annotations

from typing import Any

from . import evidence_validator as ev
from . import pattern_extractor as pext
from . import pattern_ranking as prank
from . import pattern_stats as pstats
from . import promotion_gate as pg
from . import walk_forward_patterns as wfp


def _evidence_growth(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    day_counts: dict[str, int] = {}
    for r in records:
        d = r.get("day")
        if d:
            day_counts[d] = day_counts.get(d, 0) + 1
    running = 0
    out = []
    for day in sorted(day_counts):
        running += day_counts[day]
        out.append({"day": day, "records_that_day": day_counts[day],
                    "cumulative_total": running})
    return out


def build_report(records: list[dict[str, Any]] | None = None,
                  queue_size: int = prank.CANDIDATE_QUEUE_SIZE) -> dict[str, Any]:
    """One aggregated research-progress snapshot. Safe to call repeatedly —
    read-only over data/opportunity_log, no live broker connection needed."""
    recs = records if records is not None else pstats.load_records()

    pattern_groups = pext.group_records(recs)       # pattern_id level (regime/session baked in)
    core_groups = pext.group_by_core(recs)           # core level (regime/session excluded)

    ev_results = ev.validate_patterns(recs)
    validated = sum(1 for r in ev_results.values() if r["status"] == "VALIDATED")

    ranked_core = prank.rank_patterns(recs)
    pqi_distribution = {"Institution Grade": 0, "High Confidence": 0,
                         "Needs Observation": 0, "Weak Evidence": 0, "Research Only": 0}
    for r in ranked_core.values():
        pqi_distribution[r["label"]] = pqi_distribution.get(r["label"], 0) + 1

    wf_results = wfp.run_walk_forward_on_queue(recs, queue_size=queue_size)
    wf_total = len(wf_results)
    wf_pass = sum(1 for r in wf_results.values() if r["verdict"] == "PASS")

    promo_results = pg.run_promotion_gate(recs, queue_size=queue_size)
    promo_total = len(promo_results)
    promoted = sum(1 for r in promo_results.values() if r["promoted"])

    return {
        "total_records": len(recs),
        "total_patterns": len(pattern_groups),
        "total_core_patterns": len(core_groups),
        "validated_patterns": validated,
        "validated_patterns_pct": (round(validated / len(pattern_groups) * 100, 1)
                                    if pattern_groups else None),
        "pqi_distribution": pqi_distribution,
        "walk_forward": {
            "candidates_tested": wf_total, "pass_count": wf_pass,
            "pass_pct": round(wf_pass / wf_total * 100, 1) if wf_total else None,
        },
        "promotion": {
            "candidates_evaluated": promo_total, "promoted": promoted,
            "promotion_rate_pct": round(promoted / promo_total * 100, 1) if promo_total else None,
        },
        "evidence_growth": _evidence_growth(recs),
        "regime_coverage": ev.composition([r.get("regime") for r in recs]),
        "session_coverage": ev.composition([r.get("session_type") for r in recs]),
    }
