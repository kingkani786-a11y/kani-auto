"""Opportunity measurement — the 'Measure' in Build → Verify → Measure → Improve.

Read-only instrumentation layered over the premium radar. It records, per
strike *episode*, the objective timeline of a move —

    base → first stir (+5%) → our IGNITE alert → runner (+30%) → peak

— and turns that into the KPIs the owner asked for, computed by the system so
they are honest and repeatable instead of eyeballed:

  • Opportunity Capture Rate   — early / late / missed  → %
  • Detection Delay            — alert_ts − move_start_ts (negative = pre-warning, the goal)
  • False-Positive Rate        — IGNITE alerts that never became a real move
  • Missed Money               — peak premium vs premium when we alerted

It NEVER decides or recommends a trade — pure measurement. IST-day scoped
(resets each session). Every threshold below is a DECLARED number, not a
calibrated one; tomorrow's evidence is what tunes them.
"""
from __future__ import annotations

import datetime
import time
from typing import Any

from ..core.clock import IST

# ── declared thresholds (tune from evidence, never silently) ────────────────
STIR_PCT = 5.0        # +5% from base = the move has "started" (move_start)
RUNNER_PCT = 30.0     # +30% from base = a real runner (owner's macro-phase)
EARLY_MAX_PCT = 15.0  # alerted while still < +15% = caught EARLY, else LATE
REAL_MOVE_PCT = 10.0  # an alert is FALSE if the strike never reaches +10%…
FALSE_WINDOW_S = 300  # …within 5 min of the alert
CLOSE_GAP_S = 120     # episode closes after it retraces + 2 min of quiet

_eps: dict[str, dict[str, Any]] = {}     # live episode per strike key
_closed: list[dict[str, Any]] = []       # completed episodes today
_day: str | None = None


def _today() -> str:
    return datetime.datetime.now(IST).strftime("%Y-%m-%d")


def _roll_day() -> None:
    global _day
    d = _today()
    if d != _day:
        _eps.clear()
        _closed.clear()
        _day = d


def _new_ep(strike: int, typ: str, premium: float, now: float) -> dict[str, Any]:
    return {"strike": strike, "type": typ, "base": premium, "base_ts": now,
            "peak": premium, "peak_ts": now,
            "move_start_ts": None, "move_start_prem": None,
            "alert_ts": None, "alert_prem": None, "alert_rise": None,
            "runner_ts": None, "runner_prem": None, "started": now}


def record(key: str, strike: int, typ: str, premium: float,
           rise_pct: float, coil_state: str, now: float | None = None) -> None:
    """Feed one radar tick. Called from premium_radar.scan (per option tick)."""
    if premium <= 0:
        return
    _roll_day()
    now = now or time.time()
    ep = _eps.get(key)
    if ep is None:
        ep = _eps[key] = _new_ep(strike, typ, premium, now)

    # while still quiet (no move yet), let the base track down to the true low
    if ep["move_start_ts"] is None and premium < ep["base"]:
        ep["base"], ep["base_ts"] = premium, now

    rise = (premium - ep["base"]) / ep["base"] * 100 if ep["base"] else 0.0
    if premium > ep["peak"]:
        ep["peak"], ep["peak_ts"] = premium, now
    if ep["move_start_ts"] is None and rise >= STIR_PCT:
        ep["move_start_ts"], ep["move_start_prem"] = now, premium
    if ep["alert_ts"] is None and coil_state == "IGNITING":
        ep["alert_ts"], ep["alert_prem"], ep["alert_rise"] = now, premium, rise
    if ep["runner_ts"] is None and rise >= RUNNER_PCT:
        ep["runner_ts"], ep["runner_prem"] = now, premium

    # close the episode once it has moved and then retraced to near the base
    moved = ep["peak"] > ep["base"] * (1 + STIR_PCT / 100)
    retraced = premium <= ep["base"] * 1.05
    if moved and retraced and now - ep["peak_ts"] > CLOSE_GAP_S:
        _closed.append(ep)
        _eps[key] = _new_ep(strike, typ, premium, now)


def _classify(ep: dict[str, Any]) -> dict[str, Any]:
    peak_rise = (ep["peak"] - ep["base"]) / ep["base"] * 100 if ep["base"] else 0.0
    is_runner = peak_rise >= RUNNER_PCT or ep["runner_ts"] is not None
    alerted = ep["alert_ts"] is not None
    # capture class (only meaningful for runners)
    if is_runner:
        if not alerted:
            cap = "MISSED"
        elif (ep["alert_rise"] or 0) < EARLY_MAX_PCT:
            cap = "EARLY"
        else:
            cap = "LATE"
    else:
        cap = None
    # was the alert a false positive? (fired but the move never got real)
    false_pos = alerted and peak_rise < REAL_MOVE_PCT
    # detection delay: alert vs the move starting (negative = warned BEFORE it moved)
    delay = None
    if alerted and ep["move_start_ts"] is not None:
        delay = round(ep["alert_ts"] - ep["move_start_ts"], 1)
    # money
    potential = round(ep["peak"] - ep["base"], 2)
    captured = round(ep["peak"] - ep["alert_prem"], 2) if alerted else 0.0
    lost = round(potential - captured, 2)
    return {"strike": ep["strike"], "type": ep["type"], "peak_rise": round(peak_rise, 1),
            "is_runner": is_runner, "alerted": alerted, "capture": cap,
            "false_pos": false_pos, "delay_s": delay,
            "potential": potential, "captured": captured, "lost": lost,
            "base": round(ep["base"], 2), "peak": round(ep["peak"], 2),
            "alert_prem": round(ep["alert_prem"], 2) if alerted else None}


def report() -> dict[str, Any]:
    """The live KPI scorecard — closed + still-open episodes that have moved."""
    _roll_day()
    now = time.time()
    eps = list(_closed) + [e for e in _eps.values()
                           if e["peak"] > e["base"] * (1 + STIR_PCT / 100)]
    rows = [_classify(e) for e in eps]

    runners = [r for r in rows if r["is_runner"]]
    early = [r for r in runners if r["capture"] == "EARLY"]
    late = [r for r in runners if r["capture"] == "LATE"]
    missed = [r for r in runners if r["capture"] == "MISSED"]
    alerts = [r for r in rows if r["alerted"]]
    false_alerts = [r for r in alerts if r["false_pos"]]
    delays = [r["delay_s"] for r in rows if r["delay_s"] is not None]

    capture_rate = round(len(early) / len(runners) * 100, 1) if runners else None
    accuracy = round((len(alerts) - len(false_alerts)) / len(alerts) * 100, 1) if alerts else None
    avg_delay = round(sum(delays) / len(delays), 1) if delays else None

    missed_money = sorted(runners, key=lambda r: r["lost"], reverse=True)[:5]

    return {
        "day": _day,
        "capture_rate": capture_rate,            # EARLY / all runners  (%)
        "runners_total": len(runners),
        "detected_early": len(early),
        "detected_late": len(late),
        "missed_completely": len(missed),
        "alerts_total": len(alerts),
        "false_alerts": len(false_alerts),
        "alert_accuracy": accuracy,              # %
        "avg_detection_delay_s": avg_delay,      # negative = pre-warning
        "missed_money": [
            {"strike": r["strike"], "type": r["type"], "potential": r["potential"],
             "captured": r["captured"], "lost": r["lost"]}
            for r in missed_money if r["potential"] > 0
        ],
        "sample": len(rows),
        "note": ("System-measured, not eyeballed. Thresholds are declared "
                 f"(stir +{STIR_PCT:.0f}%, runner +{RUNNER_PCT:.0f}%, early "
                 f"<+{EARLY_MAX_PCT:.0f}%, false if <+{REAL_MOVE_PCT:.0f}% in "
                 f"{FALSE_WINDOW_S // 60}m) — tune from evidence. Measurement "
                 "only; never a trade instruction."),
        "as_of": int(now),
    }
