"""Calibration Watch — Phase 1 item #4 (owner, 2026-07-23).

OBSERVATIONAL ONLY. This module does not read, call, or alter
analytics._calibration(), kill_switch.py's evaluate(), or any gate threshold —
calibration scoring logic is FROZEN this session per owner instruction. It only
records numbers those (untouched) modules already publish each cycle, for
display, exactly like opportunity_metrics' black box observes the radar
without ever feeding back into it.

Background (2026-07-22 trace, owner-verified): a "Calibration deadlock (54 all
day)" was initially mislabeled a FIX. Tracing track_signal (market_service.py)
showed it fires BEFORE the kill-switch downgrade but skips on "NO TRADE";
confluence emits NO TRADE whenever signal-confidence <70 — so on a genuinely
range-bound day the score never gets a signal that clears 70 to test itself
against, and a flat 54 all day is INDISTINGUISHABLE from "correctly
conservative" using one day's data alone. Reclassified FIX -> WATCH, with this
exact trigger pre-registered so the distinction becomes automatic instead of
requiring a fresh manual re-trace every time it recurs:

    If peak signal_confidence reaches >= TRIGGER_CONFIDENCE while
    calibration_score stays flat (first-of-day == last-of-day) — THAT is
    evidence of a real jam (the gate saw a confident signal and the score
    still didn't move), not a quiet range-bound day. Below the trigger, the
    WAIT gate is doing exactly what capital protection asks of it.

A human decides whether to act on the trigger; this module only surfaces it.
"""
from __future__ import annotations

import datetime
import time
from typing import Any

from ..core.clock import IST

TRIGGER_CONFIDENCE = 70.0   # owner-agreed trigger, 2026-07-22 trace
FLAT_TOLERANCE = 1.0        # calibration_score move < this = "stayed flat"

_day: str | None = None
_peak_confidence: float | None = None
_peak_ts: float | None = None
_first_cal: float | None = None
_last_cal: float | None = None


def _today() -> str:
    return datetime.datetime.now(IST).strftime("%Y-%m-%d")


def _roll_day() -> None:
    global _day, _peak_confidence, _peak_ts, _first_cal, _last_cal
    d = _today()
    if d != _day:
        _day = d
        _peak_confidence = None
        _peak_ts = None
        _first_cal = None
        _last_cal = None


def record(calibration_score: float | None, signal_confidence: float | None,
           now: float | None = None) -> None:
    """Append-only observation, called once per market_service cycle. Never
    raises, never gates, never mutates calibration/kill-switch state."""
    global _peak_confidence, _peak_ts, _first_cal, _last_cal
    try:
        _roll_day()
        now = now or time.time()
        if signal_confidence is not None:
            if _peak_confidence is None or signal_confidence > _peak_confidence:
                _peak_confidence = signal_confidence
                _peak_ts = now
        if calibration_score is not None:
            if _first_cal is None:
                _first_cal = calibration_score
            _last_cal = calibration_score
    except Exception:
        pass


def report() -> dict[str, Any]:
    _roll_day()
    difference = (round(_peak_confidence - _last_cal, 1)
                  if _peak_confidence is not None and _last_cal is not None else None)
    flat = (_first_cal is not None and _last_cal is not None
            and abs(_last_cal - _first_cal) < FLAT_TOLERANCE)
    triggered = bool(_peak_confidence is not None and _peak_confidence >= TRIGGER_CONFIDENCE and flat)
    return {
        "day": _day,
        "peak_confidence": _peak_confidence,
        "calibration_score": _last_cal,
        "difference": difference,
        "trigger_confidence": TRIGGER_CONFIDENCE,
        "status": "WATCH" if triggered else "OK",
        "note": ("Observational only — calibration scoring is FROZEN this "
                 "session (owner, 2026-07-23). Trigger (2026-07-22 trace): peak "
                 f"confidence >={TRIGGER_CONFIDENCE:.0f} while calibration stays "
                 "flat all day is evidence of a real jam, not a correctly-"
                 "conservative range-bound day. A human decides whether to "
                 "revisit calibration as a FIX — this module never alters a "
                 "threshold itself."),
    }
