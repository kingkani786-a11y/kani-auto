"""Phase 21 — Evolution Center.

Self-analysis layer: aggregates the measurement the platform already produces
(outcomes, calibration, Brier, engine reliability, DNA, kill switch) into a
daily/weekly/monthly evolution report with a system grade and a ranked,
data-derived upgrade list. Measurement only — it never changes trading logic;
it tells you what to change. Probabilities, not certainty.
"""
from __future__ import annotations

import time
from typing import Any

from . import analytics, memory
from ..core.state import state

# Phase 23 — last nightly audit kept in memory so Evolution Center / Chief
# Strategist / AI Brain can show it even before the next broker connect.
_last_nightly: dict[str, Any] = {}


def _window_seconds(period: str) -> float:
    return {"daily": 86400, "weekly": 7 * 86400, "monthly": 30 * 86400}.get(period, 7 * 86400)


def _by_day(outcomes: list[dict]) -> dict[str, dict]:
    days: dict[str, list[dict]] = {}
    for o in outcomes:
        ts = o.get("closed")
        if not ts:
            continue
        d = time.strftime("%Y-%m-%d", time.localtime(ts))
        days.setdefault(d, []).append(o)
    return {d: {"n": len(v), "pnl": round(sum(x.get("pnl", 0) for x in v), 1),
                "win_rate": round(sum(x["win"] for x in v) / len(v) * 100, 0)}
            for d, v in days.items()}


def _engine_analysis() -> list[dict]:
    rel = memory.engine_reliability()
    out = []
    for e, v in rel.items():
        n, r = v["n"], v["reliability"]
        if n < 10:
            status, rec = "MEDIUM", "Building — keep sampling"
        elif r >= 60:
            status, rec = "HIGH", f"Increase weight → {v['weight']}×"
        elif r >= 50:
            status, rec = "MEDIUM", "Keep at 1.0×"
        elif r >= 40:
            status, rec = "LOW", f"Reduce weight → {v['weight']}×"
        else:
            status, rec = "DISABLE", "Reliability < 40% on a mature sample — consider disabling"
        out.append({"engine": e, "reliability": r, "trust": v["trust"],
                    "samples": n, "weight": v["weight"],
                    "status": status, "recommendation": rec})
    out.sort(key=lambda x: (x["samples"] >= 10, x["reliability"]), reverse=True)
    return out


def _brain_analysis(perf: dict) -> dict:
    val = perf.get("validation", {})
    acc = val.get("validation_accuracy")
    avg_conf = (perf.get("month", {}) or {}).get("avg_confidence")
    verdict = "Calibrated"
    gap = None
    if acc is not None and avg_conf is not None:
        gap = round(avg_conf - acc, 1)
        if gap >= 8:
            verdict = "Overconfident — confidence runs ahead of results"
        elif gap <= -8:
            verdict = "Underconfident — results beat stated confidence"
    worst_regime = (perf.get("learning", {}).get("by_market_condition", {}) or {}).get("worst")
    return {"verdict": verdict, "avg_confidence": avg_conf, "actual_win_rate": acc,
            "confidence_gap": gap,
            "loss_regime": (worst_regime or {}).get("name"),
            "loss_regime_win_rate": (worst_regime or {}).get("win_rate")}


def _dna_analysis() -> dict:
    dna = state.market_dna or {}
    if not dna.get("ready"):
        return {"ready": False, "note": dna.get("note", "Insufficient DNA — building toward ≥10 matches")}
    days = dna.get("similar_days", [])
    matches = [d["match"] for d in days if d.get("match") is not None]
    return {
        "ready": True,
        "strongest_match": max(matches) if matches else None,
        "weakest_match": min(matches) if matches else None,
        "avg_match_score": dna.get("match_score"),
        "historical_win_rate": dna.get("historical_win_rate"),
        "verdict": dna.get("verdict"),
        # DNA prediction accuracy needs realised follow-through tracking (Phase 24);
        # surfaced honestly until then.
        "prediction_accuracy": None,
        "prediction_accuracy_note": "Tracked once DNA predictions are forward-validated (Phase 24)",
    }


def _calibration_analysis(perf: dict) -> dict:
    cal = perf.get("calibration", {}) or {}
    brier = cal.get("brier", {}) or {}
    score = cal.get("calibration_score")
    grade = ("A" if (score or 0) >= 85 else "B" if (score or 0) >= 75
             else "C" if (score or 0) >= 60 else "D" if score is not None else "BUILDING")
    return {"calibration_score": score, "error_pct": cal.get("error"),
            "grade": grade, "brier": brier.get("brier"), "brier_grade": brier.get("grade"),
            "actual_win_rate": (perf.get("validation", {}) or {}).get("validation_accuracy")}


def _recommendations(perf: dict, engines: list[dict], cal: dict, brain: dict,
                     dna: dict) -> list[dict]:
    """Top-10 data-derived improvements, ranked by impact. Each: priority,
    title, expected_gain, difficulty, impact."""
    recs: list[dict] = []

    # 1) disable / down-weight failing engines
    for e in engines:
        if e["status"] == "DISABLE":
            recs.append({"title": f"Disable or down-weight '{e['engine']}' "
                                  f"({e['reliability']}% over {e['samples']} samples)",
                         "expected_gain": "Med-High", "difficulty": "Low", "impact": "Accuracy"})
        elif e["status"] == "HIGH":
            recs.append({"title": f"Up-weight '{e['engine']}' to {e['weight']}× — top performer",
                         "expected_gain": "Medium", "difficulty": "Low", "impact": "Accuracy"})

    # 2) calibration
    if cal.get("grade") in ("C", "D"):
        recs.append({"title": f"Recalibrate confidence (calibration grade {cal['grade']}, "
                              f"error {cal.get('error_pct')} pts)",
                     "expected_gain": "High", "difficulty": "Medium", "impact": "Calibration"})
    if cal.get("brier") is not None and cal["brier"] > 0.25:
        recs.append({"title": f"Improve forecast quality (Brier {cal['brier']} > 0.25 no-skill)",
                     "expected_gain": "High", "difficulty": "Medium", "impact": "Calibration"})

    # 3) brain over/underconfidence
    if "Overconfident" in (brain.get("verdict") or ""):
        recs.append({"title": "Trim confidence in confluence gating — system is overconfident",
                     "expected_gain": "High", "difficulty": "Medium", "impact": "Risk"})
    elif "Underconfident" in (brain.get("verdict") or ""):
        recs.append({"title": "Raise confidence on confirmed setups — system is underconfident",
                     "expected_gain": "Medium", "difficulty": "Medium", "impact": "Profit"})

    # 4) worst regime / session
    if brain.get("loss_regime"):
        recs.append({"title": f"Add a guard for '{brain['loss_regime']}' regime "
                              f"({brain.get('loss_regime_win_rate')}% win rate)",
                     "expected_gain": "Med-High", "difficulty": "Medium", "impact": "Risk"})
    worst_sess = (perf.get("learning", {}).get("by_session", {}) or {}).get("worst")
    if worst_sess:
        recs.append({"title": f"Tighten filters in '{worst_sess['name']}' session "
                              f"({worst_sess['win_rate']}%)",
                     "expected_gain": "Medium", "difficulty": "Low", "impact": "Risk"})

    # 5) DNA maturity
    if not dna.get("ready"):
        recs.append({"title": "Accumulate Market DNA — enable Supabase so history survives restarts",
                     "expected_gain": "High", "difficulty": "Low", "impact": "Learning"})

    # 6) sample size
    n = (perf.get("validation", {}) or {}).get("signals_tested", 0)
    if n < 100:
        recs.append({"title": f"Grow the validated sample ({n}/100) — metrics firm up past 100 trades",
                     "expected_gain": "Foundational", "difficulty": "Time", "impact": "Confidence"})

    # standing best-practices to round out the top-10
    standing = [
        {"title": "Forward-validate DNA predictions vs realised follow-through", "expected_gain": "High", "difficulty": "Medium", "impact": "Learning"},
        {"title": "Auto-tune engine weights nightly once samples are significant (Phase 23)", "expected_gain": "High", "difficulty": "Medium", "impact": "Accuracy"},
        {"title": "Track per-strike realised premium expansion for sharper strike selection", "expected_gain": "Medium", "difficulty": "Medium", "impact": "Profit"},
        {"title": "Tighten kill-switch recovery thresholds from observed drawdowns", "expected_gain": "Medium", "difficulty": "Low", "impact": "Risk"},
    ]
    for s in standing:
        if len(recs) >= 10:
            break
        recs.append(s)

    for i, r in enumerate(recs[:10], 1):
        r["priority"] = i
    return recs[:10]


def _weight_recommendations(engines: list[dict]) -> list[dict]:
    """Phase 23 Step 7 — current vs suggested weight per engine, with reason and
    confidence. The LIVE gate is equal-weight (1.0×); these are recommendations
    only and are NEVER auto-applied (require human approval)."""
    out = []
    for e in engines:
        n, r = e["samples"], e["reliability"]
        current = 1.0     # live confluence gate weights every engine equally
        if n < 10:
            suggested, reason = 1.0, "Insufficient sample — maintain until ≥10 trades"
        elif r > 75:
            suggested, reason = round(min(1.5, 1.0 + (r - 75) / 50), 2), "Reliability > 75% — increase weight"
        elif r >= 60:
            suggested, reason = 1.0, "Reliability 60–75% — maintain"
        elif r >= 40:
            suggested, reason = round(max(0.5, r / 60), 2), "Reliability 40–60% — reduce weight"
        else:
            suggested, reason = 0.0, "Reliability < 40% — disable candidate"
        conf = "HIGH" if n >= 30 else "MEDIUM" if n >= 10 else "LOW"
        out.append({"engine": e["engine"], "current_weight": current,
                    "suggested_weight": suggested, "reason": reason,
                    "confidence": conf, "samples": n,
                    "delta": round(suggested - current, 2)})
    return out


def _narrative(perf: dict, engines: list[dict], cal: dict, brain: dict,
               dna: dict) -> dict[str, list[str]]:
    """Phase 23 Step 8 — plain-English report buckets."""
    worked, failed, improve, disable, upgrade, monitor = [], [], [], [], [], []
    learn = perf.get("learning", {})
    best_setup = (learn.get("by_setup", {}) or {}).get("best")
    worst_setup = (learn.get("by_setup", {}) or {}).get("worst")
    if best_setup:
        worked.append(f"Best setup: {best_setup['name']} ({best_setup['win_rate']}% over {best_setup['n']})")
    best_sess = (learn.get("by_session", {}) or {}).get("best")
    if best_sess:
        worked.append(f"Best session: {best_sess['name']} ({best_sess['win_rate']}%)")
    for e in engines:
        if e["status"] == "HIGH":
            worked.append(f"Reliable engine: {e['engine']} ({e['reliability']}%)")
        elif e["status"] == "DISABLE":
            disable.append(f"{e['engine']} — {e['reliability']}% over {e['samples']} samples")
        elif e["status"] == "LOW":
            improve.append(f"Down-weight {e['engine']} ({e['reliability']}%)")
    if worst_setup:
        failed.append(f"Worst setup: {worst_setup['name']} ({worst_setup['win_rate']}%)")
    if brain.get("loss_regime"):
        failed.append(f"{str(brain['loss_regime']).replace('_',' ')} regime drove losses "
                      f"({brain.get('loss_regime_win_rate')}%)")
    if cal.get("grade") in ("C", "D"):
        improve.append(f"Confidence calibration (grade {cal['grade']}, error {cal.get('error_pct')} pts)")
    if "Overconfident" in (brain.get("verdict") or ""):
        improve.append("System is overconfident — trim stated confidence")
    if not dna.get("ready"):
        upgrade.append("Accumulate Market DNA (enable Supabase for permanence)")
    else:
        worked.append(f"DNA matching live — avg match {dna.get('avg_match_score')}%")
    ks = state.kill_switch or {}
    if ks.get("active"):
        monitor.append(f"Kill switch ACTIVE: {'; '.join(ks.get('reasons', []))}")
    monitor.append("Engine reliability vs sample growth")
    monitor.append("Calibration drift week-over-week")
    upgrade.append("Apply matured engine weights once statistically significant (human-approved)")
    return {"what_worked": worked or ["Building — not enough settled trades yet"],
            "what_failed": failed or ["No notable failures recorded"],
            "what_to_improve": improve or ["Grow the validated sample"],
            "what_to_disable": disable or ["None"],
            "what_to_upgrade": upgrade,
            "what_to_monitor": monitor}


def _system_grade(perf: dict, cal: dict) -> str:
    val = perf.get("validation", {}) or {}
    acc = val.get("validation_accuracy")
    n = val.get("signals_tested", 0)
    score = cal.get("calibration_score")
    if n < 20 or acc is None:
        return "BUILDING"
    pts = 0
    pts += 2 if acc >= 65 else 1 if acc >= 55 else 0
    pts += 2 if (score or 0) >= 80 else 1 if (score or 0) >= 65 else 0
    pts += 1 if n >= 100 else 0
    return {5: "A+", 4: "A", 3: "B", 2: "C"}.get(pts, "D")


def report(period: str = "weekly", persist: bool = False) -> dict[str, Any]:
    perf = analytics.performance()
    start = time.time() - _window_seconds(period)
    outcomes = [o for o in memory._outcomes if o.get("closed", 0) >= start]

    days = _by_day(outcomes)
    best_day = max(days, key=lambda d: days[d]["pnl"]) if days else None
    worst_day = min(days, key=lambda d: days[d]["pnl"]) if days else None
    by_session = (perf.get("learning", {}).get("by_session", {}) or {})

    wins = sum(o["win"] for o in outcomes)
    n = len(outcomes)
    rr = [o["r_multiple"] for o in outcomes if "r_multiple" in o]

    engines = _engine_analysis()
    # Phase 23 Step 2 — accuracy trend / performance delta vs the last nightly audit
    prev = {e["engine"]: e["reliability"] for e in (_last_nightly.get("engine_analysis") or [])}
    for e in engines:
        p = prev.get(e["engine"])
        e["performance_delta"] = (round(e["reliability"] - p, 1) if p is not None else None)
        e["accuracy_trend"] = ("UP" if e["performance_delta"] and e["performance_delta"] > 1
                               else "DOWN" if e["performance_delta"] and e["performance_delta"] < -1
                               else "FLAT" if e["performance_delta"] is not None else "NEW")
    cal = _calibration_analysis(perf)
    brain = _brain_analysis(perf)
    dna = _dna_analysis()
    grade = _system_grade(perf, cal)

    rep = {
        "period": period,
        "generated_at": time.time(),
        "overview": {
            "total_signals": (perf.get("validation", {}) or {}).get("signals_generated", 0),
            "settled": n,
            "win_rate": round(wins / n * 100, 1) if n else None,
            "loss_rate": round((n - wins) / n * 100, 1) if n else None,
            "avg_rr": round(sum(rr) / len(rr), 2) if rr else None,
            "best_day": ({"date": best_day, **days[best_day]} if best_day else None),
            "worst_day": ({"date": worst_day, **days[worst_day]} if worst_day else None),
            "best_session": by_session.get("best"),
            "worst_session": by_session.get("worst"),
        },
        "engine_analysis": engines,
        "calibration_analysis": cal,
        "brain_analysis": brain,
        "dna_analysis": dna,
        "kill_switch": state.kill_switch or {"active": False},
        "recommendations": _recommendations(perf, engines, cal, brain, dna),
        "weight_recommendations": _weight_recommendations(engines),
        "narrative": _narrative(perf, engines, cal, brain, dna),
        "system_grade": grade,
        "roadmap": roadmap(),
        "disclaimer": "Self-analysis from real outcomes — advisory, never auto-applied to the live gate. "
                      "Weight changes require human approval (Measure → Validate → Upgrade → Deploy).",
    }
    if persist:
        _persist(rep)
    return rep


# Phase 21/v6 — roadmap tracker (single source of truth for build progress)
_ROADMAP = [
    ("14", "Kill Switch", "COMPLETED"),
    ("16", "Calibration + Brier", "COMPLETED"),
    ("19", "Supabase Memory Engine", "COMPLETED"),
    ("20", "Market DNA", "COMPLETED"),
    ("21", "Evolution Center", "COMPLETED"),
    ("22", "Weight Approval Engine", "COMPLETED"),
    ("23", "Self-Tuning Nightly Audit", "COMPLETED"),
    ("25", "Chief Strategist", "COMPLETED"),
    ("26", "Premium Forecast Engine", "COMPLETED"),
    ("27", "Entry Zone Engine", "COMPLETED"),
    ("28", "Probability Ladder", "COMPLETED"),
    ("29", "Today + Tomorrow Simulator", "COMPLETED"),
    ("30", "Options Professor", "COMPLETED"),
    ("31", "Autonomous AI Research Lab", "COMPLETED"),
    ("24", "Outcome-Trained Model", "BLOCKED"),
]


def roadmap() -> dict[str, Any]:
    items = [{"phase": p, "name": n, "status": s} for p, n, s in _ROADMAP]
    done = sum(1 for _, _, s in _ROADMAP if s == "COMPLETED")
    total = len(_ROADMAP)
    pending = [i for i in items if i["status"] == "PENDING"]
    return {
        "items": items,
        "completed": done, "pending": len([i for i in items if i["status"] == "PENDING"]),
        "blocked": len([i for i in items if i["status"] == "BLOCKED"]),
        "completion_pct": round(done / total * 100, 0),
        "next_recommended": (pending[0]["name"] if pending else "All non-blocked phases complete"),
        "note": "Phase 24 blocked until 500+ settled signals; persistence needs Supabase creds.",
    }


def run_nightly() -> dict[str, Any]:
    """Phase 23 — the nightly self-tuning audit. Generates the daily report,
    archives it to Supabase, and caches it in memory. Recommendations only —
    NOTHING is auto-applied to the live trading gate."""
    global _last_nightly
    rep = report("daily", persist=True)
    rep["nightly"] = True
    # Phase 31 — autonomous research lab self-scan attached to the nightly run
    try:
        from . import research_lab
        rep["research"] = research_lab.report()
    except Exception:
        pass
    _last_nightly = rep
    return rep


def last_nightly() -> dict[str, Any]:
    """Most recent nightly audit (or a placeholder until one has run)."""
    if _last_nightly:
        return _last_nightly
    return {"nightly": False, "note": "No nightly audit yet — runs automatically at 23:59 IST, "
                                       "or trigger one from the Evolution Center.",
            "system_grade": "BUILDING"}


def _persist(rep: dict) -> None:
    """Phase 19/23 — archive the report to Supabase when configured."""
    from .journal import _sb
    if not _sb:
        return
    try:
        ov = rep["overview"]
        _sb.table("evolution_reports").insert({
            "period": rep["period"], "accuracy": ov.get("win_rate"),
            "calibration": rep["calibration_analysis"].get("calibration_score"),
            "brier": rep["calibration_analysis"].get("brier"),
            "best_engine": (rep["engine_analysis"][0]["engine"] if rep["engine_analysis"] else None),
            "worst_engine": (rep["engine_analysis"][-1]["engine"] if rep["engine_analysis"] else None),
            "report": rep,
        }).execute()
    except Exception:
        pass
