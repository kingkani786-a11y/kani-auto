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


def years_to_expiry(expiry: str, close_hour: int = 15, close_minute: int = 30) -> float:
    """The one Expiry Clock: Expiry Date + exchange close time + current time
    → years remaining, for every Black-Scholes Greeks/IV calculation.

    Was duplicated near-identically in engines/index_analytics.py and
    engines/strike_selector.py (RC1.16 follow-up) — same formula, two copies,
    one already-fixed-for-timezone but still two places to drift apart."""
    try:
        exp = datetime.datetime.fromisoformat(expiry).replace(
            hour=close_hour, minute=close_minute, second=0, microsecond=0, tzinfo=IST)
        return max((exp - now()).total_seconds() / (365.0 * 86400.0), 1e-5)
    except ValueError:
        return 7 / 365
