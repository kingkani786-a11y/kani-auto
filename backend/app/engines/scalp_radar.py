"""SCALP RADAR V2 — independent short-duration scalping module.

Completely separate from the main signal/risk/probability engines. It may
fire BUY CE while the main engine says NO TRADE, and vice versa — by design.
It only consumes raw candles + the option chain (already in memory) and the
shared math helpers; it never writes back into the main decision path.

Scalp Score weights:
  VWAP direction 20 · 1m structure 15 · 3m structure 15 · volume spike 10 ·
  gamma distance 10 · ATR expansion 10 · liquidity sweep 10 ·
  order-flow delta 5 · time filter 5
Fires only when the dominant side's score >= 70.
"""
from __future__ import annotations

import datetime
import zoneinfo
from typing import Any

from .mtf import resample
from .technicals import atr as atr_fn, vwap as vwap_fn

IST = zoneinfo.ZoneInfo("Asia/Kolkata")


def _structure_dir(candles: list[dict]) -> int:
    """+1 up / -1 down / 0 flat from the last few swings."""
    if len(candles) < 6:
        return 0
    highs = [c["high"] for c in candles[-6:]]
    lows = [c["low"] for c in candles[-6:]]
    hh = highs[-1] > max(highs[:-1])
    hl = lows[-1] > min(lows[:-1])
    ll = lows[-1] < min(lows[:-1])
    lh = highs[-1] < max(highs[:-1])
    if hh or hl:
        return 1
    if ll or lh:
        return -1
    return 0


def _time_filter_score() -> float:
    """Avoid lunch lull and the final scramble; reward active windows."""
    t = datetime.datetime.now(IST).time()
    H = lambda h, m=0: datetime.time(h, m)
    if H(9, 20) <= t <= H(11, 0) or H(13, 15) <= t <= H(14, 45):
        return 100.0          # prime momentum windows
    if H(11, 0) < t < H(13, 15):
        return 40.0           # lunch lull
    if t > H(15, 10) or t < H(9, 20):
        return 30.0           # open auction / close scramble
    return 70.0


def compute(candles_1m: list[dict], analytics: dict[str, Any], spot: float,
            main_direction: str = "") -> dict[str, Any]:
    inactive = {"active": False, "scalp_score": 0, "direction": "NONE",
                "reason": "Insufficient data"}
    if not candles_1m or len(candles_1m) < 30 or spot <= 0:
        return inactive

    c1 = candles_1m
    c3 = resample(candles_1m, 3)
    today = datetime.datetime.now(IST).date()
    session = [c for c in candles_1m
               if datetime.datetime.fromtimestamp(c["time"], IST).date() == today] or candles_1m[-75:]

    vwap = vwap_fn(session)
    atr1 = atr_fn(c1[-30:])                          # 1-minute ATR (points/min proxy)
    atr_prev = atr_fn(c1[-60:-30]) if len(c1) >= 60 else atr1

    # ---- per-component BULL score (0..100, 50 = neutral). bear = 100 - bull
    #      for directional factors; quality factors lift both sides equally. ----
    bull: dict[str, float] = {}
    clamp = lambda x: max(0.0, min(100.0, x))
    # VWAP direction (20%)
    dist = (spot - vwap) / spot * 100 if vwap else 0
    bull["vwap"] = clamp(50 + dist * 140)
    # 1m & 3m structure (15% each)
    bull["s1"] = {1: 88, -1: 12, 0: 50}[_structure_dir(c1)]
    bull["s3"] = {1: 88, -1: 12, 0: 50}[_structure_dir(c3)]
    # volume spike (10%) — directional by last-bar close location × spike size
    vols = [max(float(c.get("volume", 0)), 0.0) for c in c1[-30:]]
    avg_v = sum(vols) / len(vols) or 1.0
    last = c1[-1]
    rng = max(last["high"] - last["low"], 1e-9)
    loc = ((last["close"] - last["low"]) / rng) * 2 - 1
    spike = min(float(last.get("volume", 0)) / avg_v, 3.0) / 3.0
    bull["vol"] = clamp(50 + loc * spike * 60)
    # gamma distance (10%) — directional room toward the OI wall
    chain = analytics.get("chain") or []
    gamma_wall = None
    if chain:
        gw = max(chain, key=lambda r: r.get("ce_oi", 0) + r.get("pe_oi", 0))
        gamma_wall = gw["strike"]
    gamma_dist = abs(spot - gamma_wall) if gamma_wall else atr1 * 5
    room = min(gamma_dist / max(atr1 * 3, 1), 1.0)            # 0..1 room to run
    # wall above → room favors longs; wall below → favors shorts
    if gamma_wall and gamma_wall > spot:
        bull["gamma"] = clamp(50 + room * 40)
    elif gamma_wall and gamma_wall < spot:
        bull["gamma"] = clamp(50 - room * 40)
    else:
        bull["gamma"] = 50 + room * 10
    # ATR expansion (10%) — quality, lifts both sides (good = tradeable)
    atr_exp = 1.0 if atr_prev <= 0 else min(atr1 / atr_prev, 2.0)
    atr_state = "EXPANDING" if atr_exp > 1.2 else "CONTRACTING" if atr_exp < 0.8 else "NORMAL"
    atr_q = clamp(35 + min((atr_exp - 0.7) / 1.3, 1.0) * 65)  # 35..100
    bull["atr"] = atr_q                                       # symmetric quality
    # liquidity sweep (10%) — wick beyond recent extreme then reclaim
    recent_hi = max(c["high"] for c in c1[-20:-1])
    recent_lo = min(c["low"] for c in c1[-20:-1])
    if last["high"] > recent_hi and last["close"] < recent_hi:
        bull["sweep"] = 8.0     # swept highs, rejected -> bearish
    elif last["low"] < recent_lo and last["close"] > recent_lo:
        bull["sweep"] = 92.0    # swept lows, reclaimed -> bullish
    else:
        bull["sweep"] = 50.0
    # order-flow delta (5%)
    deltas = []
    for c in c1[-10:]:
        r = max(c["high"] - c["low"], 1e-9)
        deltas.append((((c["close"] - c["low"]) / r) * 2 - 1) * max(float(c.get("volume", 0)), 0.0))
    tot_v = sum(max(float(c.get("volume", 0)), 0.0) for c in c1[-10:]) or 1.0
    bull["of"] = clamp(50 + sum(deltas) / tot_v * 60)
    # time filter (5%) — quality, both sides
    bull["time"] = _time_filter_score()

    W = {"vwap": 0.20, "s1": 0.15, "s3": 0.15, "vol": 0.10, "gamma": 0.10,
         "atr": 0.10, "sweep": 0.10, "of": 0.05, "time": 0.05}
    QUALITY = {"atr", "time"}   # symmetric factors: same on both sides
    scalp_bull = sum(bull[k] * w for k, w in W.items())
    scalp_bear = sum((bull[k] if k in QUALITY else 100 - bull[k]) * w for k, w in W.items())

    direction = "BULL" if scalp_bull >= scalp_bear else "BEAR"
    scalp_score = round(max(scalp_bull, scalp_bear), 0)
    comp = {k: round(v, 0) for k, v in bull.items()}

    # ---- Layer 13: the scalp NEVER overrides the main direction. When it
    # opposes the main signal it becomes a COUNTER-TREND scalp — higher bar,
    # reduced confidence (display label flagged downstream). ----
    counter_trend = bool(main_direction in ("BULL", "BEAR") and direction != main_direction)
    if counter_trend:
        scalp_score = round(max(0, scalp_score - 15), 0)   # penalise opposing scalps
    threshold = 78 if counter_trend else 70                # tougher bar against trend
    active = scalp_score >= threshold

    # holding-time estimate: minutes to traverse +15 at the current 1m pace
    pace = max(atr1, spot * 0.0002)
    hold_min = max(1, round(15 / pace, 0)) if pace else None

    d = 1 if direction == "BULL" else -1
    stop_pts = max(round(atr1 * 0.8, 1), 8.0)        # scalp stop
    base_sig = ("BUY CE" if direction == "BULL" else "BUY PE") if active else "NO SCALP"
    out = {
        "active": active,
        "direction": direction,
        "counter_trend": counter_trend,
        "main_direction": main_direction,
        "signal": (f"COUNTER-TREND {base_sig}" if (active and counter_trend) else base_sig),
        "scalp_score": scalp_score,
        "probability": round(min(90, 40 + scalp_score * 0.5), 0),
        "entry": round(spot, 2),
        "stop_loss": round(spot - d * stop_pts, 2),
        "target1": round(spot + d * 5, 2),
        "target2": round(spot + d * 10, 2),
        "target3": round(spot + d * 15, 2),
        "gamma_distance": round(gamma_dist, 1),
        "gamma_wall": gamma_wall,
        "atr_state": atr_state,
        "atr_1m": round(atr1, 1),
        "holding_time_min": hold_min,
        "components": {k: round(v, 0) for k, v in comp.items()},
        "reason": _reason(direction, comp, atr_state) if active else "Scalp score below 70",
        "ts": __import__("time").time(),
    }

    # ---- V3 Execution Intelligence Suite (all independent additions) ----
    out["threshold"] = threshold
    out["status"] = ("ACTIVE" if active else "NEAR_MISS" if scalp_score >= threshold - 5 else "REJECTED")
    out["explain"] = _explain(bull, direction, scalp_score, atr_state)
    if 65 <= scalp_score < 70:
        out["near_miss"] = _near_miss(bull, direction, scalp_score)
    if scalp_score < 65:
        out["rejection"] = _rejection(bull, direction)
    # strike recommendation + premium engines (when a direction exists)
    if direction != "NONE" and (analytics or {}).get("chain"):
        out["execution"] = _execution_suite(
            analytics["chain"], spot, direction, atr1,
            (analytics or {}).get("expiry"))
    return out


# ---- friendly component labels (Module 6 breakdown) ----
_LABELS = {"vwap": "VWAP", "s1": "1m Structure", "s3": "3m Structure",
           "vol": "Volume", "gamma": "Gamma", "atr": "ATR",
           "sweep": "Liquidity Sweep", "of": "Delta", "time": "Time Filter"}
_QUALITY = {"atr", "time"}


def _favorable(bull: dict, direction: str) -> dict[str, float]:
    """Each component's score in FAVOR of the chosen direction (0..100)."""
    out = {}
    for k, v in bull.items():
        out[k] = v if (direction == "BULL" or k in _QUALITY) else 100 - v
    return out


def _explain(bull: dict, direction: str, score: float, atr_state: str) -> dict:
    fav = _favorable(bull, direction)
    return {
        "score": round(score, 0),
        "threshold": 70,
        "status": "ACTIVE" if score >= 70 else "NEAR MISS" if score >= 65 else "REJECTED",
        "breakdown": [{"name": _LABELS[k], "score": round(fav[k], 0),
                       "favorable": fav[k] >= 55} for k in _LABELS if k in fav],
    }


def _rejection(bull: dict, direction: str) -> dict:
    fav = _favorable(bull, direction)
    weak = sorted(((_LABELS[k], v) for k, v in fav.items() if k in _LABELS),
                  key=lambda x: x[1])
    reasons = [f"Weak {n}" for n, v in weak if v < 50][:2]
    return {"primary": reasons[0] if reasons else "Insufficient confluence",
            "secondary": reasons[1] if len(reasons) > 1 else "—"}


def _near_miss(bull: dict, direction: str, score: float) -> dict:
    fav = _favorable(bull, direction)
    missing = sorted(((_LABELS[k], v) for k, v in fav.items() if k in _LABELS and v < 60),
                     key=lambda x: x[1])
    return {"score": round(score, 0), "need": round(70 - score, 0),
            "missing": [n for n, _ in missing[:2]] or ["marginal confluence"]}


def _execution_suite(chain: list[dict], spot: float, direction: str,
                     atr1: float, expiry: str | None) -> dict:
    """Modules 1–4 + 10: best strike, premium entry/SL/targets, execution score."""
    from .greeks import compute_greeks
    is_call = direction == "BULL"
    side = "ce" if is_call else "pe"
    strikes = sorted({r["strike"] for r in chain})
    if not strikes:
        return {}
    step = min((b - a for a, b in zip(strikes, strikes[1:])), default=50) or 50
    atm = min(strikes, key=lambda k: abs(k - spot))
    # ATM, 1-step ITM, 1-step OTM
    itm = atm - step if is_call else atm + step
    otm = atm + step if is_call else atm - step
    candidates = [s for s in (atm, itm, otm) if s in strikes]

    import datetime as _dt
    try:
        t = max((_dt.date.fromisoformat(expiry) - _dt.date.today()).days, 0) / 365 + 1e-4 if expiry else 2/365
    except Exception:
        t = 2 / 365

    rows = {r["strike"]: r for r in chain}
    max_oi = max((rows[s].get(f"{side}_oi", 0) for s in candidates), default=1) or 1
    max_vol = max((rows[s].get(f"{side}_volume", 0) for s in candidates), default=1) or 1

    best = None
    for s in candidates:
        r = rows[s]
        ltp = float(r.get(f"{side}_ltp") or 0)
        if ltp <= 0:
            continue
        iv = float(r.get(f"{side}_iv") or 0) / 100.0
        g = compute_greeks(spot, s, t, 0.07, ltp, is_call, iv_hint=iv)
        delta = abs(g.delta)
        bid, ask = float(r.get(f"{side}_bid") or 0), float(r.get(f"{side}_ask") or 0)
        spread_pct = (ask - bid) / ltp if (bid > 0 and ask > bid) else 0.03
        delta_q = max(0.0, 1 - abs(delta - 0.5) / 0.35)
        liq_q = 0.6 * (r.get(f"{side}_oi", 0) / max_oi) + 0.4 * (r.get(f"{side}_volume", 0) / max_vol)
        spread_q = max(0.0, 1 - spread_pct / 0.06)
        quality = 0.4 * delta_q + 0.35 * liq_q + 0.25 * spread_q
        cand = {"strike": s, "ltp": ltp, "delta": round(delta, 3), "iv": round(g.iv * 100, 1),
                "oi": r.get(f"{side}_oi", 0), "volume": r.get(f"{side}_volume", 0),
                "spread_pct": round(spread_pct * 100, 2),
                "delta_q": delta_q, "liq_q": liq_q, "spread_q": spread_q, "quality": quality}
        if best is None or quality > best["quality"]:
            best = cand
    if not best:
        return {}

    delta, ltp = best["delta"], best["ltp"]
    prem = lambda under_move: max(round(delta * under_move, 1), 0.05)
    # Module 2 — Entry
    entry = {"aggressive": round(ltp, 1), "conservative": round(ltp + max(1, ltp * 0.01), 1),
             "trigger_above": round(ltp + max(1, ltp * 0.008), 1)}
    # Module 3 — Stop Loss (structure vs volatility, in premium)
    struct_stop = round(ltp - prem(max(atr1 * 0.8, 8)), 1)
    vol_stop = round(ltp - prem(atr1), 1)
    rec_sl = round(max(struct_stop, vol_stop, ltp * 0.5), 1)
    # Module 4 — Targets (premium for +5/+10/+15 underlying)
    targets = {"t1": round(ltp + prem(5), 1), "t2": round(ltp + prem(10), 1),
               "t3": round(ltp + prem(15), 1)}
    risk_pts = round(ltp - rec_sl, 1)
    reward_pts = round(targets["t2"] - ltp, 1)
    rr = round(reward_pts / risk_pts, 2) if risk_pts > 0 else None

    # Module 10 — Execution score
    exec_score = round(best["quality"] * 100, 0)
    liq_label = "Excellent" if best["liq_q"] > 0.66 else "Good" if best["liq_q"] > 0.33 else "Thin"
    spread_label = "Tight" if best["spread_q"] > 0.66 else "Moderate" if best["spread_q"] > 0.33 else "Wide"

    return {
        "strike": best["strike"], "type": "CE" if is_call else "PE",
        "option_ltp": ltp, "spot": round(spot, 2),
        "delta": delta, "iv": best["iv"], "oi": best["oi"], "volume": best["volume"],
        "strike_quality": round(best["quality"] * 100, 0),
        "liquidity": liq_label, "spread": spread_label, "spread_pct": best["spread_pct"],
        "entry": entry,
        "stop": {"structure": struct_stop, "volatility": vol_stop,
                 "recommended": rec_sl, "risk_points": risk_pts},
        "targets": {**targets, "holding": "5-15 min"},
        "reward_risk": rr,
        "execution_score": exec_score,
        "quality_detail": {"execution": exec_score,
                           "liquidity": round(best["liq_q"] * 100, 0),
                           "spread": round(best["spread_q"] * 100, 0),
                           "risk": round(min((rr or 0) / 2.5, 1) * 100, 0)},
    }


def _reason(direction: str, comp: dict, atr_state: str) -> str:
    # comp values are BULL scores (0..100, 50 neutral)
    bull = direction == "BULL"
    fav = (lambda v: v > 60) if bull else (lambda v: v < 40)
    bits = []
    if fav(comp.get("vwap", 50)):
        bits.append("VWAP side")
    if fav(comp.get("s1", 50)):
        bits.append("1m structure")
    if (bull and comp.get("sweep", 50) > 80) or (not bull and comp.get("sweep", 50) < 20):
        bits.append("liquidity sweep")
    if atr_state == "EXPANDING":
        bits.append("ATR expanding")
    return (", ".join(bits) or "momentum aligned").capitalize() + f" — {'long' if bull else 'short'} scalp"
