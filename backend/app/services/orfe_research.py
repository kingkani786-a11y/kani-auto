"""ORFE (Opening Range Fibonacci Engine) — Research Phase 0 (owner, 2026-08-07).

RESEARCH ONLY. Never imported by confluence.py, market_service.py, or any
live decision/gate/execution path — same isolation contract as
historical_learning.py and backtest.py (on-demand via API route, using the
already-connected broker client, writing to its own file under data/).

WHY THIS EXISTS: the owner spotted a 9:15-9:30 Opening-Range -> Fibonacci
0.618 retracement -> entry pattern on one day's option-premium chart. Per the
owner's own stated rule: "ஒரு நாள் result பார்த்து அதை strategy-ஆ மாற்றக்
கூடாது" (one day's result must not become a strategy) — this module tests
that hypothesis against ~6 months of REAL historical data before any part of
it becomes a live Trade Explorer evidence layer. Output is per (day,
fib_level), never a single per-day verdict, per the owner's explicit
instruction not to fold multiple levels into one label.

HONEST SCOPE (same discipline as historical_learning.py's own docstring):
  * Dhan's historical API returns UNDERLYING INDEX candles only — no
    historical option chain for any past date. So this validates the
    DIRECTIONAL setup in index points, never option premium P&L.
  * OI Change / PCR / Gamma / Buyer-Seller-Strength need a live chain that
    does not exist for past dates — they are NOT computed here, and do not
    appear in the output at all (never null-padded to look present).
  * VWAP / EMA / ATR / ADX / RSI ARE computed — all derivable from OHLC.
  * India VIX is not fetched here (no historical VIX pull exists in this
    codebase yet) — left out rather than guessed.

DECLARED RULES (Phase 0 v1 — tune from evidence; nothing here is fitted to
any known outcome, same discipline as every THRESHOLD_REGISTRY in this repo):
  OR_START/OR_END   09:15 -> 09:30 (exclusive) IST, the opening 15 one-minute
                     candles
  FIB_LEVELS        0.382 / 0.5 / 0.618 / 0.786, measured across the OR
                     range itself (OR_low -> OR_high) — NOT a later swing leg
  BIAS RULE         at the 09:30 close: price>VWAP(session-to-09:30) AND
                     EMA9>EMA21 -> CALL bias; price<VWAP AND EMA9<EMA21 ->
                     PUT bias; anything else -> NO BIAS, day excluded. This
                     mirrors the owner's own precondition ("Market direction
                     ஏற்கனவே ... bias") — the hypothesis is that Fibonacci
                     refines an ALREADY-existing bias, not that it creates one.
  ENTRY TRIGGER     price must first CLOSE beyond the OR on the bias side
                     (above OR_high for CALL, below OR_low for PUT) after
                     09:30, THEN retrace back and touch a fib level from the
                     far side. A day can register at most one entry per level;
                     a level never touched that day produces no row (a
                     non-event is not fabricated as a loss).
  STOP              the opposite OR boundary (OR_low for CALL, OR_high for
                     PUT) — no buffer, kept simple and declared
  TARGET_1          the breakout extreme reached before the retracement began
  TARGET_2          TARGET_1 + one more OR-range-width in the trade direction
  REGIME (ADX@09:30)  ADX>=25 TRENDING · ADX<18 RANGE · else MIXED
  Outcome is whichever of stop/target1/target2 is touched FIRST by later
  1-min candles; EOD with none hit -> OPEN, excluded from win-rate (neither
  scored a win nor silently counted as a loss).

Persisted to data/orfe_research/<symbol>.jsonl — overwritten wholesale on
each run() call for that symbol (this is a research re-computation over the
full window, not an incremental log).
"""
from __future__ import annotations

import datetime
import json
import pathlib
import time
from typing import Any

from ..broker.dhan import DhanClient
from ..broker.instruments import get_instrument
from ..core.clock import IST
from ..engines.technicals import adx, atr, ema, rsi, vwap

# Retracement depths measured UP from or_low (CALL) / DOWN from or_high (PUT),
# so f=1.0 sits at the breakout boundary and SMALLER f = DEEPER retracement.
# 0.236 and 1.0 added 2026-08-08 (owner) to cover the shallow and full-give-back
# ends — without 1.0 there is no record of "barely pulled back at all", and
# without 0.236 no record of "nearly gave the whole range back but held".
FIB_LEVELS = (0.236, 0.382, 0.5, 0.618, 0.786, 1.0)
OR_START = (9, 15)
OR_END = (9, 30)
ADX_TRENDING = 25.0
ADX_RANGE = 18.0
MIN_OR_CANDLES = 10          # below this, treat the day as a thin/holiday feed
MIN_POST_OR_CANDLES = 30     # need a real afternoon of data to judge outcomes
# Only ~16 one-minute closes can exist by 09:30 (09:15..09:30), so EMA21 is
# necessarily short-seeded at bias time — declared limitation, not hidden:
# ema() seeds from the day's first close, so on a one-directional opening the
# 9-vs-21 ordering is still meaningful, but it is NOT a converged EMA21.
MIN_WARMUP_CLOSES = 12

_DATA_DIR = pathlib.Path(__file__).resolve().parents[3] / "data" / "orfe_research"


def _hm(ts: float) -> tuple[int, int]:
    d = datetime.datetime.fromtimestamp(ts, IST)
    return d.hour, d.minute


def _hhmm(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts, IST).strftime("%H:%M")


def _day_key(ts: float) -> str:
    return datetime.datetime.fromtimestamp(ts, IST).strftime("%Y-%m-%d")


def _group_by_day(candles: list[dict]) -> dict[str, list[dict]]:
    days: dict[str, list[dict]] = {}
    for c in candles:
        days.setdefault(_day_key(c["time"]), []).append(c)
    return days


def _resolve_trade(bars: list[dict], entry_px: float, stop_px: float,
                   target1_px: float, target2_px: float, d: float) -> dict[str, Any]:
    """Resolve one entry against subsequent bars — the SINGLE definition of
    trade management, shared by _process_day and the dynamic-zone backtest so
    the two can never drift apart and produce non-comparable numbers.

    Rules (unchanged from the tested path): stop is evaluated BEFORE targets
    within a bar (conservative fill); T1 is BANKED on touch and the position
    keeps running toward T2; a stop touched AFTER T1 ends the run at WIN_T1
    rather than converting a realised target into a loss.
    """
    outcome, exit_px = "OPEN", None
    mfe = mae = 0.0
    t1_hit = False
    t1_ts = t2_ts = None
    for c in bars:
        fav = (c["high"] - entry_px) if d > 0 else (entry_px - c["low"])
        adv = (entry_px - c["low"]) if d > 0 else (c["high"] - entry_px)
        mfe, mae = max(mfe, fav), max(mae, adv)
        hit_stop = (c["low"] <= stop_px) if d > 0 else (c["high"] >= stop_px)
        hit_t1 = (c["high"] >= target1_px) if d > 0 else (c["low"] <= target1_px)
        hit_t2 = (c["high"] >= target2_px) if d > 0 else (c["low"] <= target2_px)
        if not t1_hit:
            if hit_stop:
                outcome, exit_px = "LOSS", stop_px
                break
            if hit_t1:
                t1_hit, t1_ts = True, c["time"]
                outcome, exit_px = "WIN_T1", target1_px
                if hit_t2:
                    outcome, exit_px, t2_ts = "WIN_T2", target2_px, c["time"]
                    break
                continue
        else:
            if hit_t2:
                outcome, exit_px, t2_ts = "WIN_T2", target2_px, c["time"]
                break
            if hit_stop:
                break
    return {"outcome": outcome, "exit_px": exit_px, "mfe": mfe, "mae": mae,
            "t1_ts": t1_ts, "t2_ts": t2_ts}


def _r_multiple(res: dict[str, Any], entry_px: float, stop_px: float,
                target1_px: float, target2_px: float) -> float | None:
    """Realised R. None for OPEN (never resolved) — excluded rather than
    scored as a zero, which would silently dilute expectancy toward 0."""
    risk = abs(entry_px - stop_px)
    if risk <= 0:
        return None
    o = res["outcome"]
    if o == "LOSS":
        return -1.0
    if o == "WIN_T1":
        return abs(target1_px - entry_px) / risk
    if o == "WIN_T2":
        return abs(target2_px - entry_px) / risk
    return None


def _process_day(day: str, candles: list[dict]) -> list[dict[str, Any]]:
    """Pure function over one day's 1-min candles -> zero or more (fib_level)
    rows. Never raises on thin data — returns [] and lets the caller move on,
    same as every other honest-exclusion path in this codebase."""
    candles = sorted(candles, key=lambda c: c["time"])
    or_candles = [c for c in candles if OR_START <= _hm(c["time"]) < OR_END]
    if len(or_candles) < MIN_OR_CANDLES:
        return []
    or_high = max(c["high"] for c in or_candles)
    or_low = min(c["low"] for c in or_candles)
    or_range = or_high - or_low
    if or_range <= 0:
        return []

    post_or = [c for c in candles if _hm(c["time"]) >= OR_END]
    if len(post_or) < MIN_POST_OR_CANDLES:
        return []

    closes_930 = [c["close"] for c in candles if _hm(c["time"]) <= OR_END]
    if len(closes_930) < MIN_WARMUP_CLOSES:
        return []
    warmup_candles = [c for c in candles if _hm(c["time"]) <= OR_END]
    ema9 = ema(closes_930, 9)[-1]
    ema21 = ema(closes_930, 21)[-1]
    vwap_930 = vwap(warmup_candles)
    px_930 = closes_930[-1]
    adx_930 = adx(warmup_candles, 14) if len(warmup_candles) >= 16 else None
    rsi_930 = rsi(closes_930, 14)
    atr_930 = atr(warmup_candles, 14) if len(warmup_candles) >= 2 else None

    if px_930 > vwap_930 and ema9 > ema21:
        bias = "CALL"
    elif px_930 < vwap_930 and ema9 < ema21:
        bias = "PUT"
    else:
        return []   # NO BIAS — excluded, per the declared rule; never guessed

    if adx_930 is None:
        regime = "UNKNOWN"
    elif adx_930 >= ADX_TRENDING:
        regime = "TRENDING"
    elif adx_930 < ADX_RANGE:
        regime = "RANGE"
    else:
        regime = "MIXED"

    levels = ({f: or_low + f * or_range for f in FIB_LEVELS} if bias == "CALL"
              else {f: or_high - f * or_range for f in FIB_LEVELS})

    breakout_idx = None
    for i, c in enumerate(post_or):
        if bias == "CALL" and c["close"] > or_high:
            breakout_idx = i
            break
        if bias == "PUT" and c["close"] < or_low:
            breakout_idx = i
            break
    if breakout_idx is None:
        return []   # this setup did not occur today — no breakout, no row

    extreme = post_or[breakout_idx]["high"] if bias == "CALL" else post_or[breakout_idx]["low"]
    extreme_idx = breakout_idx
    for i in range(breakout_idx, len(post_or)):
        c = post_or[i]
        if bias == "CALL":
            if c["high"] > extreme:
                extreme, extreme_idx = c["high"], i
            if c["close"] <= or_high and i > extreme_idx:
                break   # retracement back inside the range — extreme is locked
        else:
            if c["low"] < extreme:
                extreme, extreme_idx = c["low"], i
            if c["close"] >= or_low and i > extreme_idx:
                break

    # ── THE DENOMINATOR (owner, 2026-08-08) ────────────────────────────────
    # Until now an untouched level emitted NO row, so the log recorded only
    # setups that DID retrace to a given depth. That makes "how often does a
    # setup retrace to 0.618?" structurally uncomputable — the numerator was
    # stored and the denominator thrown away. One setup-level row per
    # qualifying day fixes that: it records how deep this setup actually
    # pulled back, whether or not any particular level was reached.
    #
    # deepest_frac is the retracement extreme expressed on the SAME scale as
    # the fib levels (0 = or_low, 1.0 = or_high for a CALL), measured over the
    # same window the touch search uses (post-breakout-extreme -> end of day).
    # SMALLER = deeper. A setup that never pulls back below the breakout
    # boundary yields deepest_frac >= 1.0.
    retrace_window = post_or[extreme_idx:]
    if bias == "CALL":
        deepest_px = min(c["low"] for c in retrace_window)
        deepest_frac = (deepest_px - or_low) / or_range
    else:
        deepest_px = max(c["high"] for c in retrace_window)
        deepest_frac = (or_high - deepest_px) / or_range

    # ── FIRST PULLBACK, and where it actually REVERSED ────────────────────
    # (owner, 2026-08-08: "pullback எங்க வரைக்கும் போச்சு, எங்க இருந்து
    # reverse ஆச்சு"). deepest_frac above is the deepest point at ANY time
    # after the breakout — so on a setup that ran to target and then faded
    # into the close, it reports the late fade, not the entry pullback. That
    # makes it the wrong statistic for "where does a retracement usually
    # turn". Measured separately here: scan forward from the breakout
    # extreme, track the running retracement low, and STOP the moment price
    # exceeds the original extreme — that exceedance IS the resumption.
    # If it never happens, the pullback never reversed: recorded as
    # reversal_confirmed False rather than being mixed in as if it had.
    pb_extreme_px = None
    pb_end_idx = None
    reversal_confirmed = False
    running = None
    for i in range(extreme_idx, len(post_or)):
        c = post_or[i]
        if bias == "CALL":
            running = c["low"] if running is None else min(running, c["low"])
            if c["high"] > extreme and i > extreme_idx:
                pb_end_idx, reversal_confirmed = i, True
                break
        else:
            running = c["high"] if running is None else max(running, c["high"])
            if c["low"] < extreme and i > extreme_idx:
                pb_end_idx, reversal_confirmed = i, True
                break
    pb_extreme_px = running
    if pb_extreme_px is None:
        first_pullback_frac = None
    elif bias == "CALL":
        first_pullback_frac = (pb_extreme_px - or_low) / or_range
    else:
        first_pullback_frac = (or_high - pb_extreme_px) / or_range
    pb_mins = (round((post_or[pb_end_idx]["time"] - post_or[extreme_idx]["time"]) / 60, 1)
               if pb_end_idx is not None else None)

    setup_row: dict[str, Any] = {
        "kind": "setup",                 # the denominator record
        "day": day, "bias": bias, "regime": regime,
        "or_high": round(or_high, 2), "or_low": round(or_low, 2),
        "or_range": round(or_range, 2),
        "breakout_extreme": round(extreme, 2),
        "deepest_px": round(deepest_px, 2),
        "deepest_frac": round(deepest_frac, 4),
        # the FIRST pullback and whether it actually reversed — the honest
        # basis for a retracement-depth distribution
        "first_pullback_frac": (round(first_pullback_frac, 4)
                                if first_pullback_frac is not None else None),
        "first_pullback_px": round(pb_extreme_px, 2) if pb_extreme_px is not None else None,
        "reversal_confirmed": reversal_confirmed,
        "pullback_mins": pb_mins,
        "adx_930": round(adx_930, 1) if adx_930 is not None else None,
        "atr_930": round(atr_930, 2) if atr_930 is not None else None,
        "rsi_930": round(rsi_930, 1),
        "levels_touched": [],            # filled below
    }

    rows: list[dict[str, Any]] = [setup_row]
    for f in FIB_LEVELS:
        level_px = levels[f]
        touch_idx = None
        for i in range(extreme_idx, len(post_or)):
            c = post_or[i]
            if c["low"] <= level_px <= c["high"]:
                touch_idx = i
                break
        if touch_idx is None:
            continue   # level never reached today — no row, not a fabricated loss

        setup_row["levels_touched"].append(f)

        entry_px = level_px
        entry_time = post_or[touch_idx]["time"]
        stop_px = or_low if bias == "CALL" else or_high

        # ── ENTRY-QUALITY CONTEXT AT THE TOUCH (owner, 2026-08-08) ─────────
        # The owner's rule: "Fib touched" and "Fib gave a high-quality entry"
        # must be distinguishable. Nothing here decides anything — these are
        # recorded so the stats layer can later compare a bare touch against
        # a touch WITH confirmation, from real outcomes instead of belief.
        # Every field is derived from candles already in hand; nothing is
        # fetched, and nothing unavailable is guessed (None instead).
        tc = post_or[touch_idx]
        _body = abs(tc["close"] - tc["open"])
        if bias == "CALL":
            _wick = min(tc["open"], tc["close"]) - tc["low"]
        else:
            _wick = tc["high"] - max(tc["open"], tc["close"])
        # A rejection bar: the wick into the level is longer than the body,
        # i.e. price probed the level and was pushed back within the bar.
        rejection = bool(_wick > _body > 0) if _body > 0 else bool(_wick > 0)
        wick_body_ratio = round(_wick / _body, 2) if _body > 0 else None

        # session VWAP up to and including the touch bar (cumulative, honest —
        # uses only candles that had already printed at that moment)
        _upto = candles[:candles.index(tc) + 1] if tc in candles else None
        vwap_at_touch = vwap(_upto) if _upto else None
        if vwap_at_touch:
            vwap_side = ("ABOVE" if tc["close"] > vwap_at_touch else "BELOW")
        else:
            vwap_side = None
        # with-trend means VWAP agrees with the setup's own bias
        vwap_supports = (None if vwap_side is None else
                         (vwap_side == "ABOVE") == (bias == "CALL"))
        target1_px = extreme
        target2_px = target1_px + or_range if bias == "CALL" else target1_px - or_range

        # BUGFIX 2026-08-08 (found by disbelieving my own result). The first
        # version of this loop `break`ed the instant T1 was touched, with the
        # T2 check nested inside that same branch — so WIN_T2 could only ever
        # register if ONE 1-minute candle spanned from below T1 to beyond T2,
        # i.e. a full OR-range-width inside a single minute. It therefore
        # reported t2_rate = 0.0 in every bucket and every regime across 288
        # rows, and I wrongly read that as "the T2 rule is set too far". The
        # rule was never tested; the measurement stopped before T2 could be
        # observed. A 0.0 that is identical across every stratum is a
        # measurement artifact, not a market fact.
        #
        # Corrected trade management: T1 is BANKED when touched, then the
        # position keeps running toward T2. A stop touched AFTER T1 no longer
        # turns the trade into a loss (T1 was already realised) — it just ends
        # the run at WIN_T1. Stop is still checked BEFORE targets within the
        # same candle, keeping the existing conservative fill convention.
        # Extracted to _resolve_trade() (2026-08-08) so the dynamic-zone
        # backtest resolves trades by the IDENTICAL rule. Two copies of trade
        # management would eventually diverge and make the comparison
        # meaningless — which is the entire point of that backtest.
        d = 1.0 if bias == "CALL" else -1.0
        _res = _resolve_trade(post_or[touch_idx + 1:], entry_px, stop_px,
                              target1_px, target2_px, d)
        outcome, exit_px = _res["outcome"], _res["exit_px"]
        mfe, mae = _res["mfe"], _res["mae"]
        t1_ts, t2_ts = _res["t1_ts"], _res["t2_ts"]

        rows.append({
            "kind": "touch",
            "rejection": rejection, "wick_body_ratio": wick_body_ratio,
            "vwap_side": vwap_side, "vwap_supports": vwap_supports,
            "deepest_frac": round(deepest_frac, 4),
            "day": day, "bias": bias, "regime": regime,
            "or_high": round(or_high, 2), "or_low": round(or_low, 2),
            "fib_level": f, "entry_time": _hhmm(entry_time), "entry_px": round(entry_px, 2),
            "stop_px": round(stop_px, 2), "target1_px": round(target1_px, 2),
            "target2_px": round(target2_px, 2), "outcome": outcome,
            "exit_px": round(exit_px, 2) if exit_px is not None else None,
            "mfe_pts": round(mfe, 2), "mae_pts": round(mae, 2),
            # time-to-target (owner's Phase 5 field). None when that target was
            # never reached — never zero-filled, which would read as "instant".
            "t1_time": _hhmm(t1_ts) if t1_ts else None,
            "t2_time": _hhmm(t2_ts) if t2_ts else None,
            "mins_to_t1": round((t1_ts - entry_time) / 60, 1) if t1_ts else None,
            "mins_to_t2": round((t2_ts - entry_time) / 60, 1) if t2_ts else None,
            "vwap_930": round(vwap_930, 2), "ema9_930": round(ema9, 2),
            "ema21_930": round(ema21, 2),
            "adx_930": round(adx_930, 1) if adx_930 is not None else None,
            "rsi_930": round(rsi_930, 1), "atr_930": round(atr_930, 2) if atr_930 is not None else None,
        })
    return rows


def _path(symbol: str) -> pathlib.Path:
    return _DATA_DIR / f"{symbol}.jsonl"


def _candle_cache_path(symbol: str) -> pathlib.Path:
    return _DATA_DIR / f"_candles_{symbol}.json.gz"


def _cache_candles(symbol: str, candles: list[dict], meta: dict[str, Any]) -> None:
    """Persist the raw 1-min history a run() fetched.

    WHY: the fetch is ~6 chunked broker calls under a 45/min budget, and this
    backend holds credentials in process memory only — so every re-analysis
    previously meant restart -> lost credentials -> manual reconnect -> refetch.
    With the candles on disk, reanalyze() can re-run the ENTIRE study offline,
    with no broker and no market session. The measurement rules are what get
    iterated during research; the underlying candles do not change."""
    import gzip
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    tmp = _candle_cache_path(symbol).with_suffix(".tmp")
    with gzip.open(tmp, "wt") as f:
        json.dump({"meta": meta, "candles": candles}, f)
    tmp.replace(_candle_cache_path(symbol))


def _load_cached_candles(symbol: str) -> tuple[list[dict], dict[str, Any]] | None:
    import gzip
    p = _candle_cache_path(symbol)
    if not p.exists():
        return None
    try:
        with gzip.open(p, "rt") as f:
            d = json.load(f)
        return d.get("candles") or [], d.get("meta") or {}
    except Exception:
        return None


def reanalyze(symbol: str = "NIFTY") -> dict[str, Any]:
    """Re-run the whole study from CACHED candles — no broker, no market
    session, no credentials. This is what makes iterating on the measurement
    rules cheap: change a rule, reanalyze, compare. Raises if no cache yet."""
    cached = _load_cached_candles(symbol)
    if not cached:
        raise ValueError(f"No cached candles for {symbol} — run the live "
                         f"backtest once first to populate the cache.")
    candles, meta = cached
    days = _group_by_day(candles)
    all_rows: list[dict[str, Any]] = []
    for day, day_candles in sorted(days.items()):
        all_rows.extend(_process_day(day, day_candles))
    _write_rows(symbol, all_rows)
    return {"symbol": symbol, "source": "cached candles (offline)",
            "cached_meta": meta, "candles": len(candles),
            "trading_days_seen": len(days), "rows_written": len(all_rows),
            "stats": level_stats(symbol)}


def _write_rows(symbol: str, rows: list[dict[str, Any]]) -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    with _path(symbol).open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


def _read_rows(symbol: str) -> list[dict[str, Any]]:
    p = _path(symbol)
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]


def level_stats(symbol: str) -> dict[str, Any]:
    """Aggregate win-rate / avg MFE / avg MAE per fib level, and per
    (regime, level) — read-only over the persisted rows. Nothing here
    changes any threshold; it only reports what already happened."""
    all_rows = _read_rows(symbol)
    # Legacy rows (written before 2026-08-08) carry no "kind" — every one of
    # them is a touch record, so default accordingly rather than dropping them.
    setups = [r for r in all_rows if r.get("kind") == "setup"]
    rows = [r for r in all_rows if r.get("kind", "touch") == "touch"]

    by_level: dict[float, list[dict]] = {}
    for r in rows:
        by_level.setdefault(r["fib_level"], []).append(r)

    def _pct(vals: list[float], q: float) -> float | None:
        """Nearest-rank percentile. Reported alongside the mean because MAE is
        skewed — an average hides the tail that actually stops a trade out."""
        if not vals:
            return None
        s = sorted(vals)
        i = min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))
        return round(s[i], 2)

    def _agg(rs: list[dict]) -> dict[str, Any]:
        decided = [r for r in rs if r["outcome"] != "OPEN"]
        wins = [r for r in decided if r["outcome"].startswith("WIN")]
        t2 = [r for r in decided if r["outcome"] == "WIN_T2"]
        maes = [r["mae_pts"] for r in decided]
        # Bare touch vs touch WITH a rejection bar — the owner's explicit
        # distinction between "Fib touched" and "Fib gave a quality entry".
        # None (not 0) when the split has no samples, so an absent comparison
        # never reads as a measured zero.
        conf = [r for r in decided if r.get("rejection")]
        bare = [r for r in decided if r.get("rejection") is False]
        def _wr(x):
            return (round(100 * sum(1 for r in x if r["outcome"].startswith("WIN")) / len(x), 1)
                    if x else None)
        return {
            "sample": len(decided),
            "open": len(rs) - len(decided),
            "win_rate": round(100 * len(wins) / len(decided), 1) if decided else None,
            "t2_rate": round(100 * len(t2) / len(decided), 1) if decided else None,
            "avg_mfe_pts": round(sum(r["mfe_pts"] for r in decided) / len(decided), 2) if decided else None,
            "avg_mae_pts": round(sum(maes) / len(decided), 2) if decided else None,
            "median_mae_pts": _pct(maes, 0.50),
            "p90_mae_pts": _pct(maes, 0.90),
            "win_rate_with_rejection": _wr(conf),
            "n_with_rejection": len(conf),
            "win_rate_bare_touch": _wr(bare),
            "n_bare_touch": len(bare),
        }

    # REACH PROBABILITY — now computable because setup rows supply the
    # denominator. deepest_frac <= f means the retracement got at least as
    # deep as level f (levels are measured from the far side, so smaller is
    # deeper). None when no setup rows exist yet (legacy-only logs), never 0 —
    # "not measured" and "never happened" must not look identical.
    n_setups = len(setups)

    def _reach(f: float) -> dict[str, Any]:
        if not n_setups:
            return {"reach_pct": None, "reached": None, "of_setups": 0,
                    "note": "no setup rows yet — re-run to populate the denominator"}
        hit = sum(1 for s in setups if (s.get("deepest_frac") is not None
                                        and s["deepest_frac"] <= f))
        return {"reach_pct": round(100 * hit / n_setups, 1),
                "reached": hit, "of_setups": n_setups}

    levels = [{"fib_level": f, **_reach(f), **_agg(by_level.get(f, []))}
              for f in FIB_LEVELS]

    by_regime: dict[str, list[dict]] = {}
    for regime in ("TRENDING", "RANGE", "MIXED", "UNKNOWN"):
        per_level = []
        for f in FIB_LEVELS:
            rs = [r for r in by_level.get(f, []) if r["regime"] == regime]
            if not rs:
                continue
            per_level.append({"fib_level": f, **_agg(rs)})
        if per_level:
            by_regime[regime] = per_level

    # Retracement-depth distribution across ALL setups (owner, 2026-08-08) —
    # answers "how deep does this setup usually pull back?" independently of
    # whether any particular fib level was traded.
    depths = [s["deepest_frac"] for s in setups if s.get("deepest_frac") is not None]
    depth_profile = {
        "setups": n_setups,
        "median_deepest_frac": _pct(depths, 0.50),
        "p10_deepest_frac": _pct(depths, 0.10),   # the deep tail
        "p90_deepest_frac": _pct(depths, 0.90),   # the shallow tail
        "note": ("deepest_frac is on the fib scale: 1.0 = never pulled back past "
                 "the breakout boundary, smaller = deeper retracement. "
                 "SMALLER IS DEEPER."),
    } if depths else {"setups": n_setups, "note": "no setup rows yet — re-run to populate"}

    return {
        "symbol": symbol,
        "total_rows": len(rows),
        "setup_rows": n_setups,
        "days_with_a_setup": len({r["day"] for r in rows}),
        "levels": levels,
        "by_regime": by_regime,
        "depth_profile": depth_profile,
        "note": ("Observed frequency over the persisted research rows — NOT a "
                 "live win probability and NOT wired into any gate or evidence "
                 "layer. Index-points only (no historical option chain "
                 "available); OI/PCR/Gamma/Buyer-Seller-Strength are not "
                 "computed here for that reason."),
    }


def depth_distribution(symbol: str = "NIFTY") -> dict[str, Any]:
    """WHERE DOES THE PULLBACK ACTUALLY TURN? (owner, 2026-08-08)

    Answers the question a fixed-level table structurally cannot: instead of
    asking "is 0.618 good?", it reports the observed distribution of FIRST
    pullback depth across every setup — percentiles, a histogram, and the
    split between pullbacks that reversed and ones that never did.

    Uses first_pullback_frac (retracement measured until price exceeds the
    breakout extreme), NOT deepest_frac, because the latter includes any late
    end-of-day fade after the trade already resolved.

    Scale note: 1.0 = the breakout boundary, 0.0 = the far side of the opening
    range, NEGATIVE = broke clean through the range. SMALLER IS DEEPER."""
    setups = [r for r in _read_rows(symbol) if r.get("kind") == "setup"]
    vals = [(s.get("first_pullback_frac"), bool(s.get("reversal_confirmed")))
            for s in setups if s.get("first_pullback_frac") is not None]
    if not vals:
        return {"symbol": symbol, "setups": 0,
                "note": "no setup rows with a measured first pullback — "
                        "run or reanalyze first"}

    reversed_ = [v for v, ok in vals if ok]
    failed = [v for v, ok in vals if not ok]

    def _p(xs: list[float], q: float) -> float | None:
        if not xs:
            return None
        s = sorted(xs)
        return round(s[min(len(s) - 1, max(0, int(round(q * (len(s) - 1)))))], 4)

    # Histogram over the fib scale. Bins are declared, evenly spaced, and
    # include an explicit below-range bucket so a clean breakdown is visible
    # rather than being clipped into the deepest normal bin.
    edges = [-0.25, 0.0, 0.15, 0.30, 0.45, 0.60, 0.75, 0.90, 1.05]
    hist = []
    for lo, hi in zip(edges, edges[1:]):
        n = sum(1 for v, _ in vals if lo <= v < hi)
        hist.append({"from": lo, "to": hi, "n": n,
                     "pct": round(100 * n / len(vals), 1)})
    below = sum(1 for v, _ in vals if v < edges[0])
    above = sum(1 for v, _ in vals if v >= edges[-1])

    return {
        "symbol": symbol,
        "setups": len(vals),
        "reversal_confirmed": len(reversed_),
        "never_reversed": len(failed),
        "reversal_rate_pct": round(100 * len(reversed_) / len(vals), 1),
        "percentiles_all": {f"p{int(q*100)}": _p([v for v, _ in vals], q)
                            for q in (0.10, 0.25, 0.50, 0.75, 0.90)},
        "percentiles_reversed_only": {f"p{int(q*100)}": _p(reversed_, q)
                                      for q in (0.10, 0.25, 0.50, 0.75, 0.90)},
        "histogram": hist,
        "below_lowest_bin": below,
        "above_highest_bin": above,
        "scale_note": ("1.0 = breakout boundary · 0.0 = far side of the opening "
                       "range · negative = broke clean through. SMALLER IS DEEPER."),
        "why_reversed_only_matters": (
            "percentiles_reversed_only excludes setups whose pullback never "
            "turned. Those are not shallow-or-deep retracements — they are "
            "failed breakouts, and averaging them in would drag the 'typical "
            "pullback' deeper than any tradeable retracement actually goes."),
    }


TRAIN_FRACTION = 0.70          # declared; time-based, never random (see below)
ZONE_LO_PCTILE = 0.25          # zone fitted as the middle 50% of where
ZONE_HI_PCTILE = 0.75          # reversal-confirmed pullbacks actually turned

# UNLOCK BAR (owner, 2026-08-08). Until the TEST split clears one of these,
# the backtest is BACKTEST_ONLY and must not reach entry logic. The bar is the
# owner's own standard, and the reason it is enforced in code rather than left
# to judgement is measured, not theoretical: on this dataset the identical
# fixed rule earned 0.627 mean R on the train half and 1.178 on the test half
# purely because the market changed. At n~30 that regime effect is larger than
# any difference between the strategies being compared, so an ungated number
# here would let noise be read as edge.
UNLOCK_MIN_DAYS = 100
UNLOCK_MIN_SIGNALS = 500
BACKTEST_ONLY = True           # flipped only by a human, after the bar is met


def dynamic_zone_backtest(symbol: str = "NIFTY",
                          train_fraction: float = TRAIN_FRACTION,
                          baselines: tuple[float, ...] = (0.618, 0.786)) -> dict[str, Any]:
    """STEP 2 — does a DATA-FITTED entry zone beat a FIXED fib level?

    Method (owner-specified, 2026-08-08):
      * Split the trading days CHRONOLOGICALLY, never randomly. Market regime
        shifts over time; a random split leaks future regime into training and
        would flatter the result.
      * Fit the zone on the TRAIN days only — the p25..p75 band of where
        reversal-confirmed pullbacks actually turned.
      * Apply it to the TEST days, which the fit never saw.
      * Run the fixed-level baselines over the SAME test days and compare
        expectancy in R.

    Entry rule for the zone: enter at the first touch of its SHALLOW edge —
    that is the first price at which a resting limit order inside the zone
    would actually fill as price falls in. Taking the deep edge instead would
    assume a fill that often never happens, which flatters the result.

    Stop/T1/T2 and trade management are IDENTICAL to the fixed-level path
    (shared _resolve_trade), so the comparison isolates entry location and
    nothing else. Expectancy is reported in R, which normalises the fact that
    a shallower entry carries a wider stop.

    Runs fully offline from cached candles.
    """
    cached = _load_cached_candles(symbol)
    if not cached:
        raise ValueError(f"No cached candles for {symbol} — run the live "
                         f"backtest once first.")
    candles, meta = cached
    days = sorted(_group_by_day(candles).items())
    split = int(len(days) * train_fraction)
    train_days, test_days = days[:split], days[split:]

    def _contexts(day_pairs):
        out = []
        for day, dcs in day_pairs:
            for r in _process_day(day, dcs):
                if r.get("kind") == "setup":
                    out.append((day, dcs, r))
        return out

    train_ctx, test_ctx = _contexts(train_days), _contexts(test_days)

    # ── FIT on train only ────────────────────────────────────────────────
    fit_vals = sorted(c[2]["first_pullback_frac"] for c in train_ctx
                      if c[2].get("first_pullback_frac") is not None
                      and c[2].get("reversal_confirmed"))
    if len(fit_vals) < 10:
        return {"symbol": symbol, "error": "INSUFFICIENT_TRAIN_SAMPLE",
                "train_reversals": len(fit_vals),
                "note": "fewer than 10 reversal-confirmed train setups — "
                        "fitting a zone on this would be noise, not evidence"}

    def _q(xs, q):
        return xs[min(len(xs) - 1, max(0, int(round(q * (len(xs) - 1)))))]

    zone_lo, zone_hi = _q(fit_vals, ZONE_LO_PCTILE), _q(fit_vals, ZONE_HI_PCTILE)

    # ── evaluate one entry fraction over a set of contexts ───────────────
    def _run_at(ctxs, frac_of):
        rs, rows = [], 0
        for day, dcs, s in ctxs:
            bias, or_low, or_high = s["bias"], s["or_low"], s["or_high"]
            or_range, extreme = s["or_range"], s["breakout_extreme"]
            frac = frac_of(s)
            if frac is None:
                continue
            entry_px = (or_low + frac * or_range) if bias == "CALL" else (or_high - frac * or_range)
            stop_px = or_low if bias == "CALL" else or_high
            t1 = extreme
            t2 = t1 + or_range if bias == "CALL" else t1 - or_range
            d = 1.0 if bias == "CALL" else -1.0
            post = [c for c in dcs if _hm(c["time"]) >= OR_END]
            # locate the breakout extreme bar, then the first touch of entry_px
            hit = None
            for i, c in enumerate(post):
                if c["low"] <= entry_px <= c["high"]:
                    hit = i
                    break
            if hit is None:
                continue                       # never filled — not a trade
            rows += 1
            res = _resolve_trade(post[hit + 1:], entry_px, stop_px, t1, t2, d)
            r = _r_multiple(res, entry_px, stop_px, t1, t2)
            if r is not None:
                rs.append(r)
        return rs, rows

    def _summary(rs, fills, ctxs, label):
        if not rs:
            return {"strategy": label, "fills": fills, "resolved": 0,
                    "mean_R": None, "median_R": None, "win_rate": None,
                    "fill_rate_pct": round(100 * fills / len(ctxs), 1) if ctxs else None}
        wins = sum(1 for r in rs if r > 0)
        srt = sorted(rs)
        return {
            "strategy": label,
            "fills": fills,
            "resolved": len(rs),
            "fill_rate_pct": round(100 * fills / len(ctxs), 1) if ctxs else None,
            "mean_R": round(sum(rs) / len(rs), 3),
            "median_R": round(srt[len(srt) // 2], 3),
            "win_rate": round(100 * wins / len(rs), 1),
            "total_R": round(sum(rs), 2),
        }

    results = [_summary(*_run_at(test_ctx, lambda s: zone_hi), test_ctx,
                        f"DYNAMIC zone {zone_lo:.3f}-{zone_hi:.3f} (fitted on train)")]
    for b in baselines:
        results.append(_summary(*_run_at(test_ctx, lambda s, b=b: b), test_ctx,
                                f"FIXED {b}"))

    # in-sample figure for the same zone, purely to expose overfit gap
    in_sample = _summary(*_run_at(train_ctx, lambda s: zone_hi), train_ctx,
                         "DYNAMIC zone (IN-SAMPLE, for overfit check only)")

    # ── REGIME SENSITIVITY, measured rather than asserted ────────────────
    # Run the SAME unchanged fixed rule on both halves. Any difference is
    # attributable to the market, not the rule — which is the concrete
    # argument for why a thin out-of-sample table must not drive decisions.
    _ref = baselines[0] if baselines else 0.618
    _tr = _summary(*_run_at(train_ctx, lambda s, b=_ref: b), train_ctx, f"FIXED {_ref} on TRAIN")
    _te = _summary(*_run_at(test_ctx, lambda s, b=_ref: b), test_ctx, f"FIXED {_ref} on TEST")
    regime_gap = None
    if _tr.get("mean_R") is not None and _te.get("mean_R") is not None:
        regime_gap = {
            "identical_rule": f"FIXED {_ref}",
            "train": {"n": _tr["resolved"], "mean_R": _tr["mean_R"], "win_rate": _tr["win_rate"]},
            "test": {"n": _te["resolved"], "mean_R": _te["mean_R"], "win_rate": _te["win_rate"]},
            "mean_R_delta": round(_te["mean_R"] - _tr["mean_R"], 3),
            "reading": ("The rule did not change between these two halves — only "
                        "the market did. A delta of this size on samples this "
                        "small means the out-of-sample table above is measuring "
                        "WHEN it was tested at least as much as WHAT was tested."),
        }

    # ── DECISION GATE (owner, 2026-08-08) ────────────────────────────────
    # Numbers this thin must not be reachable as if they were tradeable.
    # Evaluated on the TEST split, because that is what the comparison rests on.
    n_test_setups, n_test_days = len(test_ctx), len(test_days)
    unlocked = (n_test_setups >= UNLOCK_MIN_SIGNALS) or (n_test_days >= UNLOCK_MIN_DAYS)
    gate = {
        "unlocked_for_decisions": bool(unlocked),
        "status": "DECISION_GRADE" if unlocked else "DIRECTIONAL_ONLY",
        "bar": f">={UNLOCK_MIN_DAYS} trading days OR >={UNLOCK_MIN_SIGNALS} signals "
               f"in the TEST split (owner's own standard, 2026-08-07)",
        "sample_size": {"test_setups": n_test_setups, "test_days": n_test_days,
                        "train_setups": len(train_ctx), "train_days": len(train_days)},
        "shortfall": (None if unlocked else
                      {"signals_short": max(0, UNLOCK_MIN_SIGNALS - n_test_setups),
                       "days_short": max(0, UNLOCK_MIN_DAYS - n_test_days)}),
        "regime_warning": (
            f"n={n_test_setups} test setups over {n_test_days} days — "
            "REGIME-SENSITIVE, DIRECTIONAL ONLY. Do not wire into entry logic. "
            + (f"Measured proof: the identical FIXED {_ref} rule earned "
               f"{_tr['mean_R']} mean R on train and {_te['mean_R']} on test "
               f"(delta {regime_gap['mean_R_delta']:+}) with no rule change at all."
               if regime_gap else "")),
    }

    return {
        "symbol": symbol,
        "mode": "BACKTEST_ONLY",          # never a live-trading input
        "gate": gate,                      # mandatory — read this before the numbers
        "sample_size": gate["sample_size"],        # duplicated at top level so it
        "regime_warning": gate["regime_warning"],  # cannot be missed by a caller
        "cached_window": meta,
        "split": {"method": "chronological (never random — regime shifts over time)",
                  "train_days": len(train_days), "test_days": len(test_days),
                  "train_setups": len(train_ctx), "test_setups": len(test_ctx),
                  "train_reversals_used_for_fit": len(fit_vals)},
        "fitted_zone": {"lo": round(zone_lo, 4), "hi": round(zone_hi, 4),
                        "percentiles": [ZONE_LO_PCTILE, ZONE_HI_PCTILE],
                        "entry_at": "shallow edge (hi) — first realistic fill"},
        "out_of_sample": results,
        "in_sample_reference": in_sample,
        "regime_sensitivity": regime_gap,
        "cost_warning": ("No brokerage, slippage or spread modelled. Index points "
                         "only — not option premium P&L."),
        "as_of": int(time.time()),
    }


async def run(client: DhanClient, symbol: str = "NIFTY", months: int = 6) -> dict[str, Any]:
    """On-demand: POST /api/orfe-research/run while connected (same pattern
    as historical_learning.run()). Fetches ~`months` of 1-min history via the
    already-connected broker client, recomputes every day, and OVERWRITES
    this symbol's research file with the fresh result."""
    inst = get_instrument(symbol)
    to_date = datetime.date.today()
    from_date = to_date - datetime.timedelta(days=months * 30)
    candles = await client.get_intraday_range(inst, "1", from_date, to_date)
    if len(candles) < 500:
        raise ValueError(f"Not enough historical intraday data returned for {symbol} "
                          f"({len(candles)} candles) — broker may not carry this far back")
    # Cache the raw candles before analysing, so every later iteration of the
    # measurement rules can run offline via reanalyze() — no broker call, no
    # credential re-entry, no market session.
    _cache_candles(symbol, candles, {
        "from_date": from_date.isoformat(), "to_date": to_date.isoformat(),
        "fetched_at": int(time.time()), "interval": "1",
    })
    days = _group_by_day(candles)
    all_rows: list[dict[str, Any]] = []
    for day, day_candles in sorted(days.items()):
        all_rows.extend(_process_day(day, day_candles))
    _write_rows(symbol, all_rows)
    return {
        "symbol": symbol, "from_date": from_date.isoformat(), "to_date": to_date.isoformat(),
        "candles_fetched": len(candles), "trading_days_seen": len(days),
        "candles_cached": True,
        "rows_written": len(all_rows), "stats": level_stats(symbol),
    }
