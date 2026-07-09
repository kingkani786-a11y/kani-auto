"""RC1.16 Single Time Service.

Every wall-clock read in this codebase must funnel through here instead of
constructing its own `zoneinfo.ZoneInfo(...)` — before this existed, 12 files
each independently built an IST timezone object. All happened to agree, but
nothing structurally guaranteed that; a single stray `datetime.now()" (naive,
server-OS-timezone) already caused two genuine bugs in Greeks time-to-expiry
(RC1.16 finding #1). One source, one policy (Rule 10).
"""
from __future__ import annotations

import datetime
import zoneinfo

IST = zoneinfo.ZoneInfo("Asia/Kolkata")
NY = zoneinfo.ZoneInfo("America/New_York")   # US-session clock only (global_feed)


def now() -> datetime.datetime:
    """Current wall-clock time, always IST, always tz-aware."""
    return datetime.datetime.now(IST)


def today_str(ts: float | None = None) -> str:
    """Calendar-date string for an epoch timestamp (defaults to now), in IST —
    the single day-boundary rule every daily grouping/reset in this app uses."""
    dt = datetime.datetime.fromtimestamp(ts, IST) if ts is not None else now()
    return dt.strftime("%Y-%m-%d")


def midnight_today_ts() -> float:
    """Start of the current IST calendar day, as a Unix timestamp — the one
    definition of 'Today' for daily-reset windows (Rule 2: one metric, one
    meaning). Distinct from a rolling 24h window on purpose."""
    return now().replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
