"""EOD AI Report — the first Tier-3 consumer of the Cortex.

Assembles the day's MEASURED performance (daily review, report card, gate
verdict stats) into a structured context and asks the Cortex (Reviewer role)
to write an honest end-of-day review. All numbers come from existing ledgers —
the LLM writes prose over them, it never invents figures.

This is a scheduled/on-demand consumer, never on the decision path.
"""
from __future__ import annotations

from typing import Any

from .. import validation, verdicts
from . import context_builder
from .provider import cortex


def _eod_context() -> dict[str, Any]:
    review = _safe(validation.daily_review)
    card = _safe(validation.report_card)
    vstats = _safe(verdicts.report)
    return {
        "snapshot": context_builder.build_snapshot(),
        "daily_review": review,
        "report_card": card,
        "gate_verdicts": {
            # keep the summary numbers, drop verbose per-item arrays
            k: v for k, v in (vstats or {}).items()
            if not isinstance(v, list)
        },
    }


def _safe(fn) -> dict[str, Any]:
    try:
        return fn() or {}
    except Exception as e:
        return {"error": str(e)}


def eod_report(max_tokens: int = 1200) -> dict[str, Any]:
    """Generate the end-of-day AI report (or an honest disabled/capped note)."""
    ctx = _eod_context()
    question = (
        "Write today's end-of-day review for the trader. Cover: how many "
        "decisions and their measured accuracy; which modules helped or hurt "
        "(with the measured figure); the single clearest lesson; and one thing "
        "to watch tomorrow. Ground every claim in the numbers above — if a "
        "number is missing or says 'building', say so plainly instead of "
        "guessing. Keep it under 250 words, warm and direct."
    )
    res = cortex.ask("reviewer", ctx, question, max_tokens=max_tokens)
    res["context_used"] = {
        "decisions": (ctx["daily_review"] or {}).get("total")
        or (ctx["daily_review"] or {}).get("decisions"),
        "has_report_card": bool(ctx["report_card"]),
        "verdict_samples": (ctx["gate_verdicts"] or {}).get("settled")
        or (ctx["gate_verdicts"] or {}).get("total"),
    }
    return res
