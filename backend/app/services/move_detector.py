"""MODE Phase A — Market Opportunity Detection Engine (PROPOSAL #010).

Opportunity Layer ONLY (owner-locked law): detects premium moves on strikes
the platform is already watching and raises tiered alerts —
+10 WATCH · +20 STRONG · +30 MOMENTUM · +50 BREAKOUT · +100 EXPANSION.
It NEVER forces, softens, or bypasses the Decision Layer; the gate remains
the sole authority on entries. Zero new broker calls — consumes the option
chain the platform already fetches every option tick.

Every alert is ledgered so the future Miss Detector (Phase B) can measure
BOTH error directions: moves with no alert AND alerts with no move.
"""
from __future__ import annotations

import collections
import datetime
import logging
import time
from typing import Any

from ..core.clock import IST

log = logging.getLogger("move_detector")

# (points, name) descending. A tier fires once per episode per strike.
_TIERS = [(100, "EXPANSION"), (50, "BREAKOUT"), (30, "MOMENTUM"),
          (20, "STRONG"), (10, "WATCH")]
_MIN_RISE_PCT = 5.0      # noise floor — +10 pts on a ₹600 premium is not a move
_LOOKBACK_SEC = 600      # rise measured against the 10-min rolling low
_EPISODE_QUIET = 900     # 15 min without a fresh tier ⇒ episode closes
_MAX_ALERTS_PER_MIN = 4  # hard cap — no siren fatigue (PROPOSAL #010 guard-rail)

# per "symbol:strike:type" tracking state
_tracks: dict[str, dict[str, Any]] = {}
# fired-alert ledger (Phase B miss-join consumes this)
_alerts: collections.deque = collections.deque(maxlen=300)
_recent_fire_ts: collections.deque = collections.deque(maxlen=32)


def _rate_ok() -> bool:
    now = time.time()
    while _recent_fire_ts and now - _recent_fire_ts[0] > 60:
        _recent_fire_ts.popleft()
    return len(_recent_fire_ts) < _MAX_ALERTS_PER_MIN


async def scan(symbol: str, spot: float, chain: list[dict] | None,
               strike_queue: list[dict] | None) -> None:
    """Called every option tick with the fresh chain + the watched strikes."""
    if not chain or not strike_queue:
        return
    from . import alerts

    now = time.time()
    for sq in strike_queue[:5]:
        strike, typ = sq.get("strike"), sq.get("type")
        if strike is None or typ not in ("CE", "PE"):
            continue
        side = "ce" if typ == "CE" else "pe"
        row = next((r for r in chain if float(r.get("strike", 0)) == float(strike)), None)
        if not row:
            continue
        prem = float(row.get(f"{side}_ltp") or 0)
        if prem <= 0:
            continue

        key = f"{symbol}:{strike}:{typ}"
        t = _tracks.setdefault(key, {"series": collections.deque(maxlen=400),
                                     "fired": set(), "last_fire": 0.0})
        t["series"].append((now, prem))
        while t["series"] and now - t["series"][0][0] > _LOOKBACK_SEC:
            t["series"].popleft()

        low = min(p for _, p in t["series"])
        rise = prem - low
        rise_pct = rise / low * 100 if low else 0.0

        # episode close: premium gave the move back, or long quiet
        if t["fired"] and (rise < 5.0 or now - t["last_fire"] > _EPISODE_QUIET):
            t["fired"] = set()

        # acceleration (owner item #7): last-60s rise vs the prior 60s
        r_now = _window_rise(t["series"], now - 60, now)
        r_prev = _window_rise(t["series"], now - 120, now - 60)
        accelerating = r_now > max(r_prev, 0) * 1.5 and r_now >= 8

        if rise_pct < _MIN_RISE_PCT:
            continue
        for pts, name in reversed(_TIERS):          # fire ascending, once each
            if rise >= pts and pts not in t["fired"]:
                t["fired"].add(pts)
                t["last_fire"] = now
                mins = round((now - t["series"][0][0]) / 60, 1)
                rec = {"ts": now, "symbol": symbol, "strike": strike, "type": typ,
                       "tier": name, "tier_pts": pts,
                       "rise_pts": round(rise, 1), "rise_pct": round(rise_pct, 1),
                       "premium": round(prem, 2), "from_low": round(low, 2),
                       "window_min": mins, "accelerating": accelerating,
                       "spot": round(spot, 2)}
                _alerts.append(rec)
                if _rate_ok():
                    _recent_fire_ts.append(now)
                    title = f"🔥 {name}: {symbol} {strike:g} {typ} +{rise:.0f} pts"
                    body = (f"₹{low:.2f} → ₹{prem:.2f} (+{rise_pct:.0f}%) in {mins:g} min"
                            + (" · ACCELERATING" if accelerating else "")
                            + " · Opportunity layer — the entry gate is unchanged and decides separately.")
                    try:
                        await alerts.send("MOVE", title, body, symbol)
                    except Exception:
                        log.exception("move alert send failed")
                else:
                    log.info("move alert rate-capped: %s %s %s", symbol, strike, name)


def _window_rise(series, t0: float, t1: float) -> float:
    win = [p for ts, p in series if t0 <= ts <= t1]
    return (win[-1] - min(win)) if len(win) >= 2 else 0.0


def report() -> dict[str, Any]:
    al = list(_alerts)
    by_tier: dict[str, int] = {}
    for a in al:
        by_tier[a["tier"]] = by_tier.get(a["tier"], 0) + 1
    return {
        "ready": True,
        "note": ("MODE Phase A — opportunity alerts only; the decision gate is "
                 "untouched and decides entries separately. Ledger feeds the "
                 "Phase B miss-detector (both error directions)."),
        "alerts_fired": len(al),
        "by_tier": by_tier,
        "tracked_strikes": len(_tracks),
        "recent": [dict(a, ts=datetime.datetime.fromtimestamp(a["ts"], IST).strftime("%H:%M:%S"))
                   for a in al[-20:]],
    }
