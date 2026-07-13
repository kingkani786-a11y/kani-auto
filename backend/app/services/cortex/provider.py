"""Cortex — the provider-agnostic LLM interface.

One method: `cortex.ask(role, context, question)`. Behind it, a Gemini adapter
and an Anthropic adapter, chosen by whichever key is configured. Switching
providers is a config change (CAT_AI_PROVIDER + the matching CAT_*_API_KEY),
never a rewrite — this is the owner's locked provider-agnostic design.

SDKs are imported LAZILY inside each adapter so the backend runs perfectly
with no AI configured and no SDK installed. When disabled, every call returns
an honest "AI layer not configured" payload — the engine is never affected.

Enforcement wired in here so NO caller can bypass it:
  • Cost Controller check() before the call, record() after
  • Safety Layer guard() on every returned text
  • System prompt = the owner's Master Prompt (hard NOs)
"""
from __future__ import annotations

import json
import time
from typing import Any

from ...config import settings
from . import cost_controller as cost
from . import safety
from .prompts import MASTER_PROMPT, ROLE_PROMPTS

# gemini-flash-latest is an always-current alias (cheap flash tier) — the
# dated gemini-2.5-flash is closed to new keys.
_DEFAULT_MODEL = {"gemini": "gemini-flash-latest", "anthropic": "claude-opus-4-8"}


def _resolve_provider() -> tuple[str, str, str]:
    """Return (provider, api_key, model) or ('', '', '') when disabled."""
    prov = (settings.ai_provider or "").strip().lower()
    gem = settings.gemini_api_key.strip()
    ant = settings.anthropic_api_key.strip()
    if not prov:  # auto-detect from whichever key is present
        if gem:
            prov = "gemini"
        elif ant:
            prov = "anthropic"
    key = gem if prov == "gemini" else ant if prov == "anthropic" else ""
    if not prov or not key:
        return "", "", ""
    model = (settings.ai_model or "").strip() or _DEFAULT_MODEL.get(prov, "")
    return prov, key, model


def cortex_status() -> dict[str, Any]:
    prov, key, model = _resolve_provider()
    return {
        "enabled": bool(prov and key),
        "provider": prov or None,
        "model": model or None,
        "roles": sorted(ROLE_PROMPTS.keys()),
        "budget": cost.report(),
        "note": ("AI Cortex active — explanation/research only, never the "
                 "decision path." if prov and key else
                 "AI Cortex OFF — add CAT_GEMINI_API_KEY or "
                 "CAT_ANTHROPIC_API_KEY to backend/.env to enable. The "
                 "trading engine runs identically without it."),
    }


class Cortex:
    def ask(self, role: str, context: dict[str, Any], question: str,
            max_tokens: int | None = None) -> dict[str, Any]:
        prov, key, model = _resolve_provider()
        snapshot = (context or {}).get("snapshot") or {}
        if not prov:
            return {"ok": False, "disabled": True,
                    "error": "AI Cortex not configured (no API key).",
                    **safety.guard("", snapshot)}

        gate = cost.check()
        if not gate["allowed"]:
            return {"ok": False, "capped": True, "error": gate["reason"],
                    "budget": cost.report(), **safety.guard("", snapshot)}

        role_prompt = ROLE_PROMPTS.get(role, ROLE_PROMPTS["explainer"])
        system = f"{MASTER_PROMPT}\n\n# YOUR ROLE\n{role_prompt}"
        user = (
            "STRUCTURED MARKET SNAPSHOT (the ONLY source of truth — do not "
            "invent data beyond this):\n"
            f"{json.dumps(context, ensure_ascii=False, indent=2)}\n\n"
            f"TASK: {question}\n\n"
            "Answer using only the snapshot. If the snapshot lacks something, "
            "say so honestly — never fabricate. Do not issue trade "
            "instructions; explain the engine's decision instead."
        )
        mt = int(max_tokens or settings.ai_max_output_tokens)
        t0 = time.time()
        try:
            if prov == "gemini":
                text, in_tok, out_tok = _ask_gemini(key, model, system, user, mt)
            else:
                text, in_tok, out_tok = _ask_anthropic(key, model, system, user, mt)
        except Exception as e:  # never crash a request path
            es = str(e)
            # Transient upstream errors (high demand / rate limit) → soft,
            # friendly message + a flag so the UI can show "retrying" not a dump.
            transient = any(k in es for k in ("503", "UNAVAILABLE", "429",
                                              "overloaded", "high demand", "RESOURCE_EXHAUSTED"))
            msg = ("AI temporarily busy (high demand) — retrying automatically."
                   if transient else f"{prov} call failed: {es}")
            return {"ok": False, "error": msg, "transient": transient,
                    **safety.guard("", snapshot)}

        inr = cost.record(role, model, in_tok, out_tok)
        return {
            "ok": True, "provider": prov, "model": model, "role": role,
            "latency_ms": int((time.time() - t0) * 1000),
            "usage": {"input_tokens": in_tok, "output_tokens": out_tok,
                      "cost_inr": inr},
            "budget": cost.report(),
            **safety.guard(text, snapshot),
        }


def _ask_gemini(key: str, model: str, system: str, user: str,
                max_tokens: int) -> tuple[str, int, int]:
    # New official SDK (google-genai). The old google-generativeai is EOL.
    from google import genai  # lazy
    from google.genai import types

    client = genai.Client(api_key=key)
    # Disable "thinking" — these are phrasing/explain tasks, not reasoning; on
    # flash models thinking silently eats the output-token budget and truncates
    # the answer. thinking_budget=0 frees the full budget for the reply.
    cfg = dict(system_instruction=system, max_output_tokens=max_tokens, temperature=0.4)
    try:
        cfg["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
    except Exception:
        pass
    resp = client.models.generate_content(
        model=model, contents=user,
        config=types.GenerateContentConfig(**cfg),
    )
    text = (getattr(resp, "text", "") or "").strip()
    um = getattr(resp, "usage_metadata", None)
    in_tok = int(getattr(um, "prompt_token_count", 0) or 0)
    out_tok = int(getattr(um, "candidates_token_count", 0) or 0)
    return text, in_tok, out_tok


def _ask_anthropic(key: str, model: str, system: str, user: str,
                   max_tokens: int) -> tuple[str, int, int]:
    import anthropic  # lazy

    client = anthropic.Anthropic(api_key=key)
    msg = client.messages.create(
        model=model,
        max_tokens=max_tokens,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(b.text for b in msg.content if getattr(b, "type", "") == "text").strip()
    in_tok = int(getattr(msg.usage, "input_tokens", 0) or 0)
    out_tok = int(getattr(msg.usage, "output_tokens", 0) or 0)
    return text, in_tok, out_tok


cortex = Cortex()
