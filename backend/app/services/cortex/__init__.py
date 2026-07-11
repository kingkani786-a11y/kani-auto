"""AI Cortex — Proposal #013 Phase A (provider-agnostic LLM layer).

Doctrine (owner-locked, docs/AI_OS_VISION.md):
  • The LLM is a CORTEX, never the spine. It only Explains / Researches /
    Reviews / Teaches / Summarizes / Reports. It NEVER emits BUY/SELL/SL/
    strike and NEVER overrides the execution gate.
  • It is a CONSUMER of published, structured state (Rule 10) — it never
    receives raw candles or market data.
  • It NEVER runs on the decision path — only on-demand / scheduled endpoints.
  • Disabled unless an API key is present; the engine is unaffected either way.

Phase A modules:
  context_builder  — assemble the structured snapshot (published state only)
  safety           — code-enforced hard NOs on LLM output (not prompt trust)
  cost_controller  — per-call + daily ₹/call caps with an IST-day ledger
  provider         — Cortex.ask(role, context, question); Gemini | Anthropic
  report           — EOD AI Report consumer (first Tier-3 consumer)
"""
from .provider import cortex, cortex_status  # noqa: F401
