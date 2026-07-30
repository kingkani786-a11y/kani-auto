"""V8 Phase 3B — Pattern Statistics (v8-dev, 2026-07-30).

Owner's own sub-phase split for V8 Phase 3 (Pattern Mining):
    3A Pattern Extractor  — tag each episode with the conditions present. (done)
    3B Pattern Statistics — occurrences / win% / avg MFE-MAE / avg timing. (THIS FILE)
    3C Pattern Ranking    — confidence / reliability / sample size / regime. (not yet)

THIS FILE IS 3B ONLY, per the owner's explicit scope: three things only —
(1) occurrence count, (2) performance metrics (win%/MFE/MAE/etc), (3)
stability (sample size/consistency). No recommendation, no trading
decision, no "this pattern is good/bad" verdict, no ordering by quality —
those are Phase 3C (ranking) and Phase 4 (validation + proposals),
explicitly NOT this file. `compute_pattern_stats()` returns a plain dict
keyed by pattern_id, in no particular order — callers must not read
dict order as a ranking.

Pure analytics over already-closed episodes (every line in
data/opportunity_log/*.jsonl is a CLOSED episode — opportunity_metrics only
ever calls _black_box() from _close_episode()). Read-only; never touches
live state, never runs as part of any gate.
"""
from __future__ import annotations

import json
import pathlib
import statistics
from typing import Any

from . import pattern_extractor as pext

# same log directory opportunity_metrics.py itself resolves to (or override)
import os
_LOG_DIR = (pathlib.Path(os.environ["CAT_DATA_DIR"]) if os.getenv("CAT_DATA_DIR")
            else pathlib.Path(__file__).resolve().parents[3] / "data" / "opportunity_log")

# declared (statistical, not trading) threshold — a rule-of-thumb minimum
# sample size below which a win-rate is not treated as meaningful evidence.
# This is NOT a trading gate; it only labels a fact ("insufficient_sample")
# for a human or Phase 4 to weigh, exactly as the owner specified: the AI
# reports "sample size insufficient", it doesn't decide anything from it.
MIN_SAMPLE_SIZE = 30


def load_records(paths: list[str] | None = None) -> list[dict[str, Any]]:
    """Read every black-box line from data/opportunity_log/*.jsonl (or an
    explicit file list). Tolerant of a corrupt/partial line — skips it rather
    than aborting the whole load, since one bad line must never hide every
    other day's evidence."""
    files = [pathlib.Path(p) for p in paths] if paths else sorted(_LOG_DIR.glob("*.jsonl"))
    records: list[dict[str, Any]] = []
    for f in files:
        try:
            with f.open() as fh:
                for line in fh:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        except OSError:
            continue
    return records


def _avg(values: list[float]) -> float | None:
    return round(statistics.fmean(values), 2) if values else None


def _group_by_pattern(records: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for r in records:
        pid = pext.pattern_id(r)
        groups.setdefault(pid, []).append(r)
    return groups


def _pattern_stats_one(pid: str, recs: list[dict[str, Any]]) -> dict[str, Any]:
    n = len(recs)
    days = {r.get("day") for r in recs if r.get("day")}
    outcomes = [r.get("outcome") for r in recs]
    wins = sum(1 for o in outcomes if o == "SUCCESS")
    losses = sum(1 for o in outcomes if o in ("FALSE", "FADE"))
    # a record's outcome can only be SUCCESS/FALSE/FADE (see opportunity_metrics
    # ._classify) so wins+losses == n always, for every record actually logged.

    oj = [r.get("outcome_join") or {} for r in recs]
    mfe = [x["mfe_pct"] for x in oj if x.get("mfe_pct") is not None]
    mae = [x["mae_pct"] for x in oj if x.get("mae_pct") is not None]
    t_target = [x["time_to_target_s"] for x in oj if x.get("time_to_target_s") is not None]
    t_failure = [x["time_to_failure_s"] for x in oj if x.get("time_to_failure_s") is not None]
    decay = [x["premium_decay_pct"] for x in oj if x.get("premium_decay_pct") is not None]

    win_rate_by_day: dict[str, float] = {}
    for day in sorted(days):
        day_recs = [r for r in recs if r.get("day") == day]
        day_outcomes = [r.get("outcome") for r in day_recs]
        day_wins = sum(1 for o in day_outcomes if o == "SUCCESS")
        win_rate_by_day[day] = round(day_wins / len(day_recs) * 100, 1) if day_recs else 0.0

    return {
        "pattern_id": pid,
        "signature": pext.pattern_signature(recs[0]),
        "tags": pext.extract_tags(recs[0]),
        "occurrences": n,
        "days_observed": len(days),
        "win": wins, "loss": losses,
        "win_pct": round(wins / n * 100, 1) if n else None,
        "loss_pct": round(losses / n * 100, 1) if n else None,
        # denominators differ from `occurrences` on purpose — most of these
        # metrics are only defined for alerted episodes (see
        # opportunity_metrics._outcome_join); reporting each metric's own
        # sample count alongside it, rather than silently dividing by `n`,
        # so nobody misreads e.g. avg_mfe_pct as "average over ALL occurrences"
        # when it may really be "average over the 40 of 65 that were alerted".
        "avg_mfe_pct": _avg(mfe), "mfe_n": len(mfe),
        "avg_mae_pct": _avg(mae), "mae_n": len(mae),
        "avg_time_to_target_s": _avg(t_target), "time_to_target_n": len(t_target),
        "avg_time_to_failure_s": _avg(t_failure), "time_to_failure_n": len(t_failure),
        "avg_premium_decay_pct": _avg(decay), "decay_n": len(decay),
        "sample_size": n,
        "insufficient_sample": n < MIN_SAMPLE_SIZE,
        "win_rate_by_day": win_rate_by_day,
    }


def compute_pattern_stats(records: list[dict[str, Any]] | None = None) -> dict[str, dict[str, Any]]:
    """Group already-closed episodes by pattern_id and compute pure
    occurrence/performance/stability facts for each — no ranking, no
    ordering by any performance measure, no recommendation. Returned dict's
    key order is NOT a ranking; callers must not treat it as one (that's
    Phase 3C's job, not built here)."""
    recs = records if records is not None else load_records()
    groups = _group_by_pattern(recs)
    return {pid: _pattern_stats_one(pid, g) for pid, g in groups.items()}
