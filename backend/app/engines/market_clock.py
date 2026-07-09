"""V28 §6 — AI Market Clock.

Maps the current IST time to the session phase a desk thinks in — Open Drive,
Trend Confirm, Institution Build, Range/Lunch, Breakout Window, Power Hour,
Exit-Only. Derivation-only (clock + market hours); tells the trader which
behaviour to expect and which window is active.
"""
from __future__ import annotations

import datetime
from typing import Any

from ..core.clock import IST

# (start "HH:MM", phase, expected behaviour) for INDEX (09:15–15:30 IST)
_PHASES = [
    ("09:15", "Open Drive", "High volatility, fast moves — avoid chasing"),
    ("09:45", "Trend Confirm", "Direction firming — best clean entries"),
    ("11:00", "Institution Build", "Smart-money positioning — follow strength"),
    ("12:30", "Range / Lunch", "Low volume chop — scalps only, tighten filters"),
    ("13:30", "Afternoon Trend", "Trend resumption — re-entries"),
    ("14:30", "Breakout Window", "Expiry/late-day breakouts — runners possible"),
    ("15:00", "Power Hour", "Strong directional + reversals — manage risk"),
    ("15:20", "Exit Only", "Square-off window — no fresh entries"),
]


def _to_min(hhmm: str) -> int:
    h, m = hhmm.split(":")
    return int(h) * 60 + int(m)


def now_phase(market_type: str = "INDEX") -> dict[str, Any]:
    now = datetime.datetime.now(IST)
    cur = now.hour * 60 + now.minute
    open_m, close_m = _to_min("09:15"), _to_min("15:30")
    if market_type == "COMMODITY":
        open_m, close_m = _to_min("09:00"), _to_min("23:30")

    is_open = open_m <= cur <= close_m and now.weekday() < 5
    current, nxt = None, None
    timeline = []
    for i, (start, phase, beh) in enumerate(_PHASES):
        sm = _to_min(start)
        em = _to_min(_PHASES[i + 1][0]) if i + 1 < len(_PHASES) else close_m
        active = is_open and sm <= cur < em
        if active:
            current = {"phase": phase, "behaviour": beh, "start": start,
                       "ends": _PHASES[i + 1][0] if i + 1 < len(_PHASES) else "15:30",
                       "minutes_left": max(0, em - cur)}
        elif is_open and cur < sm and nxt is None:
            nxt = {"phase": phase, "start": start, "in_min": sm - cur}
        timeline.append({"start": start, "phase": phase, "active": active})

    return {
        "ready": True,
        "is_open": is_open,
        "ist_time": now.strftime("%H:%M"),
        "current": current or ({"phase": "Closed", "behaviour": "Market closed"} if not is_open else None),
        "next": nxt,
        "timeline": timeline,
        "no_fresh_entries": (current or {}).get("phase") == "Exit Only" if current else (not is_open),
        "note": "Session-phase clock — expected behaviour by time of day. Derivation-only.",
    }
