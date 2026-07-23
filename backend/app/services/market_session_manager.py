"""V7 Market Independence — Phase A (owner, 2026-07-23; LTS freeze exception —
foundational measurement-integrity fix, not a new feature: without this, the
platform sits idle at NSE close even while a registered market is live).

Root cause this fixes: `state.market_type` previously only ever changed on an
explicit `set_symbol()` call (a user pick or the INDEX-only scanner ranking) —
nothing ever asked "is a DIFFERENT market open right now?". Every downstream
`is_market_open(state.market_type)` gate was already correct in isolation; it
was just answering the wrong question, because nothing kept `state.market_type`
pointed at whichever market is actually live.

Currency (CDS) is deliberately NOT in MARKET_PRIORITY — Dhan API/account
segment access is unverified (owner, 2026-07-23: "skip for now"). It appears in
`market_overview()` as an honest NOT_CONFIGURED entry, never fabricated as open
or closed.
"""
from __future__ import annotations

from typing import Any

from ..broker.instruments import INSTRUMENTS
from ..core.state import is_market_open, market_status

# Priority order the resolver checks, first-open-wins. Both already have real,
# working instrument coverage (INSTRUMENTS + resolve_commodities() contract
# auto-resolution) — this is a cascade over what already exists, not new
# market coverage.
MARKET_PRIORITY: tuple[str, ...] = ("INDEX", "COMMODITY")


def registered_market_types() -> list[str]:
    return sorted({i.market_type for i in INSTRUMENTS.values()})


def candidates_for(market_type: str) -> list[str]:
    """Symbols registered under a market_type — replaces the scanner's old
    hardcoded INDEX-only filter (scanner.py, fixed alongside this file)."""
    return [s for s, i in INSTRUMENTS.items() if i.market_type == market_type]


def resolve_active_market_type() -> str | None:
    """First market in MARKET_PRIORITY that is currently open. None if every
    registered market is closed right now — an honest WAIT, never a fabricated
    pick just to have something running."""
    for mt in MARKET_PRIORITY:
        if is_market_open(mt):
            return mt
    return None


def market_overview() -> dict[str, Any]:
    """Per-exchange open/closed status for the dashboard's 'Active Market' bar.
    Covers every market_type this resolver actually cascades over, PLUS an
    honest placeholder for Currency so the UI never silently omits a segment
    the owner asked about — it says why it's absent instead of hiding it."""
    out: dict[str, Any] = {mt: market_status(mt) for mt in registered_market_types()}
    out["CURRENCY"] = {
        "status": "NOT_CONFIGURED",
        "market_type": "CURRENCY",
        "is_open": False,
        "reason": "Dhan CDS segment access not verified — parked (owner, 2026-07-23)",
    }
    return out
