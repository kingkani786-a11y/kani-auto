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
                text, in_tok, out_tok, finish_reason = _ask_gemini(key, model, system, user, mt)
            else:
                text, in_tok, out_tok, finish_reason = _ask_anthropic(key, model, system, user, mt)
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
            # Bug fix follow-up, 2026-07-29: a caller-authoritative truncation
            # signal, from the provider's own finish/stop reason — cheaper and
            # more direct than only inferring truncation from parsed content
            # (which still stays as defense-in-depth in analysis.py).
            "finish_reason": finish_reason,
            "truncated": finish_reason in _BAD_FINISH,
            **safety.guard(text, snapshot),
        }


_THINKING_UNSUPPORTED = False   # learned at runtime; see _ask_gemini

# Provider-specific finish/stop reasons that mean "the reply is not safe to
# trust as complete" — cut off by the token budget, or blocked/filtered.
# STOP (Gemini) / end_turn, stop_sequence (Anthropic) are normal completion
# and are deliberately NOT in this set.
_BAD_FINISH = {"MAX_TOKENS", "SAFETY", "RECITATION", "PROHIBITED_CONTENT",
               "max_tokens", "refusal"}


def _ask_gemini(key: str, model: str, system: str, user: str,
                max_tokens: int) -> tuple[str, int, int, str | None]:
    # New official SDK (google-genai). The old google-generativeai is EOL.
    from google import genai  # lazy
    from google.genai import types

    client = genai.Client(api_key=key)
    # Disable "thinking" — these are phrasing/explain tasks, not reasoning; on
    # flash models thinking silently eats the output-token budget and truncates
    # the answer. thinking_budget=0 frees the full budget for the reply.
    #
    # 2026-07-22: this started returning 400 INVALID_ARGUMENT with no code
    # change on our side. `gemini-flash-latest` is a FLOATING ALIAS — Google
    # repointed it to a model that rejects thinking_budget. Verified by
    # bisection: identical request WITH thinking_config → 400, WITHOUT → OK.
    # The old guard only caught errors CONSTRUCTING ThinkingConfig, never the
    # API rejecting it, so the whole AI layer went dark instead of degrading.
    # Now: try it, and if the model refuses, remember that and retry once
    # without. Self-healing across future alias moves in either direction.
    # When thinking cannot be disabled it still consumes max_output_tokens.
    # Measured 2026-07-22 on this alias: ~240-290 tokens of thought BEFORE any
    # answer. At the old 64-token budget the reply truncated mid-word
    # ("Goodbye my", finish=MAX_TOKENS, out=2). Headroom is therefore not
    # optional once thinking is forced on — it is what makes the answer exist.
    global _THINKING_UNSUPPORTED
    _budget = max_tokens if not _THINKING_UNSUPPORTED else max(max_tokens + 400, 512)
    cfg = dict(system_instruction=system, max_output_tokens=_budget, temperature=0.4)
    used_thinking = False
    if not _THINKING_UNSUPPORTED:
        try:
            cfg["thinking_config"] = types.ThinkingConfig(thinking_budget=0)
            used_thinking = True
        except Exception:
            cfg.pop("thinking_config", None)

    def _call(c: dict):
        return client.models.generate_content(
            model=model, contents=user, config=types.GenerateContentConfig(**c))

    try:
        resp = _call(cfg)
    except Exception as e:
        if used_thinking and "INVALID_ARGUMENT" in str(e):
            _THINKING_UNSUPPORTED = True          # learn once, not every call
            cfg.pop("thinking_config", None)
            cfg["max_output_tokens"] = max(max_tokens + 400, 512)   # room to think AND answer
            resp = _call(cfg)                     # degrade, never go dark
        else:
            raise
    text = (getattr(resp, "text", "") or "").strip()
    um = getattr(resp, "usage_metadata", None)
    in_tok = int(getattr(um, "prompt_token_count", 0) or 0)
    out_tok = int(getattr(um, "candidates_token_count", 0) or 0)
    candidates = getattr(resp, "candidates", None) or []
    fr = getattr(candidates[0], "finish_reason", None) if candidates else None
    finish_reason = getattr(fr, "value", None) or (str(fr) if fr is not None else None)
    return text, in_tok, out_tok, finish_reason


def _ask_anthropic(key: str, model: str, system: str, user: str,
                   max_tokens: int) -> tuple[str, int, int, str | None]:
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
    return text, in_tok, out_tok, getattr(msg, "stop_reason", None)


cortex = Cortex()
