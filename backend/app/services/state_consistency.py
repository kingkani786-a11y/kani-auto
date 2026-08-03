"""State Consistency Detector — P5A (owner, 2026-08-03, "State Consistency").

Read-only, additive, gate-adjacent-nothing: this file does not import or
touch kill_switch.py, safe_mode.py, confluence.py, execution_gate.py, or
market_service.py. It only READS state.data_quality and calls
data_quality.report() — the exact same two calls FeedDiagnostics.tsx already
makes over the wire — and reports whether they agree.

Why this exists: the 2026-08-03 review found the SAME underlying bug shape
recurring across a whole session of otherwise-unrelated audits — a duplicated
fact with no single source of truth (state.data_quality vs
data_quality.report().overall; Kill Switch/Safe Mode/Gate echoing one cause
three ways; Order Flow's low-data default sharing its real baseline). The
owner's own framing: manual audit found each instance one at a time; a
runtime detector should say "state inconsistency detected" instead, so the
NEXT instance of this bug class doesn't need a fresh manual audit to surface.

v1 registers exactly ONE check — the one already CONFIRMED to have caused a
real dashboard contradiction (2026-08-03 morning: FeedDiagnostics said "all
feeds healthy" while Kill Switch/Safe Mode were vetoing on data quality).
Designed so more checks can be added as a plain list of functions, not so
hypothetical checks get built ahead of a real second instance.
"""
from __future__ import annotations

from typing import Any

from ..core.state import state, is_market_open


def _check_data_quality_dual_source() -> dict[str, Any]:
    """A = state.data_quality (set by market_service._safe()'s try/except —
    "did the last tick raise BrokerError?"). B = data_quality.report().overall
    (the 8 per-stream freshness checks — what kill_switch/safe_mode/the gate's
    own "Data Quality" row are actually evaluated against). These are
    DIFFERENT measurements that usually agree; when they don't, at least one
    panel reading only A is silently wrong, exactly as FeedDiagnostics was.

    Market-closed is excluded from the hard-contradiction check on purpose —
    A reads "CLOSED" while B has no CLOSED state and idle feeds routinely
    read DEGRADED/POOR there; that is expected (same doctrine as RC1.11/
    RC1.14/kill_switch.py's own market_closed_note), not an inconsistency."""
    from . import data_quality

    a = state.data_quality
    b = data_quality.report().get("overall")
    market_open = is_market_open(state.market_type)

    # The specific, confirmed-dangerous shape: one side says fine, the other
    # says hard-broken, while the market is actually open to trade on.
    hard_contradiction = (
        market_open
        and ((a == "GOOD" and b == "POOR") or (a == "POOR" and b == "GOOD"))
    )
    return {
        "name": "data_quality_dual_source",
        "label": "Data Quality (state.data_quality vs data_quality.report())",
        "value_a": a, "source_a": "state.data_quality",
        "value_b": b, "source_b": "data_quality.report().overall",
        "market_open": market_open,
        "consistent": not hard_contradiction,
        "note": ("These two data-quality reads disagree in a way that changes "
                 "what a trader should believe: one side reports fine, the "
                 "other reports a hard fault, while the market is open."
                 if hard_contradiction else
                 "Agree, or differ only in a way already treated as expected "
                 "(e.g. market closed)."),
    }


_CHECKS = [_check_data_quality_dual_source]


def report() -> dict[str, Any]:
    checks = [c() for c in _CHECKS]
    inconsistent = [c for c in checks if not c["consistent"]]
    return {
        "consistent": not inconsistent,
        "checks": checks,
        "inconsistent_count": len(inconsistent),
    }
