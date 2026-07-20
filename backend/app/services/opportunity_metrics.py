"""Opportunity measurement + Black Box — the 'Measure' in Build→Verify→Measure→Improve.

Read-only instrumentation over the premium radar. For every strike *episode* it
records the objective timeline of a move —

    base → coil → +5% stir → IGNITE alert → +30% runner → peak → exhaust

— captures WHY it fired (velocity / volume / OI / acceleration) and the runner-
score trajectory, then turns it all into KPIs and a durable black-box log:

  • Opportunity Capture Rate   — early / late / missed  → %
  • Detection Delay            — alert_ts − move_start_ts (negative = pre-warning)
  • False-Positive Rate        — IGNITE alerts that never became a real move
  • Missed Money + Recovered % — captured vs the peak that was available
  • Prediction Stability       — smooth score climb (good) vs jumpy (unstable)

The black box (one JSON line per completed opportunity) is PERSISTED to disk so
it survives restarts — it's the learning data the AI reviews to answer "what
worked?". This module NEVER decides or recommends a trade — pure measurement.
IST-day scoped. Every threshold below is a DECLARED number, not a calibrated
one; evidence is what tunes them.
"""
from __future__ import annotations

import datetime
import json
import pathlib
import time
from typing import Any

from ..core.clock import IST

# ── declared thresholds (tune from evidence, never silently) ────────────────
STIR_PCT = 5.0        # +5% from base = the move has "started" (move_start)
RUNNER_PCT = 30.0     # +30% from base = a real runner (owner's macro-phase)
MIN_RUNNER_PTS = 5.0  # …AND ≥5 absolute pts — a +33% penny wiggle (₹0.6→₹0.8)
#                       is not a real opportunity; this stops penny options from
#                       inflating the runner count and printing absurd % (2422%)
EARLY_MAX_PCT = 15.0  # alerted while still < +15% = caught EARLY, else LATE
REAL_MOVE_PCT = 10.0  # an alert is FALSE if the strike never reaches +10%…
FALSE_WINDOW_S = 300  # …within 5 min of the alert
CLOSE_GAP_S = 300     # episode closes only after 5 min quiet past the peak
GIVEBACK_CLOSE = 0.70 # …AND only once it has given back ≥70% of the run. A
#                       normal pullback that holds is the SAME opportunity, not
#                       a new one — this stops one oscillating strike from being
#                       chopped into 20+ phantom episodes (measurement integrity)
EXHAUST_OFF_PEAK = 0.90  # premium ≤ 90% of peak after the peak = exhaustion
LAYER_CONFIRM = 55.0  # a decision-engine layer "confirms" at ≥55 (matches the
#                       dashboard checklist, e.g. "OI 39 < 55") — declared, tune from evidence

# ── Root-cause enumeration — WHY an opportunity was missed / faded / fired ──────
# Fixed tags so a whole day auto-classifies into a breakdown ("8 late-confirm, 6
# kill-switch, 4 OI-missing…"). Some tags need indicators not yet computed
# (RSI/EFI/CPR/Bollinger — IEIE Phase 1); those simply never fire until Phase 1
# fills the snapshot. The classifier only ever assigns a cause it has evidence for.
ROOT_CAUSE = (
    "NO_CONFIRMATION", "LATE_CONFIRMATION", "LOW_VOLUME", "LOW_OI",
    "VWAP_FAIL", "CPR_RESISTANCE", "CPR_SUPPORT", "RSI_OVERBOUGHT", "RSI_OVERSOLD",
    "ADX_WEAK", "ATR_LOW", "EFI_NEGATIVE", "PCR_CONFLICT", "IV_HIGH", "IV_CRUSH",
    "CHAIN_FAIL", "COIL_FAIL", "WAVE_FAIL", "EXECUTION_BLOCK", "KILL_SWITCH",
    "USER_SKIP", "SL_HIT", "TARGET_HIT",
    # miss taxonomy (owner, 2026-07-20): a miss during a data blackout is NOT a
    # detection failure — blame the right subsystem, never the AI by default
    "FEED_OUTAGE", "BROKER_COOLDOWN",
)

_LOG_DIR = pathlib.Path(__file__).resolve().parents[3] / "data" / "opportunity_log"

_eps: dict[str, dict[str, Any]] = {}     # live episode per strike key
_closed: list[dict[str, Any]] = []       # completed episodes today (in-memory)
_day: str | None = None
_seq = 0                                 # opportunity number, per day
_seen_keys: set[str] = set()             # keys tracked at least once today
_last_ckpt = 0.0                         # last open-episode checkpoint write
_restored = False                        # open episodes restored after (re)start?
CKPT_EVERY_S = 10                        # checkpoint cadence (measurement only)


def _today() -> str:
    return datetime.datetime.now(IST).strftime("%Y-%m-%d")


def _roll_day() -> None:
    global _day, _seq
    d = _today()
    if d != _day:
        _eps.clear(); _closed.clear(); _seen_keys.clear(); _seq = 0
        _day = d


def _ckpt_path() -> pathlib.Path:
    return _LOG_DIR / f"{_day}.open.json"


def _checkpoint_open(now: float) -> None:
    """P0 (owner, 2026-07-20): open episodes are the day's live measurement —
    the watchdog restarts the backend routinely (~20× since Jul-10), and every
    restart used to erase them (8 EARLY vanished from the 10:35 report). Write
    the open set durably every ~10s so a restart never loses measurement again.
    Never allowed to crash the scan path."""
    global _last_ckpt
    if now - _last_ckpt < CKPT_EVERY_S:
        return
    _last_ckpt = now
    try:
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        tmp = _ckpt_path().with_suffix(".tmp")
        tmp.write_text(json.dumps({"day": _day, "seq": _seq,
                                   "seen": sorted(_seen_keys), "eps": _eps}))
        tmp.replace(_ckpt_path())
    except Exception:
        pass


def _restore_open() -> None:
    """After a (re)start, resurrect the same day's open episodes so capture/
    early/delay KPIs and in-flight coil/ideal-entry tracking continue unbroken."""
    global _restored, _seq
    _restored = True
    try:
        p = _ckpt_path()
        if not p.exists():
            return
        snap = json.loads(p.read_text())
        if snap.get("day") != _day:
            return
        _eps.update(snap.get("eps") or {})
        _seen_keys.update(snap.get("seen") or [])
        _seq = max(_seq, int(snap.get("seq") or 0))
    except Exception:
        pass


def _hhmmss(ts: float | None) -> str | None:
    if not ts:
        return None
    return datetime.datetime.fromtimestamp(ts, IST).strftime("%H:%M:%S")


def _new_ep(strike: int, typ: str, premium: float, now: float) -> dict[str, Any]:
    return {"strike": strike, "type": typ, "base": premium, "base_ts": now,
            "peak": premium, "peak_ts": now,
            "coil_ts": None, "ignite_path": 0, "dte": _dte(),
            "session_type": _session_type(), "regime": _behavioural_regime(),
            "move_start_ts": None, "move_start_prem": None,
            "alert_ts": None, "alert_prem": None, "alert_rise": None,
            "runner_ts": None, "runner_prem": None, "exhaust_ts": None,
            # ideal-entry tracking (owner's missing KPI): after the alert, the
            # lowest premium BEFORE the final peak = the best entry that was
            # actually available. entry_edge = alert_prem − ideal_prem
            # (>0 ⇒ a retest gave a better price than the alert moment — the
            # evidence that decides the Best Entry Engine proposal #019).
            "ideal_prem": None, "ideal_ts": None,
            "_low_since_alert": None, "_low_ts": None,
            "reason": None, "traj": [], "last_traj_ts": 0.0, "started": now,
            # decision-engine + indicator context, snapshotted at the two moments
            # that answer "why": when the move was born (+5%) and when it became a
            # real runner (+30%). This is the JOIN the black box was missing.
            "snap_start": None, "snap_run": None}


def record(key: str, strike: int, typ: str, premium: float, rise_pct: float,
           coil_state: str, score: int = 0, velocity: float = 0.0,
           vol_delta: float = 0.0, oi_pct: float = 0.0, accel: float = 0.0,
           now: float | None = None, symbol: str = "", wave_n: int = 0,
           ignite_path: int = 0) -> None:
    """Feed one radar tick. Called from premium_radar.scan (per option tick)."""
    if premium <= 0:
        return
    _roll_day()
    now = now or time.time()
    if not _restored:
        _restore_open()          # resurrect same-day open episodes post-restart
    ep = _eps.get(key)
    if ep is None:
        ep = _eps[key] = _new_ep(strike, typ, premium, now)
        # cold start: the radar began tracking this strike >15 min after IST
        # open (symbol switch / ATM drift). Its "base" is whatever the premium
        # happened to be at that moment — a move already underway can't coil
        # and looks like a MISS. Flagged so the day report can separate
        # cold-start artifacts from genuine detection misses (2026-07-16:
        # all 12 misses were exactly this). Declared: 15 min.
        if key not in _seen_keys:
            _seen_keys.add(key)
            ist = datetime.datetime.now(IST)
            open_t = ist.replace(hour=9, minute=15, second=0, microsecond=0)
            ep["cold_start"] = bool(ist > open_t and
                                    (ist - open_t).total_seconds() > 15 * 60)
    if symbol:
        ep["symbol"] = symbol

    if ep["move_start_ts"] is None and premium < ep["base"]:
        ep["base"], ep["base_ts"] = premium, now  # track the true pre-move low
        # Re-anchor the peak with the base (2026-07-21). peak_rise is
        # (peak-base)/base, and NOTHING previously required the peak to occur
        # AFTER the base — so an episode that opened high and declined all
        # session logged as a big "missed runner" (peak first, base last).
        # Evidence 2026-07-20: 7 of 28 ">=30% movers" were falls, e.g. traj
        # [20,22,22,22,5] with t_peak at the episode's first tick; 9% of the
        # day's "lost" points were phantom. A high set before this new low
        # belongs to a pre-base period and is not a rise FROM it.
        # No-op for genuine runners (25->18->30 still yields 67% either way);
        # it only zeroes the falls.
        ep["peak"], ep["peak_ts"] = premium, now

    rise = (premium - ep["base"]) / ep["base"] * 100 if ep["base"] else 0.0
    if premium > ep["peak"]:
        ep["peak"], ep["peak_ts"] = premium, now
        # a new peak: the post-alert low that PRECEDED it is the ideal entry
        if ep["alert_ts"] is not None and ep["_low_since_alert"] is not None:
            ep["ideal_prem"], ep["ideal_ts"] = ep["_low_since_alert"], ep["_low_ts"]
    # running post-alert low (candidate ideal entry for the NEXT peak)
    if ep["alert_ts"] is not None and (
            ep["_low_since_alert"] is None or premium < ep["_low_since_alert"]):
        ep["_low_since_alert"], ep["_low_ts"] = premium, now
    if ep["coil_ts"] is None and coil_state == "COILED":
        ep["coil_ts"] = now
    if ep["move_start_ts"] is None and rise >= STIR_PCT:
        ep["move_start_ts"], ep["move_start_prem"] = now, premium
        ep["snap_start"] = _engine_snapshot()   # what did the engine see at birth?
    if ep["alert_ts"] is None and coil_state == "IGNITING":
        ep["alert_ts"], ep["alert_prem"], ep["alert_rise"] = now, premium, rise
        ep["ignite_path"] = ignite_path      # 1 = velocity spike · 2 = C6 coil breakout
        # wave_n = same-type strikes loaded at ignite — recorded so tomorrow's
        # data can answer whether chain-wave corroboration separates false
        # alerts from real earlies (2026-07-16 showed OI alone does NOT).
        ep["reason"] = {"velocity": round(velocity, 2), "volume": vol_delta > 0,
                        "oi_pct": round(oi_pct, 1), "accel": accel > 0,
                        "wave_n": int(wave_n)}
        # seed ideal-entry at the alert itself: straight-up runs get edge 0
        ep["ideal_prem"], ep["ideal_ts"] = premium, now
        ep["_low_since_alert"], ep["_low_ts"] = premium, now
    if ep["runner_ts"] is None and rise >= RUNNER_PCT and (premium - ep["base"]) >= MIN_RUNNER_PTS:
        ep["runner_ts"], ep["runner_prem"] = now, premium
        ep["snap_run"] = _engine_snapshot()     # what did the engine see when it ran?
    if ep["exhaust_ts"] is None and premium <= ep["peak"] * EXHAUST_OFF_PEAK \
            and ep["peak"] > ep["base"] * (1 + STIR_PCT / 100):
        ep["exhaust_ts"] = now

    # runner-score trajectory (for prediction-stability), throttled ~10s
    if now - ep["last_traj_ts"] >= 10:
        ep["traj"].append(int(score)); ep["last_traj_ts"] = now
        if len(ep["traj"]) > 60:
            ep["traj"] = ep["traj"][-60:]

    # close the episode only on TRUE exhaustion — the run gave back ≥70% of its
    # gain AND has been quiet 5 min past the peak. Pullbacks that hold stay the
    # same opportunity (one coherent run = one episode), so an intraday-
    # oscillating strike is no longer chopped into dozens of phantom episodes.
    moved = ep["peak"] > ep["base"] * (1 + STIR_PCT / 100)
    gain = ep["peak"] - ep["base"]
    exhausted = premium <= ep["base"] + (1 - GIVEBACK_CLOSE) * gain
    if moved and exhausted and now - ep["peak_ts"] > CLOSE_GAP_S:
        _close_episode(ep)
        _eps[key] = _new_ep(strike, typ, premium, now)

    _checkpoint_open(now)        # P0: durable open-episode snapshot (~10s)


def _dte() -> int | None:
    """Days to expiry at this instant, read defensively off the shared state.

    Recorded on EVERY black-box line from 2026-07-21 because expiry sessions are
    a different population, not a noisier version of the same one: theta crush
    inverts what a "COILED" reading (flat premium + rising volume/OI) means,
    RUNNER_PCT=30% is trivially cleared by a ₹5 option touching ₹6.50, and
    MIN_RUNNER_PTS=5 flips from a floor into a huge move when strikes trade
    ₹2-20. Without this tag, expiry episodes are indistinguishable from normal
    ones in the C6 sample and would silently decide the verdict."""
    try:
        from ..core.state import state
        v = ((state.intelligence or {}).get("layers") or {}).get("expiry") or {}
        d = v.get("days_to_expiry")
        return int(d) if d is not None else None
    except Exception:
        return None


# Manual session calendar. Budget Day / RBI Policy / special sessions CANNOT be
# derived — this system has no economic calendar — so they are declared by the
# owner in data/session_calendar.json ({"2026-02-01": "BUDGET"}) rather than
# guessed. Absent an entry the day is NORMAL, or EXPIRY when dte == 0.
_SESSION_CAL_PATH = _LOG_DIR.parent / "session_calendar.json"


def _session_type() -> str:
    """CALENDAR session type — a fact about the DATE. Deliberately separate
    from engines/regime.py's BEHAVIOURAL regime (TRENDING/VOLATILE/…), which
    is a fact about the TAPE. The owner wants to stratify C6 by both axes
    ("C6 on Expiry" vs "C6 on High Volatility"); collapsing them into one
    field called `market_regime` would make exactly that impossible."""
    try:
        if _SESSION_CAL_PATH.exists():
            declared = json.loads(_SESSION_CAL_PATH.read_text()).get(_day or _today())
            if declared:
                return str(declared).upper()
    except Exception:
        pass
    d = _dte()
    if d is None:
        # The expiry layer has not published yet (first ticks after open, or a
        # chain-less instrument). Returning NORMAL here would silently drop the
        # episode into the PRIMARY C6 sample while asserting something we cannot
        # actually know. UNKNOWN keeps it out until it can be resolved.
        return "UNKNOWN"
    return "EXPIRY" if d == 0 else "NORMAL"


def _behavioural_regime() -> str | None:
    """The existing regime layer (TRENDING/VOLATILE/HIGH_MOMENTUM/…), recorded
    so C6 can also be sliced by tape conditions. None when not yet published."""
    try:
        from ..core.state import state
        return ((state.intelligence or {}).get("layers") or {}).get("regime", {}).get("regime")
    except Exception:
        return None


# The pre-registered C6 sampling rule, in ONE place so the code cannot drift
# from the charter (same principle as the single runner-threshold table).
#   NORMAL  -> PRIMARY    counts toward the 30 path-2 events
#   EXPIRY  -> SECONDARY  reported separately, never merged
#   UNKNOWN -> EXCLUDED   session conditions unknown; must not contaminate
#   feed/broker outage -> EXCLUDED  a data-availability failure is not a
#                         detection outcome and must never score against C6
_EXCLUDING_CAUSES = ("FEED_OUTAGE", "BROKER_COOLDOWN")


def _validation_bucket(session_type: str | None, root_cause: str | None) -> str:
    if root_cause in _EXCLUDING_CAUSES:
        return "EXCLUDED"
    if session_type == "EXPIRY":
        return "SECONDARY"
    if session_type == "NORMAL":
        return "PRIMARY"
    return "EXCLUDED"


def _engine_snapshot() -> dict[str, Any]:
    """Read-only snapshot of the live Decision Engine + indicators at this instant.

    This is the JOIN that lets the black box say *why* a runner was not taken —
    "kill switch active", "OI layer 39 < 55", "institutional against". Purely
    reads the shared state singleton; never mutates it, never decides. Anything
    it can't see (RSI/EFI/CPR — IEIE Phase 1 not built yet) stays null.
    """
    try:
        from ..core.state import state
        dec = state.decision or {}
        ks = state.kill_switch or {}
        sig = state.signal or {}
        tech = sig.get("tech") or {}
        an = state.analytics or {}
        rows = ((state.intelligence or {}).get("layers", {}).get("intelligence", {})
                .get("rows", []))
        layers = {r.get("layer"): r.get("score") for r in rows if r.get("layer")}
        return {
            "decision": dec.get("primary_action"),
            "grade": dec.get("grade"),
            "confidence": sig.get("confidence"),
            "kill_switch": bool(ks.get("active")),
            "ks_reasons": ks.get("reasons") or [],
            "pcr": an.get("pcr"),
            "vwap": tech.get("vwap"),
            "adx": tech.get("adx"),
            "atr": tech.get("atr"),
            "underlying": (state.spot or {}).get("ltp"),
            "layers": layers,          # {"Trend":70,"OI":39,"Institutional":30,…}
            "rsi": None, "efi": None, "cpr": None,   # IEIE Phase 1 — filled later
        }
    except Exception:
        return {}


def _root_cause(ep: dict[str, Any], c: dict[str, Any]) -> str | None:
    """Assign the single most-likely cause from AVAILABLE evidence — a ROOT_CAUSE
    tag or None. Priority ladder; only fires a tag it has data for."""
    snap = ep.get("snap_run") or ep.get("snap_start") or {}
    layers = snap.get("layers") or {}

    def layer(name: str) -> float | None:
        v = layers.get(name)
        try:
            return float(v) if v is not None else None
        except (TypeError, ValueError):
            return None

    # a runner we failed to catch early (never alerted = MISSED, or alerted LATE).
    # DETECTION-layer causes only: the radar is independent of the engine gate,
    # so KILL_SWITCH/OI-layer can never explain a radar miss — that priority
    # masked 11/12 miss diagnoses on 2026-07-16 (all were really cold-start /
    # no-ignite). Engine context is still preserved in the 'engine' snapshot.
    if c["is_runner"] and c["capture"] in ("MISSED", "LATE"):
        if not c["alerted"]:
            # miss taxonomy: FIRST check whether data was even flowing — a miss
            # during a broker cooldown / POOR-feed window is a data-availability
            # failure, not a detection failure (owner taxonomy, 2026-07-20)
            ks_txt = " ".join(snap.get("ks_reasons") or []).lower()
            if "cooldown" in ks_txt:
                return "BROKER_COOLDOWN"
            if "data quality poor" in ks_txt or "feed" in ks_txt:
                return "FEED_OUTAGE"
            # detection-layer causes: no coil seen at all (cold start / move
            # already underway) vs coiled but the ignite gate never confirmed
            return "COIL_FAIL" if not ep.get("coil_ts") else "NO_CONFIRMATION"
        return "LATE_CONFIRMATION"

    # an alert that fizzled (fired but never became a real move)
    if c["false_pos"]:
        r = ep.get("reason") or {}
        if not r.get("volume"):
            return "LOW_VOLUME"
        if (r.get("oi_pct") or 0) <= 0:
            return "LOW_OI"
        adx = snap.get("adx")
        if adx is not None and adx < 20:
            return "ADX_WEAK"
        return "NO_CONFIRMATION"

    if c["outcome"] == "SUCCESS":
        return "TARGET_HIT"
    return None


def _stability(traj: list[int]) -> int | None:
    """Trajectory smoothness %: monotonic climb = stable (good), jumpy = low."""
    if len(traj) < 3:
        return None
    diffs = [b - a for a, b in zip(traj, traj[1:])]
    non_drop = sum(1 for d in diffs if d >= 0) / len(diffs)
    return int(round(non_drop * 100))


def _classify(ep: dict[str, Any]) -> dict[str, Any]:
    peak_rise = (ep["peak"] - ep["base"]) / ep["base"] * 100 if ep["base"] else 0.0
    is_runner = (peak_rise >= RUNNER_PCT and (ep["peak"] - ep["base"]) >= MIN_RUNNER_PTS) \
        or ep["runner_ts"] is not None
    alerted = ep["alert_ts"] is not None
    if is_runner:
        cap = "MISSED" if not alerted else ("EARLY" if (ep["alert_rise"] or 0) < EARLY_MAX_PCT else "LATE")
    else:
        cap = None
    false_pos = alerted and peak_rise < REAL_MOVE_PCT
    delay = round(ep["alert_ts"] - ep["move_start_ts"], 1) if (alerted and ep["move_start_ts"]) else None
    potential = round(ep["peak"] - ep["base"], 2)
    captured = round(ep["peak"] - ep["alert_prem"], 2) if alerted else 0.0
    lost = round(potential - captured, 2)
    outcome = "SUCCESS" if is_runner else ("FALSE" if false_pos else "FADE")
    return {"strike": ep["strike"], "type": ep["type"], "peak_rise": round(peak_rise, 1),
            "is_runner": is_runner, "alerted": alerted, "capture": cap,
            "false_pos": false_pos, "delay_s": delay, "outcome": outcome,
            "potential": potential, "captured": captured, "lost": lost,
            "stability": _stability(ep["traj"]),
            "base": round(ep["base"], 2), "peak": round(ep["peak"], 2),
            "alert_prem": round(ep["alert_prem"], 2) if alerted else None}


def _black_box(ep: dict[str, Any]) -> dict[str, Any]:
    """The full per-opportunity record — the learning data, one JSON line."""
    global _seq
    _seq += 1
    c = _classify(ep)
    if ep.get("session_type") in (None, "UNKNOWN"):
        ep["session_type"] = _session_type()   # best-effort resolve before writing
    if not ep.get("regime"):
        ep["regime"] = _behavioural_regime()
    _rc = _root_cause(ep, c)
    return {
        "n": _seq, "day": _day, "symbol": ep.get("symbol", ""),
        "cold_start": bool(ep.get("cold_start")),
        "strike": ep["strike"], "type": ep["type"],
        # t_base added 2026-07-21: base/peak ORDER is what distinguishes a real
        # run from a decline, and it was previously unlogged — forcing past-day
        # forensics to infer it. Never leave the ordering unrecoverable again.
        "t_base": _hhmmss(ep.get("base_ts")),
        "ignite_path": ep.get("ignite_path") or 0,   # 2 = attributable to C6
        "dte": ep.get("dte"),                        # days to expiry at episode start
        "expiry_day": (ep.get("dte") == 0) if ep.get("dte") is not None else None,
        "session_type": ep.get("session_type"),   # CALENDAR axis: NORMAL/EXPIRY/BUDGET/…
        "regime": ep.get("regime"),               # TAPE axis: TRENDING/VOLATILE/…
        "t_coil": _hhmmss(ep["coil_ts"]), "t_move_start": _hhmmss(ep["move_start_ts"]),
        "t_ignite": _hhmmss(ep["alert_ts"]), "t_runner": _hhmmss(ep["runner_ts"]),
        "t_peak": _hhmmss(ep["peak_ts"]), "t_exhaust": _hhmmss(ep["exhaust_ts"]),
        "base": c["base"], "alert_prem": c["alert_prem"], "peak": c["peak"],
        "potential": c["potential"], "captured": c["captured"], "lost": c["lost"],
        "peak_rise": c["peak_rise"], "delay_s": c["delay_s"],
        "reason": ep["reason"], "stability": c["stability"],
        "traj": ep["traj"], "capture": c["capture"], "outcome": c["outcome"],
        # ideal-entry KPI: the best price actually available after the alert
        "ideal_prem": round(ep["ideal_prem"], 2) if ep.get("ideal_prem") else None,
        "t_ideal": _hhmmss(ep.get("ideal_ts")),
        "entry_edge": (round(ep["alert_prem"] - ep["ideal_prem"], 2)
                       if ep.get("alert_prem") and ep.get("ideal_prem") else None),
        "ideal_wait_s": (round(ep["ideal_ts"] - ep["alert_ts"], 1)
                         if ep.get("ideal_ts") and ep.get("alert_ts") else None),
        "root_cause": _rc,                       # WHY — the Evidence-Layer verdict
        # PRIMARY = counts toward the C6 verdict · SECONDARY = expiry, separate
        # · EXCLUDED = unknown conditions or a feed/broker outage
        "validation_bucket": _validation_bucket(ep.get("session_type"), _rc),
        "engine": ep.get("snap_run") or ep.get("snap_start"),  # decision context join
    }


def _close_episode(ep: dict[str, Any]) -> None:
    _closed.append(ep)
    try:                                    # persist the black box (never crash scan)
        bb = _black_box(ep)
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        with (_LOG_DIR / f"{_day}.jsonl").open("a") as f:
            f.write(json.dumps(bb, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _read_disk_today() -> list[dict[str, Any]]:
    """All persisted black-box lines for today (survives restarts)."""
    try:
        p = _LOG_DIR / f"{_day}.jsonl"
        if p.exists():
            return [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]
    except Exception:
        pass
    return []


def _row_from_bb(bb: dict[str, Any]) -> dict[str, Any]:
    """Map a persisted black-box line back to an aggregation row, so report()
    reflects the WHOLE day (disk) — not just what's in memory since the last
    restart. Old-format lines simply lack root_cause/engine (stay None)."""
    cap = bb.get("capture")
    outcome = bb.get("outcome")
    peak_rise = bb.get("peak_rise") or 0.0
    pts = (bb.get("potential") or 0.0)
    # apply the points floor uniformly so historical lines re-clean to the new
    # definition too (old code tagged penny wiggles as runners; drop them now)
    is_runner = pts >= MIN_RUNNER_PTS and (
        cap in ("EARLY", "LATE", "MISSED") or outcome == "SUCCESS" or peak_rise >= RUNNER_PCT)
    alerted = bb.get("alert_prem") is not None or bool(bb.get("t_ignite"))
    return {"strike": bb.get("strike"), "type": bb.get("type"), "peak_rise": peak_rise,
            "is_runner": is_runner, "alerted": alerted, "capture": cap,
            "false_pos": outcome == "FALSE", "delay_s": bb.get("delay_s"),
            "potential": bb.get("potential") or 0.0, "captured": bb.get("captured") or 0.0,
            "lost": bb.get("lost") or 0.0, "stability": bb.get("stability"),
            "entry_edge": bb.get("entry_edge"), "ideal_wait_s": bb.get("ideal_wait_s"),
            "root_cause": bb.get("root_cause")}


def report() -> dict[str, Any]:
    """The live KPI scorecard — restart-proof: aggregates every persisted
    opportunity today (disk) plus still-open episodes in memory. This is what
    makes the day's measurement survive a backend reload (historical-aware)."""
    _roll_day()
    disk_rows = [_row_from_bb(b) for b in _read_disk_today()]        # all closed today
    open_eps = [e for e in _eps.values() if e["peak"] > e["base"] * (1 + STIR_PCT / 100)]
    open_rows = [{**_classify(e), "root_cause": _root_cause(e, _classify(e))} for e in open_eps]
    rows = disk_rows + open_rows                                     # closed(disk) + open(live)

    runners = [r for r in rows if r["is_runner"]]
    early = [r for r in runners if r["capture"] == "EARLY"]
    late = [r for r in runners if r["capture"] == "LATE"]
    missed = [r for r in runners if r["capture"] == "MISSED"]
    alerts = [r for r in rows if r["alerted"]]
    false_alerts = [r for r in alerts if r["false_pos"]]
    delays = [r["delay_s"] for r in rows if r["delay_s"] is not None]
    stabs = [r["stability"] for r in rows if r["stability"] is not None]

    pot_sum = sum(r["potential"] for r in runners)
    cap_sum = sum(max(0.0, r["captured"]) for r in runners)
    recovered = round(cap_sum / pot_sum * 100, 1) if pot_sum > 0 else None

    # ── root-cause breakdown — the actionable "why" over every miss + false ──
    causes: dict[str, int] = {}
    for r in rows:
        is_miss = r["is_runner"] and r["capture"] in ("MISSED", "LATE")
        if not (is_miss or r["false_pos"]):
            continue
        rc = r.get("root_cause")
        if rc:
            causes[rc] = causes.get(rc, 0) + 1
    root_causes = dict(sorted(causes.items(), key=lambda kv: kv[1], reverse=True))

    return {
        "day": _day,
        "capture_rate": round(len(early) / len(runners) * 100, 1) if runners else None,
        "runners_total": len(runners),
        "detected_early": len(early), "detected_late": len(late),
        "missed_completely": len(missed),
        "alerts_total": len(alerts), "false_alerts": len(false_alerts),
        "alert_accuracy": round((len(alerts) - len(false_alerts)) / len(alerts) * 100, 1) if alerts else None,
        "avg_detection_delay_s": round(sum(delays) / len(delays), 1) if delays else None,
        "recovered_pct": recovered,
        "lost_pct": round(100 - recovered, 1) if recovered is not None else None,
        # ideal-entry KPI (decides Best Entry Engine #019): how often a retest
        # gave a better price than the alert, and by how much on average
        "retest_rate": (lambda edges: round(
            sum(1 for e in edges if e > 0.5) / len(edges) * 100, 1) if edges else None)(
            [r.get("entry_edge") for r in rows if r.get("entry_edge") is not None]),
        "avg_entry_edge": (lambda edges: round(sum(edges) / len(edges), 2) if edges else None)(
            [r.get("entry_edge") for r in rows if r.get("entry_edge") is not None]),
        "root_causes": root_causes,   # {"KILL_SWITCH":6,"LOW_OI":4,…} — the "why" breakdown
        "avg_stability": int(round(sum(stabs) / len(stabs))) if stabs else None,
        "missed_money": [
            {"strike": r["strike"], "type": r["type"], "potential": r["potential"],
             "captured": r["captured"], "lost": r["lost"]}
            for r in sorted(runners, key=lambda r: r["lost"], reverse=True)[:5]
            if r["potential"] > 0
        ],
        "sample": len(rows),
        "note": ("System-measured, not eyeballed. Every opportunity is logged to "
                 "a durable black box (data/opportunity_log). Thresholds declared "
                 f"(stir +{STIR_PCT:.0f}%, runner +{RUNNER_PCT:.0f}%, early "
                 f"<+{EARLY_MAX_PCT:.0f}%, false <+{REAL_MOVE_PCT:.0f}% in "
                 f"{FALSE_WINDOW_S // 60}m) — tune from evidence. Measurement only."),
        "as_of": int(time.time()),
    }


def capture_status(strike: int, typ: str) -> str | None:
    """Best-known capture verdict (EARLY / LATE / MISSED) for a strike's current
    or last episode today — lets the radar's 'Missed' panel label big movers by
    whether we ACTUALLY caught them, reconciling that panel with the black box.
    None = not a runner / unknown."""
    _roll_day()
    for e in _eps.values():                       # live episode first
        if e["strike"] == strike and e["type"] == typ:
            return _classify(e)["capture"]
    for e in reversed(_closed):                   # else last closed today
        if e["strike"] == strike and e["type"] == typ:
            return _classify(e)["capture"]
    return None


def black_box_log(limit: int = 50) -> dict[str, Any]:
    """Raw per-opportunity black-box entries for today (newest first) — the
    learning data that Opportunity Replay + AI Journal will render tomorrow."""
    _roll_day()
    entries: list[dict[str, Any]] = []
    try:
        p = _LOG_DIR / f"{_day}.jsonl"
        if p.exists():
            entries = [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]
    except Exception:
        entries = []
    # include still-open episodes that have already moved (live, not yet on disk)
    live = [_black_box_preview(e) for e in _eps.values()
            if e["peak"] > e["base"] * (1 + STIR_PCT / 100)]
    entries = (entries + live)[-limit:]
    entries.reverse()
    return {"day": _day, "count": len(entries), "entries": entries}


def _black_box_preview(ep: dict[str, Any]) -> dict[str, Any]:
    c = _classify(ep)
    if ep.get("session_type") in (None, "UNKNOWN"):
        ep["session_type"] = _session_type()   # best-effort resolve before writing
    if not ep.get("regime"):
        ep["regime"] = _behavioural_regime()
    _rc = _root_cause(ep, c)
    return {"n": "live", "day": _day, "strike": ep["strike"], "type": ep["type"],
            "t_coil": _hhmmss(ep["coil_ts"]), "t_ignite": _hhmmss(ep["alert_ts"]),
            "t_peak": _hhmmss(ep["peak_ts"]), "t_exhaust": _hhmmss(ep["exhaust_ts"]),
            "base": c["base"], "peak": c["peak"], "potential": c["potential"],
            "captured": c["captured"], "reason": ep["reason"],
            "stability": c["stability"], "capture": c["capture"], "outcome": "OPEN"}
