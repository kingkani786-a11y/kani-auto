"""Supertrend Engine — the one fully-absent trend-evidence layer at the
2026-08-07 Master Architecture Audit (docs/MASTER_ARCHITECTURE_AUDIT.md §6).

The audit checked all 61 engines for every evidence layer the owner listed.
Everything on that list already existed somewhere EXCEPT Supertrend, News,
a dedicated Gap engine, Auction/CAS behaviour, and a macro calendar. Of those
five, this is the only one buildable from data the platform already has — the
other four are blocked on an external provider, a live CAS-window observation,
or a source that does not exist yet. So this is the one gap that closes today.

WHAT IT IS: the standard ATR-band trend follower. A band is placed ATR*MULT
either side of the HL2 midpoint; the band ratchets in the trend's favour and
never loosens against it; a close through the active band flips the direction.
That ratchet is the whole point — it is why Supertrend holds a trend that EMA
crossovers whipsaw out of, which is exactly the complaint that motivated it.

WHY IT IS NOT REDUNDANT WITH THE EXISTING trend LAYER. technicals.trend_engine
reads EMA20/50/200 stack + VWAP + ADX — all *level* comparisons, all
mean-reverting by construction. Supertrend is a *stateful ratchet*: it carries
the previous bar's band forward and can only tighten. On the same candles the
two genuinely disagree at turns (Supertrend flips late but holds; EMA stack
flips early but chops), which is precisely why it is worth having as a
SEPARATE, VISIBLE row rather than blended into the existing trend score.

WHAT IT DELIBERATELY DOES NOT DO — identical contract to candles.py:

  1. **No win rate, no probability.** A flip is a fact about price and ATR,
     not a forecast. The owner's own RVE-001/002 research (research/ on
     v8-dev) showed features with r up to -0.95 collapsing to ~0pp once DTE
     was held fixed. Attaching a hit-rate here would repeat that mistake.
  2. **It changes no score, no threshold, and no gate.** Not in WEIGHTS, not
     in MANDATORY, never appended to `vetoes`. Observational only. Promoting
     it into the composite is a separate change needing its own evidence and
     its own approval — the same queue candles.py is still in.
  3. **`bars_in_trend` is reported, never interpreted.** How long a trend has
     held is a measured fact; whether "long" means continuation or exhaustion
     is exactly the kind of claim that needs the black box, not a docstring.

DECLARED thresholds — stated conventions, NOT fitted or backtested values.
ATR_PERIOD/MULTIPLIER are the near-universal published defaults (10/3.0), used
here because a default nobody tuned is more honest than a number invented to
look validated. Evidence tunes them later, never a guess now.
"""
from __future__ import annotations

from typing import Any

THRESHOLD_REGISTRY = {
    "ATR_PERIOD": (10, "bars in the ATR used for band width — published default, not fitted"),
    "MULTIPLIER": (3.0, "band sits ATR * this either side of HL2 — published default, not fitted"),
    "MIN_CANDLES": (15, "bars required before any direction is reported (ATR_PERIOD + headroom)"),
}
ATR_PERIOD = 10
MULTIPLIER = 3.0
MIN_CANDLES = 15

_UNAVAILABLE = {
    "ready": False, "direction": "NONE", "supertrend": None,
    "flipped": False, "bars_in_trend": 0, "distance_pts": None,
    "distance_atr": None, "summary": "insufficient candles",
}


def _wilder_atr_series(candles: list[dict], period: int) -> list[float]:
    """Wilder-smoothed ATR, one value per bar (index-aligned to `candles`).

    technicals.atr() returns only the final scalar; Supertrend needs the ATR
    AT EVERY BAR to build its bands historically, so the series is computed
    here rather than reaching into that function. Same Wilder recursion, so
    the last element agrees with technicals.atr(candles, period).
    """
    n = len(candles)
    out = [0.0] * n
    if n < 2:
        return out
    trs: list[float] = []
    for prev, cur in zip(candles, candles[1:]):
        trs.append(max(
            cur["high"] - cur["low"],
            abs(cur["high"] - prev["close"]),
            abs(cur["low"] - prev["close"]),
        ))
    p = min(period, len(trs))
    if p <= 0:
        return out
    a = sum(trs[:p]) / p
    out[p] = a                       # trs[i] belongs to candles[i+1]
    for i in range(p, len(trs)):
        a = (a * (p - 1) + trs[i]) / p
        out[i + 1] = a
    return out


def analyze(candles: list[dict], atr_period: int = ATR_PERIOD,
            multiplier: float = MULTIPLIER) -> dict[str, Any]:
    """Compute Supertrend over already-fetched candles. Pure derivation — no
    broker call, no new data source, no extra API cost. Never raises on thin
    or malformed input; returns the honest `ready: False` shape instead, the
    same convention candles.py uses."""
    if not candles or len(candles) < MIN_CANDLES:
        return dict(_UNAVAILABLE)

    atrs = _wilder_atr_series(candles, atr_period)
    start = min(atr_period, len(candles) - 1)
    if atrs[start] <= 0:
        return dict(_UNAVAILABLE)

    direction = 1                    # +1 uptrend (line below price), -1 downtrend
    final_upper = final_lower = 0.0
    st = 0.0
    bars_in_trend = 0
    flipped = False

    for i in range(start, len(candles)):
        c = candles[i]
        atr_v = atrs[i]
        if atr_v <= 0:
            continue
        hl2 = (c["high"] + c["low"]) / 2.0
        basic_upper = hl2 + multiplier * atr_v
        basic_lower = hl2 - multiplier * atr_v
        prev_close = candles[i - 1]["close"]

        # The ratchet: a band may only tighten toward price while it is the
        # active side. It loosens ONLY after price closes through it (which is
        # what the flip below detects). Without this the bands would breathe
        # with every ATR tick and Supertrend would be just another envelope.
        if i == start:
            final_upper, final_lower = basic_upper, basic_lower
        else:
            final_upper = (basic_upper if basic_upper < final_upper or prev_close > final_upper
                           else final_upper)
            final_lower = (basic_lower if basic_lower > final_lower or prev_close < final_lower
                           else final_lower)

        prev_direction = direction
        if direction == 1 and c["close"] < final_lower:
            direction = -1
        elif direction == -1 and c["close"] > final_upper:
            direction = 1

        st = final_lower if direction == 1 else final_upper
        flipped = (direction != prev_direction) and i > start
        bars_in_trend = 1 if flipped or i == start else bars_in_trend + 1

    last_close = candles[-1]["close"]
    last_atr = atrs[-1] or 0.0
    distance_pts = last_close - st
    trend = "BULLISH" if direction == 1 else "BEARISH"
    return {
        "ready": True,
        "direction": trend,
        "supertrend": round(st, 2),
        "flipped": bool(flipped),
        "bars_in_trend": int(bars_in_trend),
        "distance_pts": round(distance_pts, 2),
        "distance_atr": round(distance_pts / last_atr, 2) if last_atr > 0 else None,
        "atr_period": atr_period,
        "multiplier": multiplier,
        "summary": (f"Supertrend {trend} at {st:.2f}"
                    + (" — FLIPPED on the last bar" if flipped
                       else f", held {bars_in_trend} bars")),
        "note": ("Observational trend-following state from price and ATR only. "
                 "No win rate and no probability attached — a flip is a fact "
                 "about price, not a forecast. Not in the decision composite: "
                 "this layer cannot move the score, flip a confirmation count, "
                 "or open/close the gate."),
    }
