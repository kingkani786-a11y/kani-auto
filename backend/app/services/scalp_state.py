"""Scalp Radar V3 — trade management (Module 5) + quality analytics (Module 9).

Fully independent of the main lifecycle/memory engines. Tracks one active
scalp at a time against the UNDERLYING levels (+5/+10/+15 / stop), and keeps
a rolling history of scalp outcomes for win-rate / RR stats.
"""
from __future__ import annotations

import time
from collections import deque
from typing import Any

_history: deque = deque(maxlen=200)   # {win, rr}

_active: dict[str, Any] | None = None  # current tracked scalp


def _new_trade(scalp: dict) -> dict:
    return {
        "direction": scalp["direction"],
        "entry": scalp["entry"], "stop": scalp["stop_loss"],
        # original risk captured at creation (before any SL-to-cost move)
        "risk_pts": abs(scalp["entry"] - scalp["stop_loss"]) or 1.0,
        "t1": scalp["target1"], "t2": scalp["target2"], "t3": scalp["target3"],
        "opened": time.time(),
        "flags": {"signal_active": True, "entry_hit": False, "t1": False,
                  "t2": False, "t3": False, "sl": False, "sl_to_cost": False,
                  "trail": False, "closed": False},
    }


def reset() -> None:
    """Drop the active scalp trade — called on symbol switch (isolation)."""
    global _active
    _active = None


def on_signal(scalp: dict | None) -> None:
    """Called each scalp tick. Arms a new trade when one becomes active and no
    trade is open; ignores while a trade is in progress (independent module)."""
    global _active
    if not scalp or not scalp.get("active"):
        return
    if _active and not _active["flags"]["closed"]:
        # same direction & similar entry → keep tracking; else leave as is
        return
    _active = _new_trade(scalp)


def on_tick(spot: float) -> dict | None:
    """Advance the active scalp trade against the live underlying price."""
    global _active
    if not _active or _active["flags"]["closed"] or not spot:
        return status()
    t = _active
    d = 1 if t["direction"] == "BULL" else -1
    f = t["flags"]

    if not f["entry_hit"]:
        f["entry_hit"] = True            # market entry at signal (scalp)

    # stop check first (conservative)
    if (spot - t["stop"]) * d <= 0 and not f["sl_to_cost"]:
        f["sl"] = True; f["closed"] = True
        _settle(False, t)
        return status()

    # targets
    if not f["t1"] and (spot - t["t1"]) * d >= 0:
        f["t1"] = True
        t["stop"] = t["entry"]; f["sl_to_cost"] = True   # move SL to cost after T1
        _settle(True, t)                                  # banked at least 1R-ish
    if f["t1"] and not f["t2"] and (spot - t["t2"]) * d >= 0:
        f["t2"] = True; f["trail"] = True
    if f["t2"] and not f["t3"] and (spot - t["t3"]) * d >= 0:
        f["t3"] = True; f["closed"] = True
    # cost-stop after T1
    if f["sl_to_cost"] and not f["t3"] and (spot - t["entry"]) * d <= 0:
        f["closed"] = True
    return status()


def _settle(win: bool, t: dict) -> None:
    # RR using the ORIGINAL risk (captured at creation) vs reward to T2
    risk_pts = t.get("risk_pts") or 1.0
    reward_pts = abs(t["t2"] - t["entry"])
    _history.append({"win": 1 if win else 0, "rr": round(reward_pts / risk_pts, 2)})


def status() -> dict:
    if not _active:
        return {"open": False, "flags": {}, "stage": "IDLE"}
    f = _active["flags"]
    stage = ("CLOSED" if f["closed"] else "T3 HIT" if f["t3"] else "T2 HIT" if f["t2"]
             else "T1 HIT" if f["t1"] else "SL HIT" if f["sl"] else "ENTRY HIT"
             if f["entry_hit"] else "SIGNAL ACTIVE")
    return {"open": not f["closed"], "stage": stage, "direction": _active["direction"],
            "flags": f, "levels": {"entry": _active["entry"], "stop": _active["stop"],
                                    "t1": _active["t1"], "t2": _active["t2"], "t3": _active["t3"]}}


def analytics() -> dict:
    h = list(_history)
    if not h:
        return {"trades": 0, "win_rate": None, "avg_rr": None, "success_rate": None}
    wins = sum(o["win"] for o in h)
    rrs = [o["rr"] for o in h if o["win"]]
    return {
        "trades": len(h),
        "win_rate": round(wins / len(h) * 100, 0),
        "avg_rr": round(sum(rrs) / len(rrs), 1) if rrs else None,
        "success_rate": round(wins / len(h) * 100, 0),
    }
