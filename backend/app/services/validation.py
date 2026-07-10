"""V27 §1 — AI Accuracy Report Card.

Consolidates everything the platform already MEASURES (win rate, entry accuracy,
MFE/MAE execution quality, premium/point capture, calibration, Brier, reliability)
into one daily report card. Derivation-only aggregation — no new data, no
fabrication. Metrics that need data not yet captured (entry delay, opportunity
miss) are honestly reported as "building" until live trades accumulate.
"""
from __future__ import annotations

from typing import Any

from . import analytics, audit
from ..core.state import state


def _grade(win: float | None, cal: float | None, n: int) -> str:
    if n < 20 or win is None:
        return "BUILDING"
    pts = 0
    pts += 2 if win >= 60 else 1 if win >= 52 else 0
    pts += 2 if (cal or 0) >= 80 else 1 if (cal or 0) >= 65 else 0
    pts += 1 if n >= 100 else 0
    return {5: "A+", 4: "A", 3: "B", 2: "C"}.get(pts, "D")


def daily_review() -> dict[str, Any]:
    """Market-closed Daily Review — keeps the dashboard alive after hours with a
    learning summary of the session: signals, win rate, best/worst, last strike.
    Derivation-only from stored outcomes; honest 'no trades yet' when empty."""
    perf = analytics.performance()
    today = perf.get("today", {}) or {}
    week = perf.get("week", {}) or {}
    eq = perf.get("execution_quality", {}) or {}
    dec = state.decision or {}
    card = (dec.get("execution_card") or {}).get("card") or {}
    strike = state.intelligence.get("strike") or {}

    settled = today.get("closed", 0) or 0
    return {
        "ready": True,
        "signals": today.get("generated", 0),
        "settled": settled,
        "wins": today.get("wins", 0),
        "losses": today.get("losses", 0),
        "win_rate": today.get("accuracy"),
        "net_points": today.get("net_points", 0),
        "avg_mfe_pts": eq.get("avg_mfe_pts"),
        "best": week.get("best"),
        "worst": week.get("worst"),
        "last_strike": (card.get("strike") or strike.get("strike")),
        "last_strike_type": (card.get("type") or strike.get("type")),
        # RC1.13 — vocabulary standardized to PAUSED, the same word AI
        # Self-Check and Feed Diagnostics use for this identical market-closed state
        "ai_status": "PAUSED — feeds healthy, scanner resumes automatically at market open",
        "note": ("Session review." if settled else
                 "No settled trades yet — review populates after live sessions."),
    }


def report_card() -> dict[str, Any]:
    perf = analytics.performance()
    aud = audit.report()
    val = perf.get("validation", {}) or {}
    eq = perf.get("execution_quality", {}) or {}
    cal = perf.get("calibration", {}) or {}
    brier = (cal.get("brier") or {})
    week = perf.get("week", {}) or {}

    n = val.get("signals_tested", 0)
    win = val.get("validation_accuracy")
    acc_known = win is not None

    return {
        "ready": True,
        "samples": n,
        "scorecard": {
            "win_rate": win,
            "entry_accuracy": (aud.get("entry") or {}).get("entry_accuracy"),
            "exit_quality": eq.get("exit_quality", "BUILDING"),
            "premium_capture_pct": eq.get("capture_efficiency_pct"),
            "point_capture_avg_pts": eq.get("avg_mfe_pts"),
            "avg_adverse_pts": eq.get("avg_mae_pts"),
            # RC1.16.10 fix #4: this is literally 100 − win_rate (loss rate of
            # TAKEN signals). The old name "false_signal_rate" collided with
            # signal_maturity's genuinely different predictive false-signal
            # probability. One meaning per name.
            "loss_rate": (round(100 - win, 1) if acc_known else None),
            "avg_entry_delay_sec": None,        # honest: needs ideal-vs-actual tracking
            "calibration_grade": cal.get("calibration_score"),
            "brier": brier.get("brier"),
        },
        "best_trade": week.get("best"),
        "worst_trade": week.get("worst"),
        "opportunity": {
            "taken": n,
            "seen": None,                       # honest: opportunity-miss needs live tracking
            "note": "Opportunity-miss + entry-delay analytics populate during live market hours.",
        },
        "overall_rating": _grade(win, cal.get("calibration_score"), n),
        "notes": [] if n >= 20 else
                 ["Report card is BUILDING — needs ≥20 settled live trades for graded metrics."],
        "disclaimer": "Measured from real settled outcomes only. No trading AI is ever 100% — "
                      "the goal is avoiding bad trades and positive long-run expectancy.",
    }
