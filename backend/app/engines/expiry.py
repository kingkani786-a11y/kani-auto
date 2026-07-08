"""Expiry Engine — gamma wall, max-pain shift, OI migration, pinning, squeeze."""
from __future__ import annotations

import datetime
from typing import Any

# remembers the previous chain digest per symbol to detect shifts/migration
_prev: dict[str, dict] = {}


def analyze(symbol: str, analytics: dict[str, Any], spot: float) -> dict[str, Any]:
    chain = (analytics or {}).get("chain") or []
    if not chain or not spot:
        return {"notes": [], "events": []}

    notes: list[str] = []
    events: list[str] = []

    # ---- gamma wall: strike with the heaviest combined OI near money ----
    # (OI concentration is the practical proxy for dealer gamma at a strike)
    wall = max(chain, key=lambda r: r["ce_oi"] + r["pe_oi"])
    gamma_wall = wall["strike"]
    if abs(gamma_wall - spot) / spot < 0.01:
        events.append("GAMMA_WALL_NEAR")
        notes.append(f"Gamma wall at {gamma_wall:.0f} — expect price magnetism and pinning near this strike")

    # ---- max pain shift + OI migration vs previous snapshot ----
    prev = _prev.get(symbol) or {}
    max_pain = analytics.get("max_pain")
    if prev.get("max_pain") and max_pain and prev["max_pain"] != max_pain:
        d = "up" if max_pain > prev["max_pain"] else "down"
        events.append("MAX_PAIN_SHIFT")
        notes.append(f"Max pain shifted {d}: {prev['max_pain']:.0f} → {max_pain:.0f}")

    prev_atm = prev.get("atm")
    atm = analytics.get("atm_strike")
    if prev.get("chain") and atm and prev_atm:
        def oi_above_below(rows: list[dict], ref: float) -> tuple[float, float]:
            above = sum(r["pe_oi"] for r in rows if r["strike"] > ref)
            below = sum(r["pe_oi"] for r in rows if r["strike"] < ref)
            return above, below
        a_now, b_now = oi_above_below(chain, atm)
        a_prev, b_prev = oi_above_below(prev["chain"], prev_atm)
        if b_prev and b_now / max(b_prev, 1) > 1.08 and a_now / max(a_prev, 1) < 1.0:
            events.append("OI_MIGRATION_LOWER")
            notes.append("Put OI migrating to lower strikes — support stepping down")
        elif a_prev and a_now / max(a_prev, 1) > 1.08:
            events.append("OI_MIGRATION_HIGHER")
            notes.append("Put OI migrating to higher strikes — support stepping up")

    # ---- expiry-day dynamics ----
    expiry = analytics.get("expiry")
    dte = None
    if expiry:
        try:
            dte = (datetime.date.fromisoformat(expiry) - datetime.date.today()).days
        except ValueError:
            pass
    if dte == 0:
        if max_pain and abs(spot - max_pain) / spot < 0.004:
            events.append("EXPIRY_PINNING")
            notes.append(f"Expiry pinning active around max pain {max_pain:.0f}")
        # squeeze: price far from max pain late in expiry = forced hedging moves
        if max_pain and abs(spot - max_pain) / spot > 0.012:
            events.append("EXPIRY_SQUEEZE_RISK")
            notes.append("Price stretched far from max pain on expiry day — squeeze/unwind risk elevated")

    _prev[symbol] = {"max_pain": max_pain, "atm": atm, "chain": chain}
    return {
        "gamma_wall": gamma_wall,
        "max_pain": max_pain,
        "days_to_expiry": dte,
        "events": events,
        "notes": notes,
    }
