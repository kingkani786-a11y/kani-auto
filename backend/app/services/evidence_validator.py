"""V8 Evidence Validator — the new gate the owner inserted before Phase 3C
(v8-dev, 2026-07-30):

    Pattern Extractor (3A) -> Pattern Statistics (3B) -> Evidence Validator
    (THIS FILE) -> Pattern Ranking (3C) -> Walk-Forward -> Monte Carlo ->
    Proposal Engine

Purely mechanical fact-checks over Phase 3B's per-pattern stats and the
underlying records — never a quality judgment, never a numeric confidence
score (that's Phase 3C), never BUY/SELL/threshold/weight text (that's the
Proposal Engine, and only after human approval). Every check here answers
one yes/no question about whether a pattern's EVIDENCE is even solid enough
to bother ranking, walk-forward-testing, or proposing anything from — not
whether the pattern itself is good.

Checks, each independently boolean:
  - sample_size_sufficient    — enough occurrences (reuses 3B's own bar)
  - days_observed_sufficient  — enough distinct calendar days
  - win_rate_stable           — day-to-day win% doesn't swing wildly
                                 (the same "single-session reads are
                                 unreliable" lesson already logged for OBS-2,
                                 now checked mechanically per pattern)
  - not single_day_concentrated — no one day supplies most of the occurrences
                                 ("is this just a lucky day?")
  - not min_tick_polluted     — not dominated by ₹0.05-tick episodes whose
                                 percentages are statistically meaningless
                                 (the exact OBS-6 finding, checked per pattern
                                 instead of only at the dashboard-panel level)

`walk_forward_eligible` is the AND of all five. `regime_composition` /
`session_composition` / `time_of_day_composition` are reported as FACTS, not
pass/fail checks — see the important caveat in `validate_pattern()`'s
docstring about why regime/session diversity cannot be tested at the
per-pattern-id level under the current Phase 3A tag design.
"""
from __future__ import annotations

import statistics
from typing import Any

from . import pattern_extractor as pext
from . import pattern_stats as pstats

# ── declared thresholds (statistical evidence bar, NOT a trading gate —
# these only decide whether a pattern is solid enough to rank/test further;
# unvalidated, same declared-not-fitted convention as the rest of V8) ───────
MIN_DAYS_OBSERVED = 5           # fewer distinct days = not enough calendar spread
MAX_SINGLE_DAY_SHARE_PCT = 50.0  # one day supplying more than this % = "lucky day"
MAX_WIN_RATE_SPREAD_PCT = 40.0   # max-min of win_rate_by_day above this = unstable
MIN_TICK_BASE = 0.10             # base premium at/below this = a min-tick episode (OBS-6)
MAX_MIN_TICK_SHARE_PCT = 20.0    # more than this % min-tick episodes = polluted evidence

# NSE session time bands (IST), for the "Morning only?" check — there is no
# existing tag for time-of-day anywhere in the codebase, so this reads the
# hour straight off the already-logged t_ignite (or t_base if never alerted)
# timestamp string rather than inventing a new Phase 3A tag for it.
_TIME_BANDS = (("MORNING", 9, 11), ("MIDDAY", 11, 13.5), ("AFTERNOON", 13.5, 15.5))
MAX_SINGLE_TIME_BAND_SHARE_PCT = 70.0


def _time_band(hhmmss: str | None) -> str | None:
    if not hhmmss:
        return None
    try:
        h, m, _s = (int(x) for x in hhmmss.split(":"))
    except (ValueError, AttributeError):
        return None
    hour = h + m / 60.0
    for name, lo, hi in _TIME_BANDS:
        if lo <= hour < hi:
            return name
    return None


def _composition(values: list[str]) -> dict[str, float]:
    """{value: % share}, ignoring Nones."""
    vals = [v for v in values if v]
    if not vals:
        return {}
    n = len(vals)
    counts: dict[str, int] = {}
    for v in vals:
        counts[v] = counts.get(v, 0) + 1
    return {k: round(c / n * 100, 1) for k, c in counts.items()}


def validate_pattern(pid: str, recs: list[dict[str, Any]],
                      stats: dict[str, Any] | None = None) -> dict[str, Any]:
    """Run all evidence checks for one pattern's occurrences.

    IMPORTANT CAVEAT (flagged to the owner, not silently resolved): under the
    current Phase 3A tag design, REGIME_*/SESSION_* are part of a pattern's
    own identity (baked into pattern_id via pattern_signature()). That means
    every record in `recs` is STRUCTURALLY guaranteed to share the same
    regime and the same session_type — a fixed pattern_id can never contain
    a mix of TRENDING and VOLATILE, or NORMAL and EXPIRY. So
    regime_composition/session_composition below will always show ~100% in
    one bucket, by construction, not because the evidence happens to be
    concentrated. That is reported honestly as a fact (and as an informational
    caveat), but it is NOT the same question as "does this pattern generalize
    across market regimes" — answering that properly needs a *different*
    grouping (a "core signature" excluding REGIME_*/SESSION_*), which is a
    structural change to what a "pattern" means in Phases 3A/3B, not
    something to decide inside a validator. time_of_day_composition (below)
    is NOT baked into pattern identity, so that check IS a genuine, meaningful
    diversity check as run here.
    """
    n = len(recs)
    stats = stats or pstats._pattern_stats_one(pid, recs)

    sample_size_sufficient = not stats["insufficient_sample"]
    days_observed_sufficient = stats["days_observed"] >= MIN_DAYS_OBSERVED

    win_rates = list(stats["win_rate_by_day"].values())
    win_rate_spread = round(max(win_rates) - min(win_rates), 1) if len(win_rates) >= 2 else None
    win_rate_stdev = round(statistics.pstdev(win_rates), 1) if len(win_rates) >= 2 else None
    # can't judge stability off a single day — neither stable nor unstable,
    # just not yet decidable (never fabricate a verdict from insufficient data)
    win_rate_stable = (win_rate_spread is not None and win_rate_spread <= MAX_WIN_RATE_SPREAD_PCT)

    days = [r.get("day") for r in recs if r.get("day")]
    day_counts: dict[str, int] = {}
    for d in days:
        day_counts[d] = day_counts.get(d, 0) + 1
    single_day_share = round(max(day_counts.values()) / n * 100, 1) if day_counts else None
    single_day_concentrated = single_day_share is not None and single_day_share > MAX_SINGLE_DAY_SHARE_PCT

    bases = [r.get("base") for r in recs if r.get("base") is not None]
    min_tick_n = sum(1 for b in bases if b <= MIN_TICK_BASE)
    min_tick_share = round(min_tick_n / len(bases) * 100, 1) if bases else 0.0
    min_tick_polluted = min_tick_share > MAX_MIN_TICK_SHARE_PCT

    regime_composition = _composition([r.get("regime") for r in recs])
    session_composition = _composition([r.get("session_type") for r in recs])
    time_bands = [_time_band(r.get("t_ignite") or r.get("t_base")) for r in recs]
    time_of_day_composition = _composition(time_bands)
    single_time_band_share = max(time_of_day_composition.values()) if time_of_day_composition else None
    single_time_band_concentrated = (single_time_band_share is not None
                                      and single_time_band_share > MAX_SINGLE_TIME_BAND_SHARE_PCT)

    # each entry: (check name, True == PASSING for this check)
    checks_ok = {
        "sample_size_sufficient": sample_size_sufficient,
        "days_observed_sufficient": days_observed_sufficient,
        "win_rate_stable": win_rate_stable,
        "not_single_day_concentrated": not single_day_concentrated,
        "not_min_tick_polluted": not min_tick_polluted,
        "not_single_time_band_concentrated": not single_time_band_concentrated,
    }
    failed = [name for name, ok in checks_ok.items() if not ok]
    walk_forward_eligible = all(checks_ok.values())

    return {
        "pattern_id": pid,
        "occurrences": n,
        "sample_size_sufficient": sample_size_sufficient,
        "days_observed": stats["days_observed"],
        "days_observed_sufficient": days_observed_sufficient,
        "win_rate_spread_pct": win_rate_spread,
        "win_rate_stdev_pct": win_rate_stdev,
        "win_rate_stable": win_rate_stable,
        "single_day_share_pct": single_day_share,
        "single_day_concentrated": single_day_concentrated,
        "min_tick_share_pct": min_tick_share,
        "min_tick_polluted": min_tick_polluted,
        # informational facts, not pass/fail — see caveat above
        "regime_composition": regime_composition,
        "session_composition": session_composition,
        "time_of_day_composition": time_of_day_composition,
        "single_time_band_concentrated": single_time_band_concentrated,
        "walk_forward_eligible": walk_forward_eligible,
        "status": "VALIDATED" if walk_forward_eligible else "NOT_VALIDATED",
        "failed_checks": failed,
    }


def validate_patterns(records: list[dict[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
    """Run the Evidence Validator over every pattern found in `records` (or
    every logged record, if none given). Returns a plain dict keyed by
    pattern_id — no ranking, no ordering by eligibility or anything else."""
    recs = records if records is not None else pstats.load_records()
    groups = pext.group_records(recs)
    all_stats = pstats.compute_pattern_stats(recs)
    return {pid: validate_pattern(pid, g, stats=all_stats.get(pid))
            for pid, g in groups.items()}
