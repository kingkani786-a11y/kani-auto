"""ENTRY EVIDENCE BOARD — where price is now, and what history says about it.

Owner ask (2026-08-10): "எந்த அடிப்படையில entry வந்தாலும் உடனே முன்னாடி
dashboard-ல தெரியுற மாதிரி" — show the entry evidence up front, live, on
whatever basis it arises (Fibonacci, candle pattern, database).

WHAT THIS IS. A join between two things that already exist separately:
  * LIVE  — today's opening range and where spot sits on its fib ladder,
            computed from state.candles (already fetched; no broker call).
  * PAST  — the 1,230-day / 894-setup NIFTY study already cached on disk
            (orfe_research), which knows how often price reaches each level
            and what happened after it did.

WHAT THIS IS NOT, and cannot become:
  * NOT a BUY/SELL call, not a signal, not a second decision surface. The
    Hero card (TradeNowCard) remains the ONLY decision surface — Rule 11,
    "One Hero -> One Decision". This board explains and locates; it never
    verdicts.
  * NOT a Kill Switch bypass. It touches no gate, no threshold, no weight.
    The owner asked for the Kill Switch to be removed so data would flow;
    the honest answer is that the Kill Switch never blocked data (proven by
    the 2026-08-10 continuity test — radar, MTF, evidence and premium panels
    all kept running while the gate was shut). What was actually missing was
    this: the evidence, assembled in one place, readable at a glance.
  * NOT a promotion of any level. The historical study's own verdict stands:
    no fib level is validated, `preferred_level = NONE`. Numbers here are
    reported WITH their sample size and confidence interval so a thin cell
    can never read like a strong one.

HONEST SCOPE. Historical figures are index-point outcomes on NIFTY opening-
range setups, no costs modelled, and explicitly NOT option-premium P&L.
Where today's session does not present a setup (no opening range, no
breakout), the board says so rather than inventing a level.
"""
from __future__ import annotations

import time
from typing import Any

from ..core.clock import IST
from ..engines import candles as candle_eng
from ..engines import supertrend
from ..engines.technicals import atr, rsi, vwap
from . import orfe_research as orfe


def _today_candles() -> list[dict]:
    """Today's 1-min candles from live state. No fetch — reads what the AI
    cycle already pulled."""
    from ..core.state import state
    import datetime
    cs = list(state.candles or [])
    if not cs:
        return []
    today = datetime.datetime.now(IST).strftime("%Y-%m-%d")
    return [c for c in cs if orfe._day_key(c["time"]) == today]


def board(symbol: str = "NIFTY") -> dict[str, Any]:
    """The whole board. Never raises — a missing piece is reported as
    unavailable with its reason, never guessed."""
    out: dict[str, Any] = {
        "symbol": symbol,
        "kind": "EVIDENCE_ONLY",
        "as_of": int(time.time()),
        "note": ("Evidence and location only — never a BUY/SELL call. The Hero "
                 "card remains the only decision surface. Historical figures are "
                 "index points on opening-range setups; no costs modelled; not "
                 "option-premium P&L."),
    }

    cs = _today_candles()
    if len(cs) < orfe.MIN_OR_CANDLES:
        out["live"] = {"available": False,
                       "reason": f"only {len(cs)} candles today — the 09:15-09:30 "
                                 f"opening range needs {orfe.MIN_OR_CANDLES}"}
        out["historical"] = _historical(symbol)
        return out

    cs = sorted(cs, key=lambda c: c["time"])
    or_c = [c for c in cs if orfe.OR_START <= orfe._hm(c["time"]) < orfe.OR_END]
    if len(or_c) < orfe.MIN_OR_CANDLES:
        out["live"] = {"available": False,
                       "reason": "opening range window incomplete for today"}
        out["historical"] = _historical(symbol)
        return out

    or_high = max(c["high"] for c in or_c)
    or_low = min(c["low"] for c in or_c)
    or_range = or_high - or_low
    if or_range <= 0:
        out["live"] = {"available": False, "reason": "zero-width opening range"}
        out["historical"] = _historical(symbol)
        return out

    spot = cs[-1]["close"]
    post = [c for c in cs if orfe._hm(c["time"]) >= orfe.OR_END]

    # Direction of the day's breakout, by the SAME rule the study used, so the
    # live read and the historical stats describe the same thing.
    bias = None
    extreme = None
    for c in post:
        if c["close"] > or_high:
            bias, extreme = "CALL", c["high"]
            break
        if c["close"] < or_low:
            bias, extreme = "PUT", c["low"]
            break
    if bias:
        for c in post:
            if bias == "CALL":
                extreme = max(extreme, c["high"])
            else:
                extreme = min(extreme, c["low"])

    levels = ({f: or_low + f * or_range for f in orfe.FIB_LEVELS} if bias == "CALL"
              else {f: or_high - f * or_range for f in orfe.FIB_LEVELS}
              if bias == "PUT" else {})

    # Where is spot on the ladder RIGHT NOW?
    pos_frac = None
    if bias == "CALL":
        pos_frac = (spot - or_low) / or_range
    elif bias == "PUT":
        pos_frac = (or_high - spot) / or_range

    # Live confirmation context at the CURRENT bar — same functions the study
    # used at its touch bars, so "rejection" means the same thing in both.
    closes = [c["close"] for c in cs]
    vw = vwap(cs)
    a = atr(cs, 14) if len(cs) >= 2 else None
    st = supertrend.analyze(cs)
    cd = candle_eng.analyze(cs, atr=(a or 0.0))
    last = cs[-1]
    body = abs(last["close"] - last["open"])
    wick = (min(last["open"], last["close"]) - last["low"]) if bias != "PUT" else \
           (last["high"] - max(last["open"], last["close"]))
    rejection = bool(wick > body > 0) if body > 0 else bool(wick > 0)

    st_dir = st.get("direction") if st.get("ready") else None
    out["live"] = {
        "available": True,
        "spot": round(spot, 2),
        "opening_range": {"high": round(or_high, 2), "low": round(or_low, 2),
                          "range": round(or_range, 2)},
        "bias": bias or "NO_BREAKOUT_YET",
        "breakout_extreme": round(extreme, 2) if extreme is not None else None,
        "position_on_ladder": round(pos_frac, 4) if pos_frac is not None else None,
        "ladder_note": ("1.0 = breakout boundary, 0.0 = far side of the range, "
                        "SMALLER IS DEEPER"),
        "fib_levels": {str(f): round(p, 2) for f, p in levels.items()},
        "confirmation_now": {
            "rejection_bar": rejection,
            "vwap": round(vw, 2) if vw else None,
            "vwap_supports": (None if not vw or not bias else
                              (spot > vw) == (bias == "CALL")),
            "rsi": round(rsi(closes, 14), 1) if len(closes) >= 15 else None,
            "atr": round(a, 2) if a else None,
            "supertrend": st_dir,
            "supertrend_agrees": (None if not st_dir or not bias else
                                  (st_dir == "BULLISH") == (bias == "CALL")),
            "candle_patterns": [p.get("name") for p in (cd.get("patterns") or [])],
        },
    }

    # The next level price would reach if it keeps retracing, and what the
    # study observed AT that level. This is the "entry evidence" the owner
    # wants surfaced before the move, not after.
    if bias and pos_frac is not None:
        deeper = [f for f in sorted(orfe.FIB_LEVELS, reverse=True) if f < pos_frac]
        nxt = deeper[0] if deeper else None
        out["live"]["next_level_below"] = nxt
        out["live"]["next_level_price"] = round(levels[nxt], 2) if nxt else None

    out["historical"] = _historical(symbol)
    return out


def _historical(symbol: str) -> dict[str, Any]:
    """The cached study, trimmed to what a trader reads at a glance. Every
    figure carries its sample size; the study's own gate/verdict is passed
    through unchanged so this can never look more certain than it is."""
    try:
        # fib_level_selector's overall.by_level is the ONE place mean_R/
        # median_R/MAE-percentiles/rejection-split are computed together
        # (_level_row_stats) — level_stats() predates that and has no R-
        # multiple math at all. Using the wrong one silently renders every
        # mean_R as None, which looks like missing data rather than a wiring
        # bug — caught by testing this against real cached rows before commit.
        sel = orfe.fib_level_selector(symbol)
        tm = orfe.transition_matrix(symbol)
    except Exception as e:
        return {"available": False, "reason": f"study not available: {e}"}

    rows = []
    tmap = {t["from"]: t for t in (tm.get("transitions") or [])}
    omap = {o["fib_level"]: o for o in (tm.get("outcomes_given_touch") or [])}
    for L in (sel.get("overall", {}).get("by_level") or []):
        f = L["fib_level"]
        o = omap.get(f, {})
        t = tmap.get(f, {})
        rows.append({
            "fib_level": f,
            "reach_pct": L.get("reach_pct"),
            "t1_given_touch": (o.get("p_t1_given_touch") or {}).get("pct"),
            "t1_ci": [(o.get("p_t1_given_touch") or {}).get("lo"),
                     (o.get("p_t1_given_touch") or {}).get("hi")],
            "stop_given_touch": (o.get("p_stop_given_touch") or {}).get("pct"),
            "p_goes_deeper": (t.get("p_deeper_given_reached") or {}).get("pct"),
            "n": L.get("sample"),
            "mean_R": L.get("mean_R"),
            "median_R": L.get("median_R"),
            "median_mae_pts": L.get("median_mae_pts"),
            "mean_R_with_rejection": (L.get("by_confirmation") or {}).get(
                "rejection", {}).get("mean_R"),
            "n_with_rejection": (L.get("by_confirmation") or {}).get(
                "rejection", {}).get("n"),
        })

    return {
        "available": True,
        "setups_studied": sel.get("sample_size", {}).get("train_setups", 0)
                         + sel.get("sample_size", {}).get("test_setups", 0),
        "by_level": rows,
        "verdict": {
            "preferred_level": None,
            "why": ("No fib level is validated. Win rate tracks R:R almost "
                    "perfectly inversely, and a data-fitted zone LOST to a plain "
                    "fixed level out-of-sample — so a high win rate at a shallow "
                    "level is geometry, not edge. Read mean_R with its n, and "
                    "treat any single level as a candidate only."),
            "gate": "BACKTEST_ONLY — historical evidence, not a live entry rule",
        },
    }
