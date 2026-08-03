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
import json
import logging
import os
import pathlib
import time
from typing import Any

from ..core.clock import IST

log = logging.getLogger(__name__)

TRIGGER_CONFIDENCE = 70.0   # owner-agreed trigger, 2026-07-22 trace
FLAT_TOLERANCE = 1.0        # calibration_score move < this = "stayed flat"

# ---------------------------------------------------------------------------
# Persistence (owner-approved 2026-08-03, "P3 — evidence persistence").
#
# Everything above was in-memory module globals reset by _roll_day(). Two ways
# the evidence was being lost, both silent:
#
#   1. Midnight. Yesterday's "was calibration flat all day?" answer simply
#      vanished, so a multi-day claim could never be supported by data.
#   2. **Restart.** The backend self-restarts ~1-3x/day, and each restart set
#      _first_cal back to None — so `flat` was really measuring "flat since
#      the last restart", not "flat all day", while reporting the latter.
#      Rehydrating below is therefore a correctness fix, not just storage:
#      without it the WATCH trigger silently understates the window it claims.
#
# Recording only. This still never reads or alters calibration scoring, the
# kill switch, or any threshold — it writes down what the untouched modules
# already publish, exactly as the module docstring promises. Same CAT_DATA_DIR
# convention as opportunity_metrics' black box.
# ---------------------------------------------------------------------------
_LOG_DIR = ((pathlib.Path(os.environ["CAT_DATA_DIR"]).parent / "calibration_watch")
            if os.getenv("CAT_DATA_DIR")
            else pathlib.Path(__file__).resolve().parents[3] / "data" / "calibration_watch")

# A sample is appended when the score actually moves, or every SAMPLE_EVERY_S
# regardless, so a flat day still proves it was *observed* flat rather than
# merely unobserved. MAX_SAMPLES caps a pathological day; the file stays tiny.
SAMPLE_MOVE = 0.5
SAMPLE_EVERY_S = 900        # 15 min
MAX_SAMPLES = 500

_day: str | None = None
_peak_confidence: float | None = None
_peak_ts: float | None = None
_first_cal: float | None = None
_last_cal: float | None = None
_samples: list[dict[str, Any]] = []   # [{ts, cal, conf}] — the P3 timeline
_restarts: int = 0                    # times a rehydrate found an existing day file
# True when a day's row was seeded by hand from a live reading rather than
# observed from the session's start. Carried through rehydrate and re-written
# on every persist ON PURPOSE: if this flag were dropped at the first write,
# a reconstructed row would silently start looking like a clean measurement.
_reconstructed: bool = False


def _today() -> str:
    return datetime.datetime.now(IST).strftime("%Y-%m-%d")


def _path(day: str) -> pathlib.Path:
    return _LOG_DIR / f"{day}.json"


def _roll_day() -> None:
    global _day, _peak_confidence, _peak_ts, _first_cal, _last_cal, _samples
    global _reconstructed
    d = _today()
    if d != _day:
        _day = d
        _reconstructed = False
        _peak_confidence = None
        _peak_ts = None
        _first_cal = None
        _last_cal = None
        _samples = []
        _rehydrate(d)


def _rehydrate(day: str) -> None:
    """Restore today's observation if this process restarted mid-session.

    Without this, a restart resets _first_cal and the day's `flat` verdict is
    computed only from the restart onward while still being reported as
    "all day". Never raises: a missing or corrupt file just means we start
    fresh, which is exactly the old behaviour.
    """
    global _peak_confidence, _peak_ts, _first_cal, _last_cal, _samples, _restarts
    global _reconstructed
    try:
        p = _path(day)
        if not p.exists():
            return
        prev = json.loads(p.read_text())
        if prev.get("day") != day:
            return                                  # stale/mismatched file
        _first_cal = prev.get("first_cal")
        _last_cal = prev.get("last_cal")
        _peak_confidence = prev.get("peak_confidence")
        _peak_ts = prev.get("peak_ts")
        _samples = list(prev.get("samples") or [])
        _restarts = int(prev.get("restarts") or 0) + 1
        _reconstructed = bool(prev.get("reconstructed"))
        log.info("calibration_watch: rehydrated %s (first_cal=%s, samples=%d, restart #%d)",
                 day, _first_cal, len(_samples), _restarts)
    except Exception:
        log.exception("calibration_watch rehydrate failed — starting fresh")


def _persist() -> None:
    """Write the day's observation. Never raises — observation must never be
    able to break the trading loop that feeds it."""
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        snap = report()
        snap.pop("note", None)                      # display text, not evidence
        snap.update({"first_cal": _first_cal, "last_cal": _last_cal,
                     "peak_ts": _peak_ts, "samples": _samples,
                     "restarts": _restarts, "reconstructed": _reconstructed,
                     "written": time.time()})
        tmp = _path(_day or _today()).with_suffix(".tmp")
        tmp.write_text(json.dumps(snap))
        tmp.replace(_path(_day or _today()))        # atomic — never a half file
    except Exception:
        log.exception("calibration_watch persist failed")


def history(days: int = 30) -> list[dict[str, Any]]:
    """Past daily observations, oldest→newest. Read-only; powers the P3
    timeline and is the evidence base for OBS-10 (does calibration ever
    recover?). Today's row is included and is live."""
    out: list[dict[str, Any]] = []
    try:
        _roll_day()
        for p in sorted(_LOG_DIR.glob("*.json"))[-days:]:
            try:
                out.append(json.loads(p.read_text()))
            except Exception:
                continue                            # skip one bad file, not all
    except Exception:
        log.exception("calibration_watch history failed")
    return out


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
        # P3 timeline: sample on a real move, or on a heartbeat so that a day
        # recorded as "flat" is provably *observed* flat rather than unobserved.
        if calibration_score is not None and len(_samples) < MAX_SAMPLES:
            last = _samples[-1] if _samples else None
            moved = last is None or abs(calibration_score - last["cal"]) >= SAMPLE_MOVE
            stale = last is not None and (now - last["ts"]) >= SAMPLE_EVERY_S
            if moved or stale:
                _samples.append({"ts": round(now, 1), "cal": calibration_score,
                                 "conf": signal_confidence})
        _persist()
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
        # P3 — observation provenance. `flat` is only meaningful alongside how
        # much of the day was actually watched: `samples` is how many times the
        # score was observed, `restarts` how many process restarts this day's
        # record survived (0 = one continuous observation).
        "flat": flat,
        "first_cal": _first_cal,
        "samples": len(_samples),
        "restarts": _restarts,
        "reconstructed": _reconstructed,
        "note": ("Observational only — calibration scoring is FROZEN this "
                 "session (owner, 2026-07-23). Trigger (2026-07-22 trace): peak "
                 f"confidence >={TRIGGER_CONFIDENCE:.0f} while calibration stays "
                 "flat all day is evidence of a real jam, not a correctly-"
                 "conservative range-bound day. A human decides whether to "
                 "revisit calibration as a FIX — this module never alters a "
                 "threshold itself."),
    }
