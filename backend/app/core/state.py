"""Single source of truth for runtime state.

Nothing in the app runs until `connected` is True, which only happens after
the user clicks SAVE & CONNECT and the credentials validate against the
broker. Disconnecting (or saving a new token) tears everything down and
rebuilds it without a process restart.
"""
from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from typing import Any


@dataclass
class Credentials:
    client_id: str = ""
    access_token: str = ""

    @property
    def present(self) -> bool:
        return bool(self.client_id and self.access_token)


@dataclass
class AppState:
    credentials: Credentials = field(default_factory=Credentials)
    connected: bool = False
    connected_at: float = 0.0
    market_type: str = "INDEX"          # INDEX | COMMODITY
    symbol: str = "NIFTY"

    # Latest computed snapshots, keyed for the dashboard
    spot: dict[str, Any] = field(default_factory=dict)
    option_chain: dict[str, Any] = field(default_factory=dict)
    greeks: dict[str, Any] = field(default_factory=dict)
    analytics: dict[str, Any] = field(default_factory=dict)
    smart_money: dict[str, Any] = field(default_factory=dict)
    signal: dict[str, Any] = field(default_factory=dict)
    decision: dict[str, Any] = field(default_factory=dict)
    risk: dict[str, Any] = field(default_factory=dict)
    candles: list[dict[str, Any]] = field(default_factory=list)
    intelligence: dict[str, Any] = field(default_factory=dict)  # full X-engine packet
    scalp: dict[str, Any] = field(default_factory=dict)         # Scalp Radar V2 (independent)
    exit_intel: dict[str, Any] = field(default_factory=dict)    # Exit Intelligence (in-trade)
    heartbeats: dict[str, float] = field(default_factory=dict)  # engine -> last success ts
    watchlist: list[str] = field(default_factory=list)
    favorites: list[str] = field(default_factory=list)
    data_quality: str = "UNKNOWN"       # GOOD | DEGRADED | POOR
    kill_switch: dict[str, Any] = field(default_factory=dict)   # Phase 14 — capital-protection veto
    market_dna: dict[str, Any] = field(default_factory=dict)    # Phase 20 — historical-similarity match
    simulator: dict[str, Any] = field(default_factory=dict)     # Phase 29 — today/tomorrow scenarios
    safe_mode: dict[str, Any] = field(default_factory=dict)     # Phase D — disaster-recovery safe mode
    opportunities: dict[str, Any] = field(default_factory=dict)  # V26 — market opportunity board

    # Background task handles owned by MarketService
    tasks: list[asyncio.Task] = field(default_factory=list)

    def status(self) -> dict[str, Any]:
        return {
            "connected": self.connected,
            "connected_since": self.connected_at,
            "market_type": self.market_type,
            "symbol": self.symbol,
            "market_open": is_market_open(self.market_type),
            "data_quality": self.data_quality,
            "kill_switch": self.kill_switch,
            "safe_mode": self.safe_mode,
            "market_status": market_status(self.market_type),
            "last_close": (self.spot or {}).get("ref") or (self.spot or {}).get("ltp"),
            "server_time": time.time(),
        }


def is_market_open(market_type: str) -> bool:
    """IST market hours. Index: 09:15–15:30 Mon–Fri. MCX: 09:00–23:30."""
    import datetime, zoneinfo

    now = datetime.datetime.now(zoneinfo.ZoneInfo("Asia/Kolkata"))
    if now.weekday() >= 5:
        return False
    t = now.time()
    if market_type == "COMMODITY":
        return datetime.time(9, 0) <= t <= datetime.time(23, 30)
    return datetime.time(9, 15) <= t <= datetime.time(15, 30)


def market_status(market_type: str) -> dict[str, Any]:
    """OPEN / CLOSED status + the next open time and a countdown (seconds).
    Used so the UI can show a calm 🟡 MARKET CLOSED with a timer, not an error."""
    import datetime, zoneinfo

    tz = zoneinfo.ZoneInfo("Asia/Kolkata")
    now = datetime.datetime.now(tz)
    open_t = datetime.time(9, 0) if market_type == "COMMODITY" else datetime.time(9, 15)
    is_open = is_market_open(market_type)

    # find the next open datetime (skip weekends)
    candidate = now.replace(hour=open_t.hour, minute=open_t.minute, second=0, microsecond=0)
    if now >= candidate or now.weekday() >= 5:
        candidate = candidate + datetime.timedelta(days=1)
    while candidate.weekday() >= 5:
        candidate = candidate + datetime.timedelta(days=1)

    next_open = candidate if not is_open else None
    secs = int((candidate - now).total_seconds()) if next_open else 0
    return {
        "status": "OPEN" if is_open else "CLOSED",
        "market_type": market_type,
        "is_open": is_open,
        "ist_time": now.strftime("%H:%M:%S"),
        "next_open_ist": next_open.strftime("%a %H:%M") if next_open else None,
        "seconds_to_open": secs,
        "weekend": now.weekday() >= 5,
    }


state = AppState()
