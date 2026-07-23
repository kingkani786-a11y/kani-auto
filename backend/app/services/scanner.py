"""Trade Scanner + Watchlist AI.

Every 60s, batch-quotes the index universe and every watchlist symbol,
scores momentum / volume surge / OI shift, ranks opportunities, and fires
alerts on breakouts, breakdowns, volume surges and OI shifts.
"""
from __future__ import annotations

import logging
import time
from collections import defaultdict, deque

from ..broker.instruments import get_instrument
from . import alerts, market_session_manager

log = logging.getLogger("scanner")

results: list[dict] = []
_hist: dict[str, deque] = defaultdict(lambda: deque(maxlen=30))   # symbol -> recent quotes
_alerted: dict[str, float] = {}                                   # de-dup: key -> ts
COOLDOWN = 600.0


def _should_alert(key: str) -> bool:
    now = time.time()
    if now - _alerted.get(key, 0) > COOLDOWN:
        _alerted[key] = now
        return True
    return False


async def scan(client, watchlist: list[str], market_type: str = "INDEX") -> list[dict]:
    """One scanner pass. Returns ranked opportunities (also kept in module state).

    market_type selects the candidate universe (V7 Market Independence Phase A,
    owner 2026-07-23) — this used to be hardcoded to INDEX, which is exactly why
    MCX never got auto-selected even though it was fully registered: the ranking
    that decides "what's the active symbol" simply never considered it."""
    symbols = market_session_manager.candidates_for(market_type)
    symbols += [s for s in watchlist if s not in symbols]

    # group by segment for batch quoting
    by_seg: dict[str, list] = defaultdict(list)
    insts = {}
    for s in symbols:
        try:
            inst = get_instrument(s)
        except ValueError:
            continue
        if inst.security_id == 0:
            continue
        by_seg[inst.segment].append(inst.security_id)
        insts[(inst.segment, str(inst.security_id))] = inst

    ranked: list[dict] = []
    for seg, ids in by_seg.items():
        try:
            quotes = await client.get_quotes_batch(seg, ids)
        except Exception as e:
            log.warning("scanner batch failed for %s: %s", seg, e)
            continue
        for sid, q in quotes.items():
            inst = insts.get((seg, sid))
            if not inst or not isinstance(q, dict):
                continue
            ltp = float(q.get("last_price") or 0)
            if ltp <= 0:
                continue
            ohlc = q.get("ohlc") or {}
            day_open = float(ohlc.get("open") or ltp)
            day_high = float(ohlc.get("high") or ltp)
            day_low = float(ohlc.get("low") or ltp)
            vol = float(q.get("volume") or 0)
            oi = float(q.get("oi") or 0)

            hist = _hist[inst.symbol]
            prev = hist[-1] if hist else {"ltp": ltp, "vol": vol, "oi": oi, "ts": time.time()}
            hist.append({"ltp": ltp, "vol": vol, "oi": oi, "ts": time.time()})

            chg_pct = (ltp / day_open - 1) * 100 if day_open else 0.0
            # volume surge: last-minute volume delta vs recent average delta
            deltas = [hist[i]["vol"] - hist[i - 1]["vol"] for i in range(1, len(hist))]
            recent_d = deltas[-1] if deltas else 0
            avg_d = (sum(deltas) / len(deltas)) if deltas else 0
            vol_surge = bool(avg_d > 0 and recent_d > 2.5 * avg_d)
            oi_shift_pct = ((oi / prev["oi"]) - 1) * 100 if prev["oi"] else 0.0

            near_high = day_high > 0 and (day_high - ltp) / day_high < 0.0015
            near_low = day_low > 0 and (ltp - day_low) / day_low < 0.0015
            breakout = near_high and chg_pct > 0.3
            breakdown = near_low and chg_pct < -0.3

            score = (abs(chg_pct) * 24 + (25 if vol_surge else 0)
                     + min(abs(oi_shift_pct) * 8, 20) + (15 if (breakout or breakdown) else 0))
            score = round(min(score, 100), 1)
            day_range = max(day_high - day_low, ltp * 0.001)
            # Opportunity-ranking extras: rough but honest single-quote estimates
            prob = round(min(85.0, 45 + score * 0.35 + (8 if (breakout or breakdown) else 0)), 1)
            risk_score = round(min(100.0, (day_range / ltp) * 100 * 30
                                   + (25 if vol_surge else 0)), 1)
            expected_reward = round(day_range * 0.6, 2)   # ~0.6x day range continuation
            ranked.append({
                "symbol": inst.symbol,
                "market_type": inst.market_type,
                "ltp": ltp,
                "change_pct": round(chg_pct, 2),
                "volume_surge": vol_surge,
                "oi_shift_pct": round(oi_shift_pct, 2),
                "breakout": breakout,
                "breakdown": breakdown,
                "near_high": near_high,
                "near_low": near_low,
                "score": score,
                "probability_pct": prob,
                "risk_score": risk_score,
                "expected_reward": expected_reward,
                "bias": "BULL" if chg_pct > 0 else "BEAR",
            })

            # ---- Watchlist AI alerts ----
            if breakout and _should_alert(f"bo:{inst.symbol}"):
                await alerts.send("SCANNER", f"{inst.symbol} breakout",
                                  f"Trading at day high {ltp:,.1f} ({chg_pct:+.2f}%)", inst.symbol)
            if breakdown and _should_alert(f"bd:{inst.symbol}"):
                await alerts.send("SCANNER", f"{inst.symbol} breakdown",
                                  f"Trading at day low {ltp:,.1f} ({chg_pct:+.2f}%)", inst.symbol)
            if vol_surge and _should_alert(f"vs:{inst.symbol}"):
                await alerts.send("SCANNER", f"{inst.symbol} volume surge",
                                  f"Volume expanding sharply at {ltp:,.1f}", inst.symbol)
            if abs(oi_shift_pct) > 4 and _should_alert(f"oi:{inst.symbol}"):
                await alerts.send("SCANNER", f"{inst.symbol} OI shift",
                                  f"OI moved {oi_shift_pct:+.1f}% — positioning change", inst.symbol)

    ranked.sort(key=lambda r: r["score"], reverse=True)
    results.clear()
    results.extend(ranked[:40])
    return results


def breadth() -> dict:
    """Market Breadth from the scanned universe (indices + watchlist)."""
    if not results:
        return {"advances": 0, "declines": 0, "unchanged": 0,
                "new_highs": 0, "new_lows": 0, "ratio": None, "note": "Scanner warming up"}
    adv = sum(1 for r in results if r["change_pct"] > 0.05)
    dec = sum(1 for r in results if r["change_pct"] < -0.05)
    unch = len(results) - adv - dec
    nh = sum(1 for r in results if r.get("near_high"))
    nl = sum(1 for r in results if r.get("near_low"))
    return {
        "advances": adv, "declines": dec, "unchanged": unch,
        "new_highs": nh, "new_lows": nl,
        "ratio": round(adv / dec, 2) if dec else None,
        "bias": "BULLISH" if adv > dec * 1.5 else "BEARISH" if dec > adv * 1.5 else "NEUTRAL",
        "universe": len(results),
    }
