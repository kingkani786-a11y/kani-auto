"""Safety Layer — code-enforced hard NOs on every LLM output.

Owner-locked (#014): the LLM must never ORIGINATE a trade instruction. This is
enforced HERE, at the code boundary — never by trusting the system prompt
alone (prompt-injection-safe by construction).

Enforcement:
  1. Scan the LLM text for imperative trade-directive patterns ("buy the X
     strike", "enter now", "place a stop loss at", "sell", "book profit at").
  2. If found, the response is FLAGGED (`safety.flagged=True`) and the offending
     phrases recorded; the caller renders the honest banner and the engine's
     real decision, never the LLM's directive.
  3. ALWAYS append the authoritative engine decision from the snapshot so the
     source of truth sits next to any narration.

The LLM output is only ever DATA rendered to the user — it is never parsed
into an action. This module makes that visible and auditable.
"""
from __future__ import annotations

import re
from typing import Any

# Imperative trade directives the LLM must not originate. These match a
# *command to act*, not a description of the engine's verdict. "The engine
# recommends WAIT" is fine; "you should buy the 25000 call" is flagged.
_DIRECTIVE_PATTERNS = [
    r"\b(you should|i (?:recommend|suggest|advise) (?:you )?(?:to )?)\s*(buy|sell|short|long|enter|exit)\b",
    r"\b(buy|sell|short|go long|go short)\s+(the\s+)?\d{3,6}\s*(ce|pe|call|put|strike)\b",
    r"\benter (?:now|immediately|the trade)\b",
    r"\bplace (?:a )?(?:stop[- ]?loss|sl|stoploss)\b",
    r"\bset (?:your )?(?:stop[- ]?loss|sl|target)\s+(?:at|to)\s*\d",
    r"\bbook (?:profit|profits)\s+(?:at|now)\b",
    r"\b(buy|sell)\s+now\b",
]
_COMPILED = [re.compile(p, re.IGNORECASE) for p in _DIRECTIVE_PATTERNS]


def scan(text: str) -> list[str]:
    """Return the list of directive phrases found (empty = clean)."""
    hits: list[str] = []
    for rx in _COMPILED:
        for m in rx.finditer(text or ""):
            hits.append(m.group(0).strip())
    return hits


def guard(text: str, snapshot: dict[str, Any] | None = None) -> dict[str, Any]:
    """Wrap an LLM response with the Safety Layer verdict + authoritative decision."""
    hits = scan(text or "")
    market = (snapshot or {}).get("market") or {}
    engine_decision = market.get("decision")
    return {
        "text": text or "",
        "safety": {
            "flagged": bool(hits),
            "directives_found": hits,
            "note": (
                "⚠️ The AI text contained trade-directive language, which the "
                "Cortex is not permitted to originate. Follow the engine "
                "decision below, not the AI text."
                if hits else
                "Clean — no trade directives (AI is explanation-only)."
            ),
        },
        "authoritative_decision": engine_decision,
        "authoritative_note": (
            "Trade decisions come ONLY from the Decision Engine + execution "
            "gate. This AI text is explanation/research, never an instruction."
        ),
    }
