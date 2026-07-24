"""Shared text-formatting helpers — the Single Time Source pattern (clock.py)
applied to display-string truncation.

Found 2026-07-24 (live owner report): four separate call sites — execution_
gate.py, execution_card.py, confluence.py, market_service.py — each did their
own plain `text[:N]` on a joined reason/alert string, cutting mid-word with
no ellipsis (e.g. "forecasts mis-tuned" -> "forecasts mis-tun"). One shared
function now, so this doesn't drift into a 5th copy with its own off-by-one.
"""
from __future__ import annotations


def truncate_at_word(text: str, limit: int) -> str:
    """Cut at the last space before `limit`, append an ellipsis. Falls back
    to a hard cut only if there's no space to break on (single long token)."""
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return (cut or text[:limit]) + "…"
