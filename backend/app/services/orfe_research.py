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
from typing import Any

from ..broker.dhan import DhanClient
from ..broker.instruments import get_instrument
from ..core.clock import IST
from ..engines.technicals import adx, atr, ema, rsi, vwap

FIB_LEVELS = (0.382, 0.5, 0.618, 0.786)
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

    rows: list[dict[str, Any]] = []
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

        entry_px = level_px
        entry_time = post_or[touch_idx]["time"]
        stop_px = or_low if bias == "CALL" else or_high
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
        d = 1.0 if bias == "CALL" else -1.0

        def _fav(c):    # favourable excursion in trade direction
            return (c["high"] - entry_px) if d > 0 else (entry_px - c["low"])

        def _adv(c):    # adverse excursion in trade direction
            return (entry_px - c["low"]) if d > 0 else (c["high"] - entry_px)

        outcome, exit_px = "OPEN", None
        mfe = mae = 0.0
        t1_hit = False
        t1_ts = t2_ts = None
        for c in post_or[touch_idx + 1:]:
            mfe = max(mfe, _fav(c))
            mae = max(mae, _adv(c))
            hit_stop = (c["low"] <= stop_px) if d > 0 else (c["high"] >= stop_px)
            hit_t1 = (c["high"] >= target1_px) if d > 0 else (c["low"] <= target1_px)
            hit_t2 = (c["high"] >= target2_px) if d > 0 else (c["low"] <= target2_px)

            if not t1_hit:
                if hit_stop:                      # conservative: stop fills first
                    outcome, exit_px = "LOSS", stop_px
                    break
                if hit_t1:
                    t1_hit, t1_ts = True, c["time"]
                    outcome, exit_px = "WIN_T1", target1_px
                    if hit_t2:                    # same candle reached both
                        outcome, exit_px, t2_ts = "WIN_T2", target2_px, c["time"]
                        break
                    continue                      # keep running toward T2
            else:
                if hit_t2:
                    outcome, exit_px, t2_ts = "WIN_T2", target2_px, c["time"]
                    break
                if hit_stop:
                    break                         # T1 already banked — stays WIN_T1

        rows.append({
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
    rows = _read_rows(symbol)
    by_level: dict[float, list[dict]] = {}
    for r in rows:
        by_level.setdefault(r["fib_level"], []).append(r)

    def _agg(rs: list[dict]) -> dict[str, Any]:
        decided = [r for r in rs if r["outcome"] != "OPEN"]
        wins = [r for r in decided if r["outcome"].startswith("WIN")]
        t2 = [r for r in decided if r["outcome"] == "WIN_T2"]
        return {
            "sample": len(decided),
            "open": len(rs) - len(decided),
            "win_rate": round(100 * len(wins) / len(decided), 1) if decided else None,
            "t2_rate": round(100 * len(t2) / len(decided), 1) if decided else None,
            "avg_mfe_pts": round(sum(r["mfe_pts"] for r in decided) / len(decided), 2) if decided else None,
            "avg_mae_pts": round(sum(r["mae_pts"] for r in decided) / len(decided), 2) if decided else None,
        }

    levels = [{"fib_level": f, **_agg(by_level.get(f, []))} for f in FIB_LEVELS]

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

    return {
        "symbol": symbol,
        "total_rows": len(rows),
        "days_with_a_setup": len({r["day"] for r in rows}),
        "levels": levels,
        "by_regime": by_regime,
        "note": ("Observed frequency over the persisted research rows — NOT a "
                 "live win probability and NOT wired into any gate or evidence "
                 "layer. Index-points only (no historical option chain "
                 "available); OI/PCR/Gamma/Buyer-Seller-Strength are not "
                 "computed here for that reason."),
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
    days = _group_by_day(candles)
    all_rows: list[dict[str, Any]] = []
    for day, day_candles in sorted(days.items()):
        all_rows.extend(_process_day(day, day_candles))
    _write_rows(symbol, all_rows)
    return {
        "symbol": symbol, "from_date": from_date.isoformat(), "to_date": to_date.isoformat(),
        "candles_fetched": len(candles), "trading_days_seen": len(days),
        "rows_written": len(all_rows), "stats": level_stats(symbol),
    }
