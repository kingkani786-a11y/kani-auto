"""STRATEGY ROUTER — one evidence view over every measurement system.

Owner-approved 2026-08-08, scoped explicitly as a READ-ONLY AGGREGATOR: it
calls the report()/stats functions the four existing measurement systems
already expose and normalises the *framing* around them. It does not merge,
refactor or re-implement any of their internal logic, and it imports nothing
that can gate a trade.

WHY THIS EXISTS. Four independent measurement systems grew up separately,
each with its own private definition of "win", "sample" and "edge":

  opportunity_metrics.py  premium-radar black box   (detection quality)
  shadow_calibration.py   blocked-cycle calibration (confidence honesty)
  verdicts.py             blocked-cycle shadow P&L  (per-blocker value)
  orfe_research.py        Opening-Range/Fib backtest(setup edge)

Nothing let you see them side by side, so "which strategy actually has an
edge?" had no single place to be answered.

THE HONEST PART — why there is deliberately NO unified score here.
These four do not measure the same thing, and averaging them would
manufacture a number with no meaning:

  * A radar CAPTURE RATE ("we alerted early on 74% of runners") says nothing
    about whether trading those alerts made money.
  * A CALIBRATION SCORE ("confidence 70 wins ~70% of the time") measures
    honesty of a probability, not profit. A perfectly calibrated system can
    lose money, and a badly calibrated one can make it.
  * A BLOCKER's saved/missed ratio measures whether one veto rule earns its
    keep — a property of a gate, not of a strategy.
  * Only a source that records entry, stop, target and realised outcome in
    the SAME units can speak to edge at all.

So every entry below declares `edge_expressible` with a reason, and the
`edge_comparable` section admits only sources that genuinely qualify. A
source that cannot speak to profit is reported as such rather than being
given a placeholder number — the same discipline as marking data UNKNOWN
instead of defaulting it to zero.

Sample sizes are reported raw, with the source's own status vocabulary
(BUILDING / LEARNING / MEASURED) preserved rather than flattened, and every
row carries `blockers_to_decision_grade`: what is actually still missing
before that evidence could responsibly inform a threshold or entry change.
This module never proposes such a change; it only shows how far the evidence
is from being able to support one.
"""
from __future__ import annotations

import time
from typing import Any

# THE OWNER'S OWN DECLARED BAR, not a number invented here (2026-08-07, on the
# ORFE hypothesis): "குறைந்தது 100 Trading Days அல்லது 500 Signals" — at least
# 100 trading days OR 500 signals before a result is treated as real.
# Satisfying EITHER is enough, exactly as stated.
#
# This is set deliberately at the owner's bar rather than a looser statistical
# default: a first draft of this module used 100 samples / 20 days and duly
# reported ORFE (83 days, 288 rows) as DECISION_GRADE — i.e. it would have told
# the owner their own hypothesis was proven when by their own rule it is not.
# An aggregator that grades evidence more leniently than the person relying on
# it is worse than no aggregator.
MIN_SAMPLE_DECISION_GRADE = 500
MIN_DAYS_DECISION_GRADE = 100


def _safe(fn, *a, **kw) -> tuple[Any, str | None]:
    """Call a source's own reporter. A research aggregator must never be able
    to break because one measurement system is mid-write or unavailable."""
    try:
        return fn(*a, **kw), None
    except Exception as exc:                       # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"


def _grade(sample: int | None, days: int | None) -> str:
    """How far this evidence is from supporting a real decision.

    DECISION_GRADE requires clearing the owner's bar on EITHER axis (>=500
    signals OR >=100 trading days), per their own wording. DIRECTIONAL means
    'interesting, look at it, do not act on it'."""
    if not sample:
        return "NO_DATA"
    if sample < 30:
        return "BUILDING"
    if sample >= MIN_SAMPLE_DECISION_GRADE or (days or 0) >= MIN_DAYS_DECISION_GRADE:
        return "DECISION_GRADE"
    return "DIRECTIONAL"


def _radar() -> dict[str, Any]:
    from . import opportunity_metrics as om
    rep, err = _safe(om.report)
    if rep is None:
        return {"id": "premium_radar", "available": False, "error": err}
    sample = rep.get("sample") or 0
    runners = rep.get("runners_total") or 0
    return {
        "id": "premium_radar",
        "name": "Premium Radar (detection black box)",
        "question": "Of option-premium moves that actually ran, how many did we "
                    "alert on EARLY rather than late or not at all?",
        "available": True,
        "native_metrics": {
            "capture_rate_pct": rep.get("capture_rate"),
            "runners_total": runners,
            "detected_early": rep.get("detected_early"),
            "detected_late": rep.get("detected_late"),
            "missed_completely": rep.get("missed_completely"),
            "alerts_total": rep.get("alerts_total"),
            "false_alerts": rep.get("false_alerts"),
            "alert_accuracy_pct": rep.get("alert_accuracy"),
            "recovered_pct": rep.get("recovered_pct"),
        },
        "sample": sample,
        "days": None,                     # report() is IST-day scoped, not cumulative
        "status": rep.get("measurement_health", {}).get("status"),
        "edge_expressible": True,
        "edge_basis": ("potential vs captured premium POINTS per episode "
                       "(recovered_pct). Real units, but it measures what the "
                       "ALERT could have captured — not a gated, executed trade."),
        "root_causes": rep.get("root_causes"),
        "grade": _grade(sample, None),
        "blockers_to_decision_grade": [
            "recovered_pct assumes entry AT the alert and exit AT the peak — "
            "neither is an executable rule, so it is an upper bound, not a P&L.",
            "No slippage, no fill assumption, no position sizing.",
        ],
    }


def _shadow_calibration() -> dict[str, Any]:
    from . import shadow_calibration as sc
    rep, err = _safe(sc.report)
    if rep is None:
        return {"id": "shadow_calibration", "available": False, "error": err}
    sample = rep.get("sample_blocked") or 0
    days = rep.get("days_covered") or 0
    return {
        "id": "shadow_calibration",
        "name": "Shadow Calibration (blocked-cycle confidence honesty)",
        "question": "While the gate was shut, was the engine's stated confidence "
                    "actually matched by what the market then did?",
        "available": True,
        "native_metrics": {
            "shadow_calibration_score": rep.get("shadow_calibration_score"),
            "error": rep.get("error"),
            "blocked_win_rate_pct": rep.get("blocked_win_rate"),
            "buckets": rep.get("buckets"),
        },
        "sample": sample,
        "days": days,
        "status": rep.get("status"),
        "edge_expressible": False,
        "edge_basis": ("NONE — calibration measures whether a probability is "
                       "HONEST, not whether trading it profits. A perfectly "
                       "calibrated engine can still lose money after costs, and "
                       "a poorly calibrated one can still win. Reporting an "
                       "'edge' here would be a category error."),
        "grade": _grade(sample, days),
        "blockers_to_decision_grade": [
            "Uses synthetic ATR levels (entry=spot, stop 1.2xATR, T1 1.5xATR) "
            "because a blocked cycle has no real planned entry.",
            "45-minute settle window biases toward faster theses.",
            f"Needs >=3 samples in a confidence bucket (currently: "
            f"{rep.get('progress') or 'measured'}).",
        ],
    }


def _verdicts() -> dict[str, Any]:
    from . import verdicts
    rep, err = _safe(verdicts.report)
    if rep is None:
        return {"id": "gate_verdicts", "available": False, "error": err}
    total = rep.get("total") or {}
    settled = total.get("settled") or 0
    rows = rep.get("rows") or []
    measured = [r for r in rows if r.get("status") == "MEASURED"]
    return {
        "id": "gate_verdicts",
        "name": "Gate Verdicts (per-blocker shadow outcomes)",
        "question": "For each rule that BLOCKED a trade — did blocking save "
                    "capital, or did it cost a winner?",
        "available": True,
        "native_metrics": {
            "settled_verdicts": settled,
            "open_shadows": total.get("open_shadows"),
            "modules_tracked": len(rows),
            "modules_measured": len(measured),
            "per_blocker": [
                {"module": r.get("module"), "blocked": r.get("blocked"),
                 "saved_pct": r.get("saved_pct"), "missed_pct": r.get("missed_pct"),
                 "missed_ci95_eff": r.get("missed_ci95_eff"),
                 "effective_samples": r.get("effective_samples"),
                 "status": r.get("status")}
                for r in rows[:10]
            ],
        },
        "sample": settled,
        "days": None,
        "status": "MEASURED" if measured else "LEARNING",
        "edge_expressible": True,
        "edge_basis": ("MISSED_WINNER vs CAPITAL_SAVED in index POINTS at the "
                       "gate's own planned levels. This is the closest thing to "
                       "a real P&L in the system — but it scores the GATE, not "
                       "a strategy: it answers 'was this veto worth it', not "
                       "'does this setup make money'."),
        "grade": _grade(settled, None),
        "blockers_to_decision_grade": [
            "Shadow trades are autocorrelated (one persisting setup spawns many); "
            "verdicts.py already discounts this via effective_samples — read the "
            "CI at the effective count, not the raw one.",
            "No costs/slippage modelled.",
        ],
    }


def _orfe(symbol: str = "NIFTY") -> dict[str, Any]:
    from . import orfe_research as orfe
    rep, err = _safe(orfe.level_stats, symbol)
    if rep is None:
        return {"id": "orfe", "available": False, "error": err}
    rows = rep.get("total_rows") or 0
    days = rep.get("days_with_a_setup") or 0
    levels = rep.get("levels") or []
    decided = [l for l in levels if (l.get("sample") or 0) >= 3]
    best = max(decided, key=lambda l: l.get("win_rate") or 0, default=None)
    return {
        "id": "orfe",
        "name": f"ORFE — Opening Range + Fibonacci ({symbol}, research)",
        "question": "After a 09:15-09:30 opening-range breakout, does entering on "
                    "a Fibonacci retracement have edge — and which level is best?",
        "available": True,
        "native_metrics": {
            "levels": levels,
            "by_regime": rep.get("by_regime"),
            "best_level_by_win_rate": ({"fib_level": best.get("fib_level"),
                                        "win_rate": best.get("win_rate"),
                                        "sample": best.get("sample")} if best else None),
            "days_with_a_setup": days,
        },
        "sample": rows,
        "days": days,
        "status": "MEASURED" if decided else "BUILDING",
        "edge_expressible": True,
        "edge_basis": ("Full entry/stop/T1/T2 in index POINTS with first-touch "
                       "resolution — the only source here that expresses a "
                       "complete, rule-defined trade. Index points only: Dhan "
                       "serves no historical option chain, so this is NOT option "
                       "premium P&L."),
        "grade": _grade(rows, days),
        "blockers_to_decision_grade": [
            "Underlying index points only — says nothing about option premium, "
            "theta, or IV, which is what is actually traded.",
            "No costs, slippage or fill assumptions.",
            f"Owner's own bar is 100 trading days / 500 signals; currently "
            f"{days} days with a setup, {rows} rows.",
            "RESEARCH ONLY — deliberately wired to no live path.",
        ],
    }


def report(symbol: str = "NIFTY") -> dict[str, Any]:
    """One evidence view across every measurement system. Pure read."""
    sources = [_radar(), _shadow_calibration(), _verdicts(), _orfe(symbol)]

    edge_capable = [s for s in sources
                    if s.get("available") and s.get("edge_expressible")]
    decision_grade = [s for s in sources if s.get("grade") == "DECISION_GRADE"]

    return {
        "sources": sources,
        "summary": {
            "total_sources": len(sources),
            "available": sum(1 for s in sources if s.get("available")),
            "can_express_edge": [s["id"] for s in edge_capable],
            "cannot_express_edge": [s["id"] for s in sources
                                    if s.get("available") and not s.get("edge_expressible")],
            "decision_grade": [s["id"] for s in decision_grade],
        },
        "verdict": (
            "No source is decision-grade yet."
            if not decision_grade else
            f"Decision-grade evidence exists in: {', '.join(s['id'] for s in decision_grade)}."
        ),
        "why_no_single_score": (
            "These sources answer different questions in different units — "
            "detection rate, probability honesty, per-rule veto value, and "
            "setup P&L in index points. Combining them into one ranked 'edge "
            "score' would invent a number that corresponds to nothing "
            "measurable. Each is therefore reported in its own units, and "
            "edge_expressible states plainly which can speak to profit at all."
        ),
        "thresholds": {
            "MIN_SAMPLE_DECISION_GRADE": MIN_SAMPLE_DECISION_GRADE,
            "MIN_DAYS_DECISION_GRADE": MIN_DAYS_DECISION_GRADE,
            "note": "Declared, not fitted. Tune from evidence, never silently.",
        },
        "note": ("READ-ONLY aggregator. Calls each system's own report()/stats "
                 "and reframes the output; changes no threshold, no gate, no "
                 "weight, and imports nothing that can block or permit a trade."),
        "as_of": int(time.time()),
    }
