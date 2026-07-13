"""Premium Radar — live option-premium tracking for the BUYER.

Owner insight: the platform watches the INDEX too much; an option buyer lives
on PREMIUM movement. MODE (move_detector) already alerts on big tiered moves,
but (a) it only watches the ATM strike_queue and (b) the dashboard hides it
until an alert fires — so the BIRTH of a move (₹85 → 99 → 112) is invisible.

Premium Radar fixes both: it tracks ATM ± N strikes (CE + PE) from the FULL
chain every option tick and always exposes, per strike:
  premium · %from-low · velocity (pts/min) · acceleration · volume · OI-change
  · a transparent Runner SCORE (0–100) · a lifecycle STAGE
    (Birth → Expansion → Acceleration → Runner → Exhaustion) · ★stars.

Doctrine kept: read-only over published chain; NOT the decision path; the
Runner score is a DECLARED transparent score (weighted signals), honestly
labelled — never a calibrated win-probability. No trade instruction is emitted.
"""
from __future__ import annotations

import collections
import time
from typing import Any

_LOOKBACK = 300.0          # 5-min rolling window per strike
_N_STRIKES = 4             # ATM ± 4 on each side, both CE and PE
_tracks: dict[str, dict[str, Any]] = {}


def _series_metrics(series) -> dict[str, Any]:
    now = series[-1][0]
    prem = series[-1][1]
    low = min(p for _, p, _v, _o in series)
    high = max(p for _, p, _v, _o in series)
    rise = prem - low
    rise_pct = (rise / low * 100) if low else 0.0
    # velocity: pts/min over the last 60s
    t0 = now - 60
    older = [p for ts, p, _v, _o in series if ts <= t0]
    base_p = older[-1] if older else series[0][1]
    vel = (prem - base_p)  # pts in last ~60s ≈ pts/min
    # acceleration: last-60s rise vs prior-60s rise
    def _rise_between(a, b):
        pts = [p for ts, p, _v, _o in series if a <= ts <= b]
        return (pts[-1] - pts[0]) if len(pts) >= 2 else 0.0
    accel = _rise_between(now - 60, now) - _rise_between(now - 120, now - 60)
    vol_now = series[-1][2]
    vol_start = series[0][2]
    oi_now = series[-1][3]
    oi_start = next((o for _ts, _p, _v, o in series if o > 0), 0)
    oi_pct = ((oi_now - oi_start) / oi_start * 100) if oi_start else 0.0
    return {"premium": round(prem, 2), "low": round(low, 2), "high": round(high, 2),
            "rise_pct": round(rise_pct, 1), "velocity": round(vel, 2),
            "accel": round(accel, 2), "vol_now": vol_now,
            "vol_delta": vol_now - vol_start, "oi_pct": round(oi_pct, 1)}


def _runner_score(m: dict[str, Any]) -> int:
    """Transparent 0–100 runner SCORE (declared, not win-calibrated). Weighted:
    rise% (30) + velocity (25) + acceleration (20) + volume (15) + OI build (10)."""
    s = 0.0
    s += min(30, m["rise_pct"] * 1.5)                       # rise
    s += min(25, max(0, m["velocity"]) * 2.5)               # velocity
    s += 20 if m["accel"] > 0 else (5 if m["accel"] == 0 else 0)  # acceleration
    s += 15 if m["vol_delta"] > 0 else 0                    # fresh volume
    s += min(10, max(0, m["oi_pct"]))                       # OI build-up
    return int(max(0, min(100, round(s))))


def _stage(m: dict[str, Any]) -> str:
    if m["velocity"] < 0 and m["rise_pct"] >= 20:
        return "EXHAUSTION"
    if m["rise_pct"] < 5:
        return "BIRTH"
    if m["accel"] > 0 and m["velocity"] >= 4:
        return "RUNNER"
    if m["accel"] > 0:
        return "ACCELERATION"
    return "EXPANSION"


def _stars(score: int) -> int:
    return max(1, min(5, 1 + score // 20))


# Owner's 3 macro-phases by %-rise from the session low.
def _phase(rise_pct: float) -> dict[str, str]:
    if rise_pct >= 70:
        return {"code": "RUNNER_CONFIRMED", "label": "RUNNER CONFIRMED", "dot": "🔴"}
    if rise_pct >= 30:
        return {"code": "RUNNER_BUILDING", "label": "RUNNER BUILDING", "dot": "🟠"}
    return {"code": "BUILDING", "label": "PREMIUM BUILDING", "dot": "🟢"}


def _ladder(series) -> list[dict[str, Any]]:
    """Down-sample the premium series to ≤6 points for the visible ladder
    (09:36 ₹85 → 09:57 ₹158). Times are IST HH:MM."""
    from ..core.clock import IST
    import datetime
    pts = list(series)
    if len(pts) <= 6:
        chosen = pts
    else:
        step = (len(pts) - 1) / 5
        chosen = [pts[round(i * step)] for i in range(6)]
    out = []
    for ts, p, _v, _o in chosen:
        t = datetime.datetime.fromtimestamp(ts, IST).strftime("%H:%M")
        out.append({"t": t, "p": round(p, 2)})
    return out


def scan(symbol: str, spot: float, chain: list[dict] | None) -> None:
    """Track ATM ± N strikes (CE+PE) each option tick. Read-only, additive."""
    if not chain or not spot:
        return
    now = time.time()
    # ATM = chain strike nearest spot
    strikes = sorted({float(r.get("strike", 0)) for r in chain if r.get("strike")})
    if not strikes:
        return
    atm = min(strikes, key=lambda k: abs(k - spot))
    idx = strikes.index(atm)
    window = strikes[max(0, idx - _N_STRIKES): idx + _N_STRIKES + 1]

    live_keys = set()
    for strike in window:
        row = next((r for r in chain if float(r.get("strike", 0)) == strike), None)
        if not row:
            continue
        for typ, side in (("CE", "ce"), ("PE", "pe")):
            prem = float(row.get(f"{side}_ltp") or 0)
            if prem <= 0:
                continue
            key = f"{symbol}:{int(strike)}:{typ}"
            live_keys.add(key)
            t = _tracks.setdefault(key, {"series": collections.deque(maxlen=200),
                                         "symbol": symbol, "strike": int(strike),
                                         "type": typ, "peak_rise": 0.0, "peak_prem": 0.0,
                                         "vol_confirm": None, "oi_confirm": None})
            vol = float(row.get(f"{side}_volume") or 0)
            oi = float(row.get(f"{side}_oi") or 0)
            t["series"].append((now, prem, vol, oi))
            while t["series"] and now - t["series"][0][0] > _LOOKBACK:
                t["series"].popleft()
            # day-peak + first confirmation timestamps (for Missed Opportunity)
            m = _series_metrics(t["series"])
            if m["rise_pct"] > t["peak_rise"]:
                t["peak_rise"] = m["rise_pct"]; t["peak_prem"] = m["premium"]
            if t["vol_confirm"] is None and m["vol_delta"] > 0 and m["rise_pct"] >= 5:
                t["vol_confirm"] = now
            if t["oi_confirm"] is None and m["oi_pct"] >= 1 and m["rise_pct"] >= 5:
                t["oi_confirm"] = now
    # drop stale tracks (strike left the ATM window long ago)
    for k in [k for k, t in _tracks.items() if t["series"] and now - t["series"][-1][0] > 120]:
        _tracks.pop(k, None)


def _checklist(m: dict[str, Any]) -> dict[str, bool]:
    """The conditions a strike needs to become a runner (owner's watchlist)."""
    return {
        "premium_rising": m["rise_pct"] > 0,
        "velocity": m["velocity"] > 0,
        "volume": m["vol_delta"] > 0,
        "oi": m["oi_pct"] >= 1,
    }


def radar(top: int = 8) -> dict[str, Any]:
    """Leaders (running now) · Watchlist (building) · Missed (peaked today)."""
    rows = []
    missed = []
    for key, t in _tracks.items():
        if len(t["series"]) < 2:
            continue
        m = _series_metrics(t["series"])
        score = _runner_score(m)
        chk = _checklist(m)
        rows.append({
            "symbol": t["symbol"], "strike": t["strike"], "type": t["type"],
            "premium": m["premium"], "from_low": m["low"], "rise_pct": m["rise_pct"],
            "velocity": m["velocity"], "accel": m["accel"], "oi_pct": m["oi_pct"],
            "vol_delta": m["vol_delta"], "runner_score": score, "stars": _stars(score),
            "stage": _stage(m), "phase": _phase(m["rise_pct"]),
            "ladder": _ladder(t["series"]), "checklist": chk,
            "checks_met": sum(chk.values()),
        })
        # Missed Opportunity: strike ran a big move today (peak ≥ 30%)
        if t.get("peak_rise", 0) >= 30:
            reasons = []
            if t.get("vol_confirm"):
                reasons.append("Volume confirmation")
            if t.get("oi_confirm"):
                reasons.append("OI breakout")
            missed.append({
                "symbol": t["symbol"], "strike": t["strike"], "type": t["type"],
                "from_low": m["low"], "peak_premium": round(t["peak_prem"], 2),
                "peak_rise_pct": round(t["peak_rise"], 1),
                "missed_points": round(t["peak_prem"] - m["low"], 2),
                "reasons": reasons or ["Premium velocity"],
            })

    rows.sort(key=lambda r: r["runner_score"], reverse=True)
    # Leaders = clear movers; Watchlist = still-building with momentum but not yet runners
    leaders = [r for r in rows if r["rise_pct"] >= 30][:top]
    watchlist = [r for r in rows
                 if r["rise_pct"] < 30 and r["checks_met"] >= 2 and r["runner_score"] > 0]
    watchlist.sort(key=lambda r: r["runner_score"], reverse=True)
    missed.sort(key=lambda r: r["peak_rise_pct"], reverse=True)
    return {
        "movers": rows[:top],            # full radar table (kept)
        "leaders": leaders,              # 🔴/🟠 running now
        "watchlist": watchlist[:6],      # 🟢 building — watch before it runs
        "missed": missed[:6],            # peaked ≥30% today
        "tracked": len(_tracks),
        "note": "Runner score is a declared transparent signal blend "
                "(rise/velocity/acceleration/volume/OI), NOT a win-calibrated "
                "probability. Radar observes premium; it never places or "
                "recommends a trade — the engine gate decides.",
    }
