"""V31 MODE-1 — Historical Learning Engine (KNOWLEDGE, not experience).

Teaches the AI from ~3 years of daily OHLC via the broker's historical API,
kept STRICTLY SEPARATE from live validation:

    Historical backtest  →  AI KNOWLEDGE   (this module; labelled HISTORICAL)
    Live decisions       →  AI EXPERIENCE  (audit tracker; Validated x/100)

HONEST SCOPE: Dhan provides historical candles for the UNDERLYING only — no
historical option chains — so this engine learns SETUP-level directional edge
(gap / trend / range / breakout day-types and their follow-through), never
premium or strike behaviour. Option-level history would need an external
EOD-bhavcopy data source the user would have to add.

Cost: ONE daily-candles call per index per run (5 calls total, on demand).
"""
from __future__ import annotations

import logging
import time
from datetime import date, timedelta
from typing import Any

from ..broker.instruments import INSTRUMENTS, get_instrument

log = logging.getLogger(__name__)

_INDICES = ["NIFTY", "BANKNIFTY", "FINNIFTY", "MIDCPNIFTY", "SENSEX"]
YEARS = 5            # V31.1 Layer-1: 5yr daily history (young indices give what they have)
_DOW = ["Mon", "Tue", "Wed", "Thu", "Fri"]
report: dict[str, Any] = {"ready": False,
                          "note": "Run POST /api/historical-learning/run while connected."}
# V32 Layer-6 — per-day feature vectors for "which historical day does today
# resemble?" (kept in memory after each run; rebuilt nightly)
_day_features: dict[str, list[dict[str, Any]]] = {}
_last_ref: dict[str, dict[str, float]] = {}


def similar_days(symbol: str, gap: float, day_ret: float, range_atr: float,
                 prev_ret: float, k: int = 5) -> dict[str, Any] | None:
    """V32 Layer-6 — nearest historical days by day-shape features. HISTORICAL
    analogue, not a prediction; similarity is feature distance, nothing more."""
    feats = _day_features.get(symbol)
    if not feats or len(feats) < 60:
        return None
    import math as _m
    # scale dims by rough spreads so no single feature dominates
    def dist(f):
        return _m.sqrt(((f["gap"] - gap) / 0.5) ** 2 + ((f["day_ret"] - day_ret) / 0.8) ** 2
                       + ((f["range_atr"] - range_atr) / 0.6) ** 2 + ((f["prev_ret"] - prev_ret) / 0.8) ** 2)
    ranked = sorted(feats, key=dist)[:k]
    d0 = dist(ranked[0])
    ups = sum(1 for f in ranked if f["next_ret"] > 0)
    return {
        "most_similar_date": ranked[0]["date"], "setup_that_day": ranked[0]["setup"],
        "similarity_pct": round(max(5.0, min(97.0, 100.0 / (1.0 + d0))), 0),
        "sample": k,
        "next_day_up_pct": round(ups / k * 100, 0),
        "avg_next_day_ret_pct": round(sum(f["next_ret"] for f in ranked) / k, 2),
        "matches": [{"date": f["date"], "setup": f["setup"],
                     "next_ret_pct": round(f["next_ret"], 2)} for f in ranked],
        "note": "HISTORICAL analogue days by shape (gap/return/range/prev-day) — "
                "context, never a prediction.",
    }


def _universe() -> list[str]:
    """Indices + resolved commodities + watchlist stocks (never unresolved ids)."""
    from ..core.state import state
    syms = list(_INDICES)
    for s, inst in INSTRUMENTS.items():
        if inst.market_type == "COMMODITY":
            syms.append(s)               # get_instrument applies runtime id overrides
    syms += [w for w in (state.watchlist or []) if w not in syms]
    return syms


def _classify(prev_close: float, o: float, h: float, l: float, c: float,
              atr: float, hh20: float, ll20: float) -> tuple[str, int]:
    """Day-type + directional bias (+1/-1/0) from plain OHLC facts."""
    gap = (o / prev_close - 1) * 100 if prev_close else 0.0
    rng = max(h - l, 1e-9)
    pos = (c - l) / rng
    if gap >= 0.3:
        return "GAP_UP", 1
    if gap <= -0.3:
        return "GAP_DOWN", -1
    if c > hh20:
        return "BREAKOUT", 1
    if c < ll20:
        return "BREAKDOWN", -1
    if rng > 1.2 * atr and pos > 0.7 and c > o:
        return "TREND_UP", 1
    if rng > 1.2 * atr and pos < 0.3 and c < o:
        return "TREND_DOWN", -1
    return "RANGE", 0


async def run(client) -> dict[str, Any]:
    global report
    t0 = time.time()
    today = date.today()
    frm = (today - timedelta(days=365 * YEARS + 30)).isoformat()
    setups: dict[str, dict[str, Any]] = {}
    vol_split: dict[str, dict[str, Any]] = {}      # V31.1 Layer-4: HIGH_VOL / LOW_VOL
    dow: dict[str, dict[str, Any]] = {}            # V31.1 Layer-3 slice: day-of-week
    per_symbol: dict[str, dict[str, Any]] = {}
    total_days = 0

    for sym in _universe():
        inst = get_instrument(sym)
        if inst.security_id == 0:
            continue
        try:
            candles = await client.get_daily_candles(inst, frm, today.isoformat())
        except Exception as e:
            log.warning("historical fetch failed for %s: %s", sym, e)
            continue
        if len(candles) < 40:
            continue
        wins = n = 0
        _feats: list[dict[str, Any]] = []
        for i in range(21, len(candles) - 1):
            win20 = candles[i - 20:i]
            atr = sum(x["high"] - x["low"] for x in win20) / 20
            hh20 = max(x["high"] for x in win20)
            ll20 = min(x["low"] for x in win20)
            cd, nd = candles[i], candles[i + 1]
            setup, bias = _classify(candles[i - 1]["close"], cd["open"], cd["high"],
                                    cd["low"], cd["close"], atr, hh20, ll20)
            nxt_ret = (nd["close"] / cd["close"] - 1) * 100 if cd["close"] else 0.0
            s = setups.setdefault(setup, {"count": 0, "follow": 0, "sum_ret": 0.0})
            s["count"] += 1
            s["sum_ret"] += nxt_ret * (bias if bias else 1)
            hitf = bias and (nxt_ret > 0) == (bias > 0)
            if hitf:
                s["follow"] += 1
                wins += 1
            if bias:
                n += 1
            total_days += 1
            # Layer-4: same setup stats split by volatility regime (range vs ATR)
            if bias:
                vkey = f"{setup}|{'HIGH_VOL' if (cd['high'] - cd['low']) > 1.3 * atr else 'LOW_VOL'}"
                v = vol_split.setdefault(vkey, {"count": 0, "follow": 0})
                v["count"] += 1
                v["follow"] += 1 if hitf else 0
            # Layer-3 slice: directional follow-through by day of week
            try:
                import datetime as _dt2
                _wd = _dt2.date.fromtimestamp(cd["time"]).weekday() if cd.get("time", 0) > 10_000 else None
            except Exception:
                _wd = None
            if bias and _wd is not None and _wd < 5:
                dw = dow.setdefault(_DOW[_wd], {"count": 0, "follow": 0})
                dw["count"] += 1
                dw["follow"] += 1 if hitf else 0
            # V32 Layer-6 — day-shape feature vector for similarity lookups
            try:
                import datetime as _dt3
                _dstr = _dt3.date.fromtimestamp(cd["time"]).isoformat() if cd.get("time", 0) > 10_000 else str(i)
            except Exception:
                _dstr = str(i)
            _prev_ret = ((candles[i - 1]["close"] / candles[i - 2]["close"] - 1) * 100
                         if candles[i - 2]["close"] else 0.0)
            _feats.append({
                "date": _dstr, "setup": setup,
                "gap": round((cd["open"] / candles[i - 1]["close"] - 1) * 100, 3) if candles[i - 1]["close"] else 0.0,
                "day_ret": round((cd["close"] / candles[i - 1]["close"] - 1) * 100, 3) if candles[i - 1]["close"] else 0.0,
                "range_atr": round((cd["high"] - cd["low"]) / atr, 3) if atr else 1.0,
                "prev_ret": round(_prev_ret, 3),
                "next_ret": round(nxt_ret, 3),
            })
        per_symbol[sym] = {"days": len(candles), "directional_days": n,
                           "follow_through_pct": round(wins / n * 100, 1) if n else None}
        _day_features[sym] = _feats
        _w20 = candles[-20:]
        _last_ref[sym] = {"prev_close": candles[-1]["close"],
                          "atr": sum(x["high"] - x["low"] for x in _w20) / len(_w20)}

    table = {}
    for k, s in setups.items():
        directional = k != "RANGE"
        table[k] = {
            "count": s["count"],
            "follow_through_pct": round(s["follow"] / s["count"] * 100, 1) if directional and s["count"] else None,
            "avg_next_day_ret_pct": round(s["sum_ret"] / s["count"], 3) if s["count"] else 0,
        }

    vol_table = {k: {"count": v["count"],
                     "follow_through_pct": round(v["follow"] / v["count"] * 100, 1) if v["count"] else None}
                 for k, v in vol_split.items() if v["count"] >= 20}
    dow_table = {k: {"count": v["count"],
                     "follow_through_pct": round(v["follow"] / v["count"] * 100, 1) if v["count"] else None}
                 for k, v in dow.items()}
    # V31.1 Layer-6 — Knowledge Score: pure data-coverage metric (how much the
    # AI has SEEN — deliberately not a claim about how good it is)
    patterns = len(table) + len(vol_table) + len(dow_table)
    knowledge = {
        "years": YEARS, "sessions": total_days,
        "symbols": len(per_symbol), "patterns_learned": patterns,
        "coverage_pct": round(min(100.0, total_days / (250.0 * YEARS * max(len(per_symbol), 1)) * 100), 0),
        "note": "Coverage of requested history — a data metric, not a skill claim.",
    }

    report = {
        "ready": True, "source": "HISTORICAL",
        "years": YEARS, "indices": list(per_symbol),
        "days_analysed": total_days,
        "setup_table": table, "vol_regime_table": vol_table,
        "day_of_week": dow_table, "knowledge": knowledge,
        "per_symbol": per_symbol,
        "scope_note": "HISTORICAL KNOWLEDGE — underlying daily setups only (Dhan has no "
                      "historical option chains, so premium/strike behaviour is NOT learned "
                      "here). Kept separate from live validation (Validated x/100 = experience).",
        "ran_in_sec": round(time.time() - t0, 1), "ts": time.time(),
    }

    # persist as knowledge snapshot (period='historical'), best-effort
    try:
        from . import journal
        _sb = getattr(journal, "_sb", None)
        if _sb:
            _sb.table("evolution_reports").insert({
                "period": "historical",
                "accuracy": max((v["follow_through_pct"] or 0) for v in table.values()) if table else None,
                "report": report,
            }).execute()
            report["persisted"] = True
    except Exception as e:
        log.warning("historical learning persist failed: %s", e)
        report["persisted"] = False
    return report
