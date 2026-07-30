"""V8 Promotion Gate (v8-dev, 2026-07-30).

Pipeline position (owner, 2026-07-30):
    Candidate Queue -> Walk-Forward -> {FAIL: Archive, INSUFFICIENT_DATA:
    Wait for More Data, UNSTABLE: Observe, PASS: PROMOTION GATE (THIS FILE)
    -> Monte Carlo} -> Proposal Engine -> Human Approval

A pattern reaching Walk-Forward PASS is necessary but the owner wants it
treated as not sufficient on its own before spending Monte Carlo compute
on it. This gate ANDs five checks together — reusing already-built
functions, no new statistical logic:

  - min_sample          occurrences >= pattern_stats.MIN_SAMPLE_SIZE (reused)
  - min_days            days_observed >= evidence_validator.MIN_DAYS_OBSERVED (reused)
  - min_pqi             pattern_ranking PQI >= MIN_PQI_FOR_PROMOTION (declared below)
  - evidence_validated  evidence_validator.validate_pattern(...).status == VALIDATED
  - walk_forward_pass   walk_forward_patterns verdict == PASS

Only patterns clearing ALL FIVE are PROMOTED_TO_MONTE_CARLO. Still no
BUY/SELL, no threshold/weight text — this is purely "is it worth spending
Monte Carlo compute on this candidate", not a trading judgment.
"""
from __future__ import annotations

from typing import Any

from . import evidence_validator as ev
from . import pattern_extractor as pext
from . import pattern_ranking as prank
from . import pattern_stats as pstats
from . import walk_forward_patterns as wfp

MIN_PQI_FOR_PROMOTION = 80.0  # declared (High Confidence band or above) —
                              # unvalidated, same declared-not-fitted
                              # convention as every other V8 threshold


def evaluate_promotion(core_pid: str, recs: list[dict[str, Any]],
                        pqi_result: dict[str, Any] | None = None,
                        evidence_result: dict[str, Any] | None = None,
                        walk_forward_result: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run all five checks for one candidate. Callers may pass already-
    computed results (e.g. from a batch run) to avoid recomputing; each is
    computed fresh from `recs` if omitted."""
    pqi_result = pqi_result or prank.pattern_quality_index(core_pid, recs)
    # validate_pattern() only needs an id + a record list — it doesn't care
    # whether the grouping key was pattern_id or core_pattern_id; every check
    # it runs (sample size, days, win-rate-by-day stability, single-day
    # concentration, min-tick pollution, time-band concentration) is equally
    # valid over any group of records.
    evidence_result = evidence_result or ev.validate_pattern(core_pid, recs)
    walk_forward_result = walk_forward_result or wfp.walk_forward_pattern(core_pid, recs)

    checks = {
        "min_sample": pqi_result["occurrences"] >= pstats.MIN_SAMPLE_SIZE,
        "min_days": pqi_result["days_observed"] >= ev.MIN_DAYS_OBSERVED,
        "min_pqi": pqi_result["pqi"] >= MIN_PQI_FOR_PROMOTION,
        "evidence_validated": evidence_result["status"] == "VALIDATED",
        "walk_forward_pass": walk_forward_result["verdict"] == "PASS",
    }
    promoted = all(checks.values())

    return {
        "pattern_id": core_pid,
        "signature": pqi_result.get("signature"),
        "occurrences": pqi_result["occurrences"],
        "days_observed": pqi_result["days_observed"],
        "pqi": pqi_result["pqi"],
        "evidence_status": evidence_result["status"],
        "walk_forward_verdict": walk_forward_result["verdict"],
        "checks": checks,
        "failed_checks": [k for k, v in checks.items() if not v],
        "promoted": promoted,
        "status": "PROMOTED_TO_MONTE_CARLO" if promoted else "NOT_PROMOTED",
    }


def run_promotion_gate(records: list[dict[str, Any]] | None = None,
                        queue_size: int = prank.CANDIDATE_QUEUE_SIZE) -> dict[str, dict[str, Any]]:
    """Runs the gate over the Research Candidate Queue only (same rule as
    Walk-Forward — never over every pattern ever seen). Returns
    {pattern_id: evaluate_promotion(...)}; only entries with
    status == PROMOTED_TO_MONTE_CARLO should ever reach Monte Carlo."""
    recs = records if records is not None else pstats.load_records()
    queue = prank.research_candidate_queue(recs, size=queue_size)
    groups = pext.group_by_core(recs)
    wf_results = wfp.run_walk_forward_on_queue(recs, queue_size=queue_size)
    out: dict[str, dict[str, Any]] = {}
    for c in queue:
        pid = c["pattern_id"]
        if pid not in groups:
            continue
        out[pid] = evaluate_promotion(pid, groups[pid], pqi_result=c,
                                       walk_forward_result=wf_results.get(pid))
    return out


def promoted_patterns(records: list[dict[str, Any]] | None = None,
                       queue_size: int = prank.CANDIDATE_QUEUE_SIZE) -> list[dict[str, Any]]:
    """Just the patterns that cleared every gate — this list, and only this
    list, is what Monte Carlo (not yet built — owner: nothing clears this
    gate yet with today's data, so there is nothing to run it on) would
    ever receive."""
    results = run_promotion_gate(records, queue_size)
    return [r for r in results.values() if r["promoted"]]
