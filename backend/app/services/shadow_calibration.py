"""SHADOW CALIBRATION — research-only calibration over BLOCKED cycles.

Owner-approved 2026-08-07, after the calibration deadlock was PROVEN (not
assumed) by tracing these five lines:

  1. kill_switch.py:22        MIN_CALIBRATION = 55
  2. (live)                   calibration_score = 54  -> kill switch ACTIVE
  3. confluence.py:367-369    active kill switch appends a veto
  4. confluence.py:495-497    ANY veto  ->  signal = "NO TRADE"
  5. memory.py:101            track_signal() early-returns on "NO TRADE",
                              so nothing enters _tracked/_outcomes

  -> analytics._calibration() reads buckets built from _outcomes, gets no new
     data, and the score can never move.  Back to step 2.  CLOSED LOOP.

Evidence for the loop being real and not theoretical: across 4,525 black-box
decision snapshots, 4,513 (99.7%) name "Calibration 54" as a kill-switch
reason, and of 686 genuine +30% premium runners the decision engine said
ENTER exactly 0 times while the kill switch was ACTIVE for 685 of them.

WHAT THIS MODULE DOES. audit.py already opens a HYPOTHETICAL forward-tracked
sample on every blocked cycle and settles it to a real win/loss against live
price. The only thing it never recorded was the confidence the engine
predicted at that moment — added now as `signal_confidence`. This module
pairs the two and computes a calibration score over blocked cycles, using
the IDENTICAL formula as the real one (analytics._calibration): buckets
60-70/70-80/80-90/90-100, midpoints 65/75/85/95, minimum 3 per bucket,
score = 100 - mean|midpoint - win_rate|. Same maths, different population,
so the two numbers are directly comparable.

WHAT THIS MODULE MUST NEVER DO — and structurally cannot:
  * It does not import kill_switch, confluence, execution_gate or decision*.
  * Nothing here is read by any gate, veto, threshold, weight or score.
  * It cannot unlock trading. Only a human changing MIN_CALIBRATION could,
    and this module never writes that value anywhere.
  * The real calibration score, its formula, and MIN_CALIBRATION=55 are all
    untouched — the owner's standing "Calibration 54 lock, தொடாதே" holds.

HONEST LIMITATIONS (stated, not hidden — these are why it is labelled
RESEARCH and not a drop-in replacement):
  * A blocked cycle has no real planned entry/stop/target, so audit.py uses
    SYNTHETIC ATR levels (entry=spot, stop=1.2*ATR, T1=1.5*ATR). This
    therefore measures "was the directional confidence honest, on standard
    ATR targets" — NOT "would the engine's own planned trade have won".
  * audit.py's 45-minute settle window means a slower thesis settles NEUTRAL
    against it; that is a real bias toward faster setups.
  * audit.py de-duplicates samples (same action within 0.2 ATR), so this is
    a sample of cycles, not every cycle.
  * Accumulation starts from the deploy of this module. Historical blocked
    cycles carry no signal_confidence and are unrecoverable — they are
    skipped, never back-filled with a guess.
"""
from __future__ import annotations

import json
import pathlib
import time
from typing import Any

from ..core.clock import IST, today_str

# Mirrors analytics._calibration() exactly — same buckets, same midpoints,
# same minimum sample. Any divergence here would make the two scores
# incomparable, which would defeat the entire purpose of this module.
BUCKET_MIDS = {"60-70": 65, "70-80": 75, "80-90": 85, "90-100": 95}
MIN_PER_BUCKET = 3
MIN_CONFIDENCE = 60.0     # below this the real calibration does not bucket either

_DATA_DIR = pathlib.Path(__file__).resolve().parents[3] / "data" / "shadow_calibration"
_seen_ts: set[float] = set()      # dedupe against audit._history re-reads
_harvested = 0                    # counter for observability


def _path() -> pathlib.Path:
    return _DATA_DIR / f"{today_str()}.jsonl"


def _bucket_of(conf: float) -> str | None:
    if 60 <= conf < 70:
        return "60-70"
    if 70 <= conf < 80:
        return "70-80"
    if 80 <= conf < 90:
        return "80-90"
    if conf >= 90:
        return "90-100"
    return None


def harvest() -> int:
    """Append any NEWLY settled audit records to today's durable log.

    Called once per AI cycle. audit._history is an in-memory deque(maxlen=400)
    with no persistence, and this backend restarts ~1-3x/day (watchdog), so
    without this the shadow sample would reset constantly and never reach a
    usable size. Returns how many new records were written this call.

    Never raises: a research module must not be able to break the AI cycle.
    """
    global _harvested
    try:
        from . import audit
        new: list[dict[str, Any]] = []
        for r in list(audit._history):
            ts = r.get("ts")
            if ts is None or ts in _seen_ts:
                continue
            _seen_ts.add(ts)
            conf = float(r.get("signal_confidence") or 0)
            if conf <= 0:
                continue        # pre-deploy record, no confidence — skipped, never guessed
            new.append({
                "ts": ts,
                "confidence": conf,
                "win": int(r.get("win") or 0),
                "hypothetical": bool(r.get("hypothetical")),
                "action": r.get("action"),
                "direction": r.get("direction"),
                "regime": r.get("regime"),
                "session": r.get("session"),
                "reached": r.get("reached"),
                "sl_hit": bool(r.get("sl_hit")),
            })
        if not new:
            return 0
        _DATA_DIR.mkdir(parents=True, exist_ok=True)
        with _path().open("a") as f:
            for r in new:
                f.write(json.dumps(r) + "\n")
        _harvested += len(new)
        return len(new)
    except Exception:
        return 0


def _read_all() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    try:
        if not _DATA_DIR.exists():
            return rows
        for p in sorted(_DATA_DIR.glob("*.jsonl")):
            for ln in p.read_text().splitlines():
                if ln.strip():
                    try:
                        rows.append(json.loads(ln))
                    except Exception:
                        continue
    except Exception:
        pass
    return rows


def report() -> dict[str, Any]:
    """The SHADOW calibration scorecard. Pure read over the durable log —
    computes nothing that any gate can see."""
    rows = _read_all()
    blocked = [r for r in rows if r.get("hypothetical")]

    def _score(sample: list[dict[str, Any]]) -> dict[str, Any]:
        buckets: dict[str, list[int]] = {k: [] for k in BUCKET_MIDS}
        for r in sample:
            b = _bucket_of(float(r.get("confidence") or 0))
            if b:
                buckets[b].append(int(r.get("win") or 0))
        rated = {
            k: {"n": len(v), "win_rate": round(100 * sum(v) / len(v), 1)}
            for k, v in buckets.items() if v
        }
        qualifying = {k: v for k, v in rated.items() if v["n"] >= MIN_PER_BUCKET}
        if not qualifying:
            need = MIN_PER_BUCKET
            return {
                "shadow_calibration_score": None, "error": None,
                "buckets": rated, "buckets_measured": 0,
                "status": "BUILDING",
                # Deliberately NOT called "note": the outer return below adds its
                # own "note" (the research disclaimer) and would silently
                # overwrite this one, hiding the only field that tells the
                # reader how far off a usable sample actually is.
                "progress": f"Need >={need} settled samples in at least one "
                            f"confidence bucket. Have: "
                            + (", ".join(f"{k}:{v['n']}" for k, v in rated.items()) or "none"),
            }
        errs = {k: abs(BUCKET_MIDS[k] - v["win_rate"]) for k, v in qualifying.items()}
        err = sum(errs.values()) / len(errs)
        contributors = sorted(
            ({"bucket": k, "midpoint": BUCKET_MIDS[k], "win_rate": qualifying[k]["win_rate"],
              "n": qualifying[k]["n"], "abs_error": round(e, 1)}
             for k, e in errs.items()),
            key=lambda c: c["abs_error"], reverse=True)
        return {
            "shadow_calibration_score": round(max(0, 100 - err), 0),
            "error": round(err, 1),
            "buckets": rated,
            "buckets_measured": len(errs),
            "status": "MEASURED",
            "contributors": contributors,
        }

    result = _score(blocked)
    days = sorted({time.strftime("%Y-%m-%d", time.localtime(r["ts"]))
                   for r in blocked if r.get("ts")})
    wins = sum(int(r.get("win") or 0) for r in blocked)
    return {
        **result,
        "sample_total": len(rows),
        "sample_blocked": len(blocked),
        "blocked_win_rate": round(100 * wins / len(blocked), 1) if blocked else None,
        "days_covered": len(days),
        "first_day": days[0] if days else None,
        "last_day": days[-1] if days else None,
        "harvested_this_run": _harvested,
        "label": "SHADOW / RESEARCH",
        "formula": ("Identical to the real calibration (analytics._calibration): "
                    "buckets 60-70/70-80/80-90/90-100, midpoints 65/75/85/95, "
                    ">=3 per bucket, score = 100 - mean|midpoint - win_rate|. "
                    "Same maths, different population."),
        "population": ("Cycles the gate BLOCKED, forward-tracked by audit.py to a "
                       "real win/loss against live price using SYNTHETIC ATR levels "
                       "(entry=spot, stop=1.2xATR, T1=1.5xATR) — a blocked cycle has "
                       "no real planned entry. Measures whether the directional "
                       "confidence was honest, NOT whether a planned trade would "
                       "have filled and won."),
        "note": ("RESEARCH ONLY. Does not modify the real calibration score, "
                 "MIN_CALIBRATION, the Kill Switch, any weight, threshold or gate — "
                 "and imports none of those modules. It cannot unlock trading; only "
                 "a human can. Accumulates while trading is blocked, which is "
                 "precisely the window the real calibration is structurally unable "
                 "to measure."),
        "as_of": int(time.time()),
    }
