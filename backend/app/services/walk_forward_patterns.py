"""V8 Walk-Forward — Candidate Patterns (v8-dev, 2026-07-30).

Pipeline position (owner, 2026-07-30):
    ... -> Phase 3C Ranking -> Research Candidate Queue -> WALK-FORWARD
    (THIS FILE) -> Monte Carlo -> Proposal Engine -> Human Approval

NOT the same thing as backend/app/services/walk_forward.py. That module
walk-forward-validates the EXISTING FIXED BACKTEST STRATEGY across
year-anchored folds (2022→2023, …→2026) using backtest.run() against years
of historical candle data. This file walk-forward-validates INDIVIDUAL
CANDIDATE PATTERNS discovered by Phase 3A-3C, using the black-box
opportunity log — a much shorter history (currently ~12-16 days total,
growing daily) — chronologically split into folds. Different validation
target, different data source, different fold granularity. Both are
legitimately "Walk-Forward"; they answer different questions.

Owner's explicit rule for this file: walk-forward MUST run only on
pattern_ranking.research_candidate_queue() — the top-N, sample-filtered
core patterns — never on every pattern ever seen. That queue is the sole
entry point here (see run_walk_forward_on_queue()).

Per candidate: split its own occurrences chronologically (by day, oldest
folds first) into up to MAX_FOLDS contiguous folds, compute Win Rate /
Profit Factor / Expectancy / Max Drawdown per fold, then a cross-fold
stability check, producing exactly one of three verdicts per the owner's
spec: PASS / FAIL / UNSTABLE. A fourth, honest state — INSUFFICIENT_DATA —
is used ONLY when there isn't enough chronological spread to construct
even 2 folds; this is flagged here explicitly as an addition to the
3-verdict design, not something silently folded into UNSTABLE (declaring
"unstable" implies we tested it and it wobbled; "insufficient data" means
we could not test it at all — different facts, and conflating them would
be exactly the kind of fabrication this project's own doctrine forbids).

IMPORTANT — Profit Factor / Expectancy are a labeled PROXY, not real P&L.
The system never places orders (standing doctrine), so there is no actual
realized trade P&L anywhere in this dataset — only opportunity episodes
(see the OBS-5 audit's own correction on this point). The proxy used here:
  - proxy gain = mfe_pts (best favorable excursion since entry) when the
    episode's outcome was SUCCESS
  - proxy loss = mae_pts (worst adverse excursion since entry) when the
    outcome was FALSE or FADE
This uses ONLY fields Phase 2 already logged — no new exit-timing rule is
invented — but it assumes an idealized single exit at the best/worst point
reached, which no real execution could reliably capture. Profit Factor and
Expectancy computed this way are optimistic upper/lower bounds, not
achievable round-trip returns. Flagged here so nobody downstream mistakes
this for a real backtest P&L.
"""
from __future__ import annotations

import statistics
from typing import Any

from . import pattern_extractor as pext
from . import pattern_ranking as prank
from . import pattern_stats as pstats

# ── declared thresholds (unvalidated, same declared-not-fitted convention as
# the rest of V8) ────────────────────────────────────────────────────────────
MAX_FOLDS = 5
MIN_FOLDS = 2                        # below this, no verdict can be reached at all
MIN_OCCURRENCES_PER_FOLD = 5         # a fold with fewer occurrences than this is
                                     # marked insufficient and excluded from the
                                     # cross-fold verdict (but still reported)
FAIL_WIN_RATE_PCT = 45.0            # pooled win rate below this -> FAIL
FAIL_PROFIT_FACTOR = 1.0            # pooled profit factor below this -> FAIL
UNSTABLE_WIN_RATE_FOLD_SPREAD_PCT = 40.0  # fold-to-fold win-rate spread above this
                                           # (and not already a FAIL) -> UNSTABLE


def chronological_folds(recs: list[dict[str, Any]], max_folds: int = MAX_FOLDS
                         ) -> list[list[dict[str, Any]]]:
    """Split records into up to `max_folds` contiguous, chronologically
    ordered folds by DAY (not by occurrence count) — walking forward through
    time, not through an arbitrarily shuffled pile. Fold count adapts down
    to however many distinct days actually exist."""
    days = sorted({r.get("day") for r in recs if r.get("day")})
    n_folds = min(max_folds, len(days))
    if n_folds < 1:
        return []
    # split the sorted day list into n_folds contiguous, near-equal chunks
    day_folds: list[list[str]] = []
    base, extra = divmod(len(days), n_folds)
    idx = 0
    for i in range(n_folds):
        take = base + (1 if i < extra else 0)
        day_folds.append(days[idx:idx + take])
        idx += take
    day_to_fold = {d: i for i, fold_days in enumerate(day_folds) for d in fold_days}
    folds: list[list[dict[str, Any]]] = [[] for _ in range(n_folds)]
    for r in recs:
        i = day_to_fold.get(r.get("day"))
        if i is not None:
            folds[i].append(r)
    return folds


def _fold_metrics(fold_recs: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(fold_recs)
    if n < MIN_OCCURRENCES_PER_FOLD:
        return {"n": n, "sufficient": False, "win_rate_pct": None,
                "profit_factor": None, "expectancy_pts": None, "max_drawdown_pct": None}

    wins = sum(1 for r in fold_recs if r.get("outcome") == "SUCCESS")
    win_rate = round(wins / n * 100, 1)

    proxy_pnls: list[float] = []
    mae_values: list[float] = []
    for r in fold_recs:
        oj = r.get("outcome_join") or {}
        outcome = r.get("outcome")
        mfe, mae = oj.get("mfe_pts"), oj.get("mae_pts")
        if outcome == "SUCCESS" and mfe is not None:
            proxy_pnls.append(mfe)
        elif outcome in ("FALSE", "FADE") and mae is not None:
            proxy_pnls.append(-mae)
        else:
            proxy_pnls.append(0.0)
        if mae is not None:
            mae_values.append(mae)

    gains = sum(p for p in proxy_pnls if p > 0)
    losses = sum(-p for p in proxy_pnls if p < 0)
    profit_factor = round(gains / losses, 2) if losses > 0 else (None if gains == 0 else float("inf"))
    expectancy = round(statistics.fmean(proxy_pnls), 2) if proxy_pnls else None
    max_drawdown = round(max(mae_values), 1) if mae_values else None

    return {"n": n, "sufficient": True, "win_rate_pct": win_rate,
            "profit_factor": profit_factor, "expectancy_pts": expectancy,
            "max_drawdown_pct": max_drawdown}


def walk_forward_pattern(core_pid: str, recs: list[dict[str, Any]],
                          max_folds: int = MAX_FOLDS) -> dict[str, Any]:
    """Walk-forward one candidate pattern. Returns per-fold metrics, a
    cross-fold stability read, and exactly one verdict: PASS / FAIL /
    UNSTABLE / INSUFFICIENT_DATA (the last is an honest 'could not test',
    not a disguised UNSTABLE — see module docstring)."""
    fold_groups = chronological_folds(recs, max_folds)
    fold_metrics = [_fold_metrics(f) for f in fold_groups]
    sufficient_folds = [m for m in fold_metrics if m["sufficient"]]

    if len(sufficient_folds) < MIN_FOLDS:
        return {
            "pattern_id": core_pid, "n_folds": len(fold_groups),
            "sufficient_folds": len(sufficient_folds),
            "fold_metrics": fold_metrics,
            "verdict": "INSUFFICIENT_DATA",
            "reason": (f"only {len(sufficient_folds)} of {len(fold_groups)} folds had "
                       f"≥{MIN_OCCURRENCES_PER_FOLD} occurrences (need ≥{MIN_FOLDS} to verdict)"),
        }

    # pooled (across all sufficient folds) win rate + profit factor decide
    # PASS vs FAIL; fold-to-fold win-rate SPREAD decides UNSTABLE
    pooled_recs = [r for f in fold_groups for r in f
                    if len(f) >= MIN_OCCURRENCES_PER_FOLD]
    pooled = _fold_metrics(pooled_recs)
    win_rates = [m["win_rate_pct"] for m in sufficient_folds]
    fold_spread = round(max(win_rates) - min(win_rates), 1) if len(win_rates) >= 2 else None

    if pooled["win_rate_pct"] < FAIL_WIN_RATE_PCT or (
            pooled["profit_factor"] is not None and pooled["profit_factor"] < FAIL_PROFIT_FACTOR):
        verdict = "FAIL"
    elif fold_spread is not None and fold_spread > UNSTABLE_WIN_RATE_FOLD_SPREAD_PCT:
        verdict = "UNSTABLE"
    else:
        verdict = "PASS"

    return {
        "pattern_id": core_pid, "n_folds": len(fold_groups),
        "sufficient_folds": len(sufficient_folds),
        "fold_metrics": fold_metrics,
        "pooled_metrics": pooled,
        "fold_win_rate_spread_pct": fold_spread,
        "verdict": verdict,
    }


def run_walk_forward_on_queue(records: list[dict[str, Any]] | None = None,
                               queue_size: int = prank.CANDIDATE_QUEUE_SIZE,
                               max_folds: int = MAX_FOLDS) -> dict[str, dict[str, Any]]:
    """Owner's explicit rule: walk-forward runs ONLY on
    pattern_ranking.research_candidate_queue() — never on every pattern.
    Returns {pattern_id: walk_forward_pattern(...)} for just that queue."""
    recs = records if records is not None else pstats.load_records()
    queue = prank.research_candidate_queue(recs, size=queue_size)
    candidate_ids = {c["pattern_id"] for c in queue}
    groups = pext.group_by_core(recs)
    return {cpid: walk_forward_pattern(cpid, groups[cpid], max_folds=max_folds)
            for cpid in candidate_ids if cpid in groups}
