"""Signal Performance Analytics (analytics layer only).

Pure aggregation over the outcomes the platform already records in
services.memory. Reads nothing from the broker and changes no trading logic.
In-memory by default (fills in as the system runs); persists across restarts
when Supabase is configured.
"""
from __future__ import annotations

import time
from typing import Any

from ..config import settings
from ..core.clock import midnight_today_ts
from . import memory


def _since(seconds: float) -> float:
    return time.time() - seconds


def _midnight_today() -> float:
    # RC1.16 — was time.localtime()/mktime() (host-OS-timezone-dependent);
    # now pinned to the app's single IST time source, same as everywhere else.
    return midnight_today_ts()


def _acc(outcomes: list[dict]) -> float | None:
    return round(sum(o["win"] for o in outcomes) / len(outcomes) * 100, 1) if outcomes else None


def _window(outcomes: list[dict], generated: list[dict], start: float) -> dict[str, Any]:
    out = [o for o in outcomes if o.get("closed", 0) >= start]
    gen = [g for g in generated if g.get("ts", 0) >= start]
    wins = [o for o in out if o["win"]]
    losses = [o for o in out if not o["win"]]
    rr = [o["r_multiple"] for o in out if "r_multiple" in o]
    confs = [g["confidence"] for g in gen if g.get("confidence")]
    return {
        "generated": len(gen),
        "closed": len(out),
        "wins": len(wins),
        "losses": len(losses),
        "accuracy": _acc(out),
        "avg_reward_risk": round(sum(rr) / len(rr), 2) if rr else None,
        "avg_confidence": round(sum(confs) / len(confs), 1) if confs else None,
        "net_points": round(sum(o.get("pnl", 0) for o in out), 1) if out else 0,
    }


def _best_worst(outcomes: list[dict]) -> dict[str, Any]:
    if not outcomes:
        return {"best": None, "worst": None}
    key = lambda o: o.get("r_multiple", o.get("pnl", 0))
    b, w = max(outcomes, key=key), min(outcomes, key=key)
    fmt = lambda o: {"signal": o.get("signal"), "regime": o.get("regime"),
                     "r_multiple": o.get("r_multiple"), "result": "WIN" if o["win"] else "LOSS"}
    return {"best": fmt(b), "worst": fmt(w)}


def _group_winrate(outcomes: list[dict], key: str, min_n: int = 3) -> dict[str, Any]:
    groups: dict[str, list[int]] = {}
    for o in outcomes:
        groups.setdefault(o.get(key) or "—", []).append(o["win"])
    rated = {k: {"n": len(v), "win_rate": round(sum(v) / len(v) * 100, 1)}
             for k, v in groups.items() if len(v) >= min_n}
    if not rated:
        return {"best": None, "worst": None, "all": {}}
    best = max(rated, key=lambda k: rated[k]["win_rate"])
    worst = min(rated, key=lambda k: rated[k]["win_rate"])
    return {"best": {"name": best, **rated[best]},
            "worst": {"name": worst, **rated[worst]}, "all": rated}


def _confidence_buckets(outcomes: list[dict]) -> dict[str, Any]:
    buckets = {"60-70": [], "70-80": [], "80-90": [], "90-100": []}
    for o in outcomes:
        c = o.get("confidence", 0)
        if 60 <= c < 70: buckets["60-70"].append(o["win"])
        elif 70 <= c < 80: buckets["70-80"].append(o["win"])
        elif 80 <= c < 90: buckets["80-90"].append(o["win"])
        elif c >= 90: buckets["90-100"].append(o["win"])
    rated = {k: {"n": len(v), "win_rate": round(sum(v) / len(v) * 100, 1)}
             for k, v in buckets.items() if v}
    best = max(rated, key=lambda k: rated[k]["win_rate"]) if rated else None
    return {"buckets": rated, "most_reliable": best}


def _avg_hold_min(outcomes: list[dict]) -> float | None:
    spans = [(o["closed"] - o["opened"]) / 60 for o in outcomes
             if o.get("closed") and o.get("opened")]
    return round(sum(spans) / len(spans), 0) if spans else None


def _validation_grade(acc: float | None, n: int) -> str:
    if n < 10 or acc is None:
        return "BUILDING"
    return "A" if acc >= 65 else "B" if acc >= 55 else "C" if acc >= 45 else "D"


def _brier(outcomes: list[dict]) -> dict[str, Any]:
    """Phase 16 — Brier score: mean((predicted_prob − actual_outcome)²) over
    every settled signal that carried a confidence. 0 = perfect, 1 = worst;
    0.25 is the no-skill baseline (always guessing 50%). Lower is better."""
    pairs = [(o.get("confidence", 0) / 100.0, float(o["win"]))
             for o in outcomes if o.get("confidence")]
    if len(pairs) < 5:
        return {"brier": None, "grade": "BUILDING", "n": len(pairs),
                "note": "Building — need ≥5 settled signals with confidence"}
    bs = sum((p - a) ** 2 for p, a in pairs) / len(pairs)
    # Grade vs the 0.25 no-skill baseline
    grade = ("EXCELLENT" if bs <= 0.12 else "GOOD" if bs <= 0.18
             else "FAIR" if bs <= 0.25 else "POOR")
    # skill score: how much better than always-50% (positive = skilled)
    skill = round((0.25 - bs) / 0.25 * 100, 0)
    return {"brier": round(bs, 4), "grade": grade, "skill_pct": skill, "n": len(pairs)}


def _calibration(buckets: dict[str, Any], outcomes: list[dict] | None = None) -> dict[str, Any]:
    """Module 4 — how well predicted confidence matches realised win rate.
    Calibration error = mean |bucket midpoint − win rate|; score = 100 − error.
    Phase 16 adds the Brier forecast-quality score over the raw outcomes."""
    mids = {"60-70": 65, "70-80": 75, "80-90": 85, "90-100": 95}
    qualifying = {k: v for k, v in buckets.items()
                  if k in mids and v.get("n", 0) >= 3 and v.get("win_rate") is not None}
    errs = [abs(mids[k] - v["win_rate"]) for k, v in qualifying.items()]
    brier = _brier(outcomes or [])
    # P2 (2026-08-03, "Calibration explanation, not a countdown") — root-cause
    # breakdown per bucket, largest error first: which confidence range is
    # dragging the score down, and by how much. Deliberately NOT a countdown
    # to the 55 threshold — that number doesn't exist (the NEXT settled
    # outcome can move the score either direction depending on its bucket and
    # win/loss, see kill_switch.py/analytics.py's own math) and showing one
    # would be a fabricated prediction, which this system never does.
    contributors = sorted(
        ({"bucket": k, "midpoint": mids[k], "win_rate": v["win_rate"], "n": v["n"],
          "abs_error": round(abs(mids[k] - v["win_rate"]), 1)}
         for k, v in qualifying.items()),
        key=lambda c: c["abs_error"], reverse=True)
    if not errs:
        return {"calibration_score": None, "error": None,
                "note": "Building — need ≥3 per bucket", "brier": brier,
                "contributors": []}
    err = sum(errs) / len(errs)
    return {"calibration_score": round(max(0, 100 - err), 0), "error": round(err, 1),
            "buckets_measured": len(errs), "brier": brier, "contributors": contributors}


def _execution_quality(outcomes: list[dict]) -> dict[str, Any]:
    """V25 §5/§10 — entry/exit quality from recorded MFE/MAE.
    Entry quality: how little adverse excursion before it worked (low MAE = good
    entry). Exit quality: how much of the favorable move was captured."""
    have = [o for o in outcomes if "mfe" in o]
    if len(have) < 5:
        return {"n": len(have), "note": "Building — need ≥5 settled with excursion data"}
    avg_mfe = round(sum(o.get("mfe", 0) for o in have) / len(have), 1)
    avg_mae = round(sum(o.get("mae", 0) for o in have) / len(have), 1)
    avg_missed = round(sum(o.get("missed_pts", 0) for o in have) / len(have), 1)
    captured = [o.get("pnl", 0) / o["mfe"] for o in have if o.get("mfe", 0) > 0]
    capture_pct = round(sum(captured) / len(captured) * 100, 0) if captured else None
    return {"n": len(have), "avg_mfe_pts": avg_mfe, "avg_mae_pts": avg_mae,
            "avg_missed_pts": avg_missed, "capture_efficiency_pct": capture_pct,
            "entry_quality": ("GOOD" if avg_mae > -8 else "FAIR" if avg_mae > -15 else "POOR"),
            "exit_quality": ("GOOD" if (capture_pct or 0) >= 60 else "FAIR" if (capture_pct or 0) >= 40 else "POOR")}


def performance() -> dict[str, Any]:
    outcomes = list(memory._outcomes)
    generated = list(memory._generated)
    now = time.time()

    month_outcomes = [o for o in outcomes if o.get("closed", 0) >= _since(30 * 86400)]
    total_r = sum(o.get("r_multiple", 0) for o in month_outcomes)
    gross_win = sum(o["pnl"] for o in month_outcomes if o.get("pnl", 0) > 0)
    gross_loss = abs(sum(o["pnl"] for o in month_outcomes if o.get("pnl", 0) < 0))

    n = len(outcomes)
    overall_acc = _acc(outcomes)
    # reliability: accuracy if the sample is meaningful, else "building"
    reliability = ("BUILDING" if n < 20 else "HIGH" if (overall_acc or 0) >= 65
                   else "MODERATE" if (overall_acc or 0) >= 55 else "LOW")

    return {
        "today": _window(outcomes, generated, _midnight_today()),
        "week": {**_window(outcomes, generated, _since(7 * 86400)),
                 **_best_worst([o for o in outcomes if o.get("closed", 0) >= _since(7 * 86400)])},
        "month": {
            **_window(outcomes, generated, _since(30 * 86400)),
            "total_r": round(total_r, 2),
            # ROI estimate: each trade risks risk_per_trade_pct of capital, so
            # portfolio ROI ≈ sum of R-multiples × risk-per-trade %.
            "roi_estimate_pct": round(total_r * settings.risk_per_trade_pct, 2),
            "profit_factor": round(gross_win / gross_loss, 2) if gross_loss else (99.0 if gross_win else 0.0),
            "risk_efficiency": round(total_r / len(month_outcomes), 2) if month_outcomes else None,
        },
        "learning": {
            "by_setup": _group_winrate(outcomes, "signal"),
            "by_market_condition": _group_winrate(outcomes, "regime"),
            "by_session": _group_winrate(outcomes, "session"),
            "by_confidence": _confidence_buckets(outcomes),
        },
        # Historical Accuracy Engine — last-30 / last-100 windows + holding time
        "historical": {
            "last_30": {"n": len(outcomes[-30:]), "accuracy": _acc(outcomes[-30:]),
                        "avg_hold_min": _avg_hold_min(outcomes[-30:])},
            "last_100": {"n": len(outcomes[-100:]), "accuracy": _acc(outcomes[-100:]),
                         "avg_hold_min": _avg_hold_min(outcomes[-100:])},
            "best_setup": _group_winrate(outcomes, "signal").get("best"),
            "worst_setup": _group_winrate(outcomes, "signal").get("worst"),
        },
        "calibration": _calibration(_confidence_buckets(outcomes).get("buckets", {}), outcomes),
        "engine_reliability": memory.engine_reliability(),
        # V25 §5 — live execution-quality validation (MFE/MAE/missed, points)
        "execution_quality": _execution_quality(outcomes),
        "validation": {
            "signals_generated": len(generated),
            "signals_tested": n,
            "wins": sum(o["win"] for o in outcomes),
            "losses": sum(1 for o in outcomes if not o["win"]),
            "validation_accuracy": overall_acc,
            "validation_grade": _validation_grade(overall_acc, n),
            "model_reliability": reliability,
            "live_success_rate": overall_acc,
            "open_positions": len(memory._tracked),
        },
        "ts": now,
    }
