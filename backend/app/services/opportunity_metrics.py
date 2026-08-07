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
# OBS-17 fix (owner, 2026-08-05) — how close an episode's own peak must sit to
# the peak a caller is asking about before it's accepted as THAT episode,
# rather than whichever one happens to be live right now for the same
# (strike, type). See capture_status() below for why this exists.
PEAK_MATCH_TOL_PCT = 2.0
FALSE_WINDOW_S = 300  # …within 5 min of the alert
CLOSE_GAP_S = 300     # episode closes only after 5 min quiet past the peak
GIVEBACK_CLOSE = 0.70 # …AND only once it has given back ≥70% of the run. A
#                       normal pullback that holds is the SAME opportunity, not
#                       a new one — this stops one oscillating strike from being
#                       chopped into 20+ phantom episodes (measurement integrity)
EXHAUST_OFF_PEAK = 0.90  # premium ≤ 90% of peak after the peak = exhaustion
STALE_CLOSE_S = 300   # no tick for 5 min ⇒ the strike left the ATM window and the
#                       radar stopped feeding it. premium_radar.py:313 drops a track
#                       after 120s of no update and then NEVER calls record() for
#                       that key again — so nothing can ever satisfy the normal
#                       close condition and the episode is stuck open forever
#                       (2026-07-22: 57 episodes open >1h). The measurement layer
#                       had no reaper mirroring the radar's stale-track drop; this
#                       is it. 300s = a comfortable margin past the radar's 120s so
#                       a brief ATM re-entry is never mistaken for abandonment.
SWEEP_EVERY_S = 60    # how often record() runs the stale-episode reaper (throttle)
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

# RESEARCH MODE (owner, 2026-07-21). On 2026-07-21 a synthetic episode from a
# verification run leaked into live measurement: record() triggers
# _checkpoint_open(), which wrote the PRODUCTION log path because that path was
# the DEFAULT — touching it required no explicit intent. A restart then restored
# it and it was counted in live KPIs (detected_early read 1 when the truth was 0).
# Isolation by convention would fail again, so it is now structural:
#   CAT_RESEARCH_MODE=1 → never checkpoint, never restore, never write to disk
#                         (in-memory _closed still populates, so tests assert fine)
#   CAT_DATA_DIR=<path>  → redirect the log directory wholesale
import os
RESEARCH_MODE = os.getenv("CAT_RESEARCH_MODE", "").strip() in ("1", "true", "yes")
_LOG_DIR = (pathlib.Path(os.environ["CAT_DATA_DIR"]) if os.getenv("CAT_DATA_DIR")
            else pathlib.Path(__file__).resolve().parents[3] / "data" / "opportunity_log")

_eps: dict[str, dict[str, Any]] = {}     # live episode per strike key
_closed: list[dict[str, Any]] = []       # completed episodes today (in-memory)
_day: str | None = None
_seq = 0                                 # opportunity number, per day
_seen_keys: set[str] = set()             # keys tracked at least once today
_last_ckpt = 0.0                         # last open-episode checkpoint write
_last_sweep = 0.0                        # last stale-episode sweep (reaper throttle)
_restored = False                        # open episodes restored after (re)start?
CKPT_EVERY_S = 10                        # checkpoint cadence (measurement only)
# Observability only (owner, 2026-07-23 — Measurement Health card, item #1).
# A flat/never-alerted episode carries no measurement, so _sweep_stale() drops
# it without a black-box line (by design — see its docstring). That silence is
# exactly what a "Dropped" counter on the dashboard needs to show, so it is
# counted here. This is the ONLY touch to this file this session — a bare
# increment inside the sweep's existing flat-branch, day-scoped like every
# other counter above. It changes no close/reap DECISION: which episodes get
# dropped vs. reaped is unchanged, this just tallies what already happens.
_dropped_today = 0


def _today() -> str:
    return datetime.datetime.now(IST).strftime("%Y-%m-%d")


def _roll_day() -> None:
    global _day, _seq, _dropped_today
    d = _today()
    if d != _day:
        # Close any still-open episodes to the OLD day before clearing, so a clean
        # cross-midnight (a process that never restarted) does not silently discard
        # the day's last open movers. _day is still the old day here, so these
        # write to the correct jsonl. Same eventful-only rule as the stale sweep.
        if _day is not None:
            for ep in list(_eps.values()):
                if ep["peak"] > ep["base"] * (1 + STIR_PCT / 100) or ep.get("alert_ts") is not None:
                    ep["close_reason"] = ep.get("close_reason") or "EOD"
                    _close_episode(ep)
        _eps.clear(); _closed.clear(); _seen_keys.clear(); _seq = 0; _dropped_today = 0
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
    if RESEARCH_MODE:
        return                      # research: never touch production state
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
    if RESEARCH_MODE:
        return                      # research: never resurrect production episodes
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
        # A same-day restart resurrects the open set INCLUDING strikes that had
        # already left ATM before the restart (their last_seen is old). Reap them
        # now instead of waiting for a fresh tick that will never come for a
        # drifted strike — otherwise a restart re-inflates the stuck-open count.
        _sweep_stale(time.time())
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
            # Late-catch diagnosis (owner, 2026-08-07) — Step 1, observational
            # only. `record()`'s own `rise_pct` PARAMETER (the detector's
            # rolling-5-min-window rise from premium_radar._series_metrics)
            # was received every tick but never once read in this function —
            # alert_rise above comes from a SEPARATE episode-base `rise`
            # computed locally. So the black box has never recorded what the
            # rolling detector actually saw at the instant it fired IGNITING,
            # which is the number _coil()'s own thresholds (rise_pct<18-20)
            # gate on. Capturing it here changes no threshold, no gate, no
            # classification — it only makes an already-computed number
            # visible for future root-cause work.
            "alert_detector_rise_pct": None,
            "runner_ts": None, "runner_prem": None, "exhaust_ts": None,
            # ideal-entry tracking (owner's missing KPI): after the alert, the
            # lowest premium BEFORE the final peak = the best entry that was
            # actually available. entry_edge = alert_prem − ideal_prem
            # (>0 ⇒ a retest gave a better price than the alert moment — the
            # evidence that decides the Best Entry Engine proposal #019).
            "ideal_prem": None, "ideal_ts": None,
            "_low_since_alert": None, "_low_ts": None,
            "reason": None, "traj": [], "last_traj_ts": 0.0, "started": now,
            # last_seen = the last tick for this key. When a strike leaves the ATM
            # window the radar stops feeding it (premium_radar.py:313), last_seen
            # freezes, and the stale sweep reaps the episode after STALE_CLOSE_S.
            # close_reason records HOW an episode ended (EXHAUST / STALE / EOD) so
            # a reaped close — whose exhaust was never observed — is never silently
            # trusted as a true exhaustion in later forensics.
            "last_seen": now, "close_reason": None,
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
    ep["last_seen"] = now        # freezes the moment the strike leaves ATM → stale sweep

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
        ep["alert_detector_rise_pct"] = rise_pct   # the rolling value _coil() actually gated on
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
        ep["close_reason"] = "EXHAUST"
        _close_episode(ep)
        _eps[key] = _new_ep(strike, typ, premium, now)

    _sweep_stale(now)            # reap episodes whose strike left ATM (throttled)
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
        # Path fixed 2026-07-21 (bug #11 — twin of bug #8). This walked
        # layers→intelligence→rows; the rows live one level deeper under
        # decision_matrix, so this dict was EMPTY on every episode ever
        # recorded (0 of 2363 black-box lines carry layer context). The
        # docstring calls this "the JOIN that lets the black box say why a
        # runner was not taken" — that join never worked.
        # I fixed the identical path in decision_contract._layers() this
        # morning and did NOT grep for the pattern, which is the exact
        # standing lesson recorded hours earlier. Same defect, two files.
        rows = (((state.intelligence or {}).get("layers") or {})
                .get("intelligence", {}).get("decision_matrix", {})
                .get("rows", []))
        layers = {r.get("layer"): r.get("score") for r in rows if r.get("layer")}
        # V7.1 Trade Explorer Phase 3A (owner, 2026-08-04) — OBSERVATIONAL.
        # Persist where the real S/R levels sat at this instant so the
        # question "did the structural target get hit before the ATR one?"
        # can be answered from data later instead of from screenshots.
        # This is recorded ONLY. It feeds no target, veto, score, calibration,
        # kill switch or execution — the engine still trades its fixed ATR
        # multiples, unchanged. Trimmed to the fields the observation window
        # actually needs; the full payload stays in the live packet.
        st = ((state.intelligence or {}).get("layers") or {}).get("structural_targets") or {}
        structural = {
            "available": bool(st.get("available")),
            "direction": st.get("direction"),
            "source": "support_resistance.compute_levels",
            "spot": st.get("spot"),
            "levels": [
                {"label": t.get("label"), "level": t.get("level"),
                 "distance_pts": t.get("distance_pts"),
                 "strength_score": t.get("strength_score"),
                 "touches": t.get("touches"), "bounce_pct": t.get("bounce_pct")}
                for t in (st.get("targets") or [])
            ],
            "comparison": st.get("comparison") or [],
        } if st else {"available": False, "source": "support_resistance.compute_levels"}
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
            "structural_targets": structural,   # Phase 3A — observation only
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
        # Late-catch diagnosis (owner, 2026-08-07) — Step 1. alert_rise (above,
        # via `c`/`peak_rise` context) is the EPISODE-BASE rise at ignite time.
        # This is the separate rolling-5-min-window rise_pct _coil() actually
        # gated its IGNITING decision on. The gap between the two is the
        # suspected root cause of late catches on smooth trend days — this
        # field lets that be checked against real data instead of assumed.
        "alert_rise": ep.get("alert_rise"),
        "alert_detector_rise_pct": ep.get("alert_detector_rise_pct"),
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
        # how the episode ended: EXHAUST (true give-back), STALE (strike left ATM,
        # exhaust unobserved), EOD (still open at day roll). None = legacy line.
        "close_reason": ep.get("close_reason"),
        "engine": ep.get("snap_run") or ep.get("snap_start"),  # decision context join
    }


def _close_episode(ep: dict[str, Any]) -> None:
    _closed.append(ep)
    if RESEARCH_MODE:
        return                      # in-memory only; assertions still work
    try:                                    # persist the black box (never crash scan)
        bb = _black_box(ep)
        _LOG_DIR.mkdir(parents=True, exist_ok=True)
        with (_LOG_DIR / f"{_day}.jsonl").open("a") as f:
            f.write(json.dumps(bb, ensure_ascii=False) + "\n")
    except Exception:
        pass


def _sweep_stale(now: float) -> None:
    """Close episodes whose strike left the ATM window (measurement integrity).

    premium_radar drops a track after 120s of no update (premium_radar.py:313)
    and then never calls record() for that key again, so the episode's normal
    close condition (moved + exhausted + quiet) can never be met and it stays
    open forever — 2026-07-22 accumulated 57 episodes stuck open >1h. This is the
    reaper the measurement layer was missing, mirroring the radar's own drop.

    An EVENTFUL episode (it moved ≥STIR_PCT, or it alerted) is black-boxed with
    close_reason='STALE' — it carries real measurement (a runner/fade/false whose
    exhaust simply went unobserved when the strike left ATM), and the tag keeps
    that unobserved exhaust honest in forensics. A flat, never-alerted strike
    carried no measurement and is dropped without a black-box line, so the log is
    not flooded with non-events (which is what the 57 mostly were)."""
    global _last_sweep, _dropped_today
    if now - _last_sweep < SWEEP_EVERY_S:
        return
    _last_sweep = now
    for key, ep in list(_eps.items()):
        if now - ep.get("last_seen", ep.get("started", now)) <= STALE_CLOSE_S:
            continue
        eventful = ep["peak"] > ep["base"] * (1 + STIR_PCT / 100) or ep.get("alert_ts") is not None
        if eventful:
            ep["close_reason"] = "STALE"
            _close_episode(ep)
        else:
            _dropped_today += 1     # observability only (item #1) — same drop, now counted
        _eps.pop(key, None)


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
    _raw_today = _read_disk_today()                                  # raw persisted lines today
    disk_rows = [_row_from_bb(b) for b in _raw_today]                 # all closed today
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
        # Measurement Health (owner, 2026-07-23 — item #1). open_episodes is the
        # live count, exactly as spec'd. status is NOT literally "open==0" —
        # dozens of episodes legitimately open mid-session is normal operation,
        # not a defect (that would make the card cry wolf all day, every day).
        # The real #0 bug was STALE-and-stuck open episodes past STALE_CLOSE_S;
        # open_stale (open AND already past the reaper's own threshold, i.e.
        # waiting on the next throttled sweep tick) is the honest degradation
        # signal, so status is keyed off that instead.
        "measurement_health": {
            "open_episodes": len(_eps),
            "open_stale": sum(1 for e in _eps.values()
                               if time.time() - e.get("last_seen", e.get("started", 0)) > STALE_CLOSE_S),
            "recovered_today": sum(1 for b in _raw_today if b.get("close_reason") in ("STALE", "EOD")),
            "dropped_today": _dropped_today,
            "status": "DEGRADED" if any(
                time.time() - e.get("last_seen", e.get("started", 0)) > STALE_CLOSE_S
                for e in _eps.values()) else "HEALTHY",
            "note": ("open_episodes = live in-flight count (normal to be >0 all "
                     "session); open_stale/status flag episodes stuck PAST the "
                     "reaper threshold — that combination is the real fault "
                     "signal #0 fixed. recovered_today/dropped_today are the "
                     "reaper's own tally for today."),
        },
        "as_of": int(time.time()),
    }


def capture_status(strike: int, typ: str, peak_hint: float | None = None) -> str | None:
    """Best-known capture verdict (EARLY / LATE / MISSED) for a strike's
    episode today — lets the radar's 'Missed' panel label big movers by
    whether we ACTUALLY caught them, reconciling that panel with the black box.
    None = not a runner / unknown.

    OBS-17 (found 2026-08-04, Observation Window): a strike can re-ignite
    into a brand-new episode (_new_ep) after its first big move closes.
    Without `peak_hint`, this function always answered for "whichever
    episode is live right now for this strike" — so a caller displaying an
    already-settled +186.9% move got the verdict for a fresh, still-immature
    +3% episode instead, flipping an already-correct ✓ to ✗ with zero new
    price data. `peak_hint` is the peak premium the CALLER is actually asking
    about (e.g. premium_radar.py's own `t["peak_prem"]`, which tracks a
    strike's peak-of-the-day and does not reset when the episode does) — this
    searches CLOSED episodes first for the one whose own peak actually
    matches that value, so the verdict is for the move being displayed, not
    for whatever happens to be live at query time. Backward compatible: with
    no hint, behaviour is unchanged (live-first, then last-closed)."""
    _roll_day()
    if peak_hint is not None and peak_hint > 0:
        tol = peak_hint * PEAK_MATCH_TOL_PCT / 100
        # closed episodes are the definitive record of a completed move —
        # check them before any live (possibly unrelated, still-forming) one
        for e in reversed(_closed):
            if e["strike"] == strike and e["type"] == typ and abs(e["peak"] - peak_hint) <= tol:
                return _classify(e)["capture"]
        for e in _eps.values():
            if e["strike"] == strike and e["type"] == typ and abs(e["peak"] - peak_hint) <= tol:
                return _classify(e)["capture"]
        # no episode's own peak explains this value — honest unknown rather
        # than guessing via whatever is live (the exact bug being fixed)
        return None
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
            "stability": c["stability"], "capture": c["capture"], "outcome": "OPEN",
            "alert_rise": ep.get("alert_rise"),
            "alert_detector_rise_pct": ep.get("alert_detector_rise_pct")}


# ── OBSERVED OUTCOME STATISTICS (owner, 2026-07-21) ─────────────────────────
# NOT a probability engine. This reports what ACTUALLY happened in the black
# box: of every episode the radar ignited on, what fraction went on to reach
# +5/+10/.../+100 premium points. Backward-looking frequency, nothing else.
#
# It replaces a declared decay curve (execution_card's
# 100*exp(-0.7*pts/em)*(0.6+0.4*edge)) that was never checked against outcomes
# and overstated reality by 3x at 20pt and ~50x at 100pt — the dashboard showed
# "100pt 42%" when 9 of 1694 ignitions (0.5%) ever got there. Unlike the other
# 2026-07-21 bugs, which hid information, that one manufactured opportunity.
#
# The owner's rule, adopted: history and prediction must never wear the same
# word. This ships as "Observed", carries its sample size, and is explicitly
# labelled not-a-forecast. A separate predictive engine (charter Layer 6, Move
# Prediction) remains unbuilt and frozen — it is NOT this.
_OUTCOME_PTS = (5, 10, 20, 30, 40, 50, 80, 100)
_stats_cache: dict[str, Any] = {"at": 0.0, "val": None}
_STATS_TTL_S = 300


def observed_reach_pct(pts: float) -> float | None:
    """Observed % of past ignitions that reached >= pts. Used by any panel that
    would otherwise invent a number (the opportunity ladder did)."""
    st = outcome_stats()
    if not st.get("sample_n"):
        return None
    best = None
    for r in st["rows"]:
        if r["points"] <= pts:
            best = r
    return (best or st["rows"][0])["reached_pct"]


def outcome_stats() -> dict[str, Any]:
    """Observed reach-rates across the whole black box. Cached ~5 min."""
    now = time.time()
    if _stats_cache["val"] is not None and now - _stats_cache["at"] < _STATS_TTL_S:
        return _stats_cache["val"]
    alerted: list[dict[str, Any]] = []
    try:
        for f in sorted(_LOG_DIR.glob("*.jsonl")):
            for line in f.read_text().splitlines():
                if not line.strip():
                    continue
                try:
                    r = json.loads(line)
                except Exception:
                    continue
                if r.get("t_ignite"):
                    alerted.append(r)
    except Exception:
        pass
    n = len(alerted)
    rows = []
    for pts in _OUTCOME_PTS:
        hit = sum(1 for r in alerted if (r.get("potential") or 0) >= pts)
        rows.append({"points": pts, "reached": hit,
                     "reached_pct": round(100 * hit / n, 1) if n else None})
    false_n = sum(1 for r in alerted if r.get("outcome") == "FALSE")
    out = {
        "observed": True,
        "sample_n": n,
        "days": len({r.get("day") for r in alerted if r.get("day")}),
        "rows": rows,
        "false_alert_pct": round(100 * false_n / n, 1) if n else None,
        "note": ("Observed historical frequency across the black box — NOT a "
                 "future prediction and NOT a win probability. Says only: of "
                 "past ignitions, this fraction went on to reach N points."),
    }
    _stats_cache.update({"at": now, "val": out})
    return out
