"""AI Analysis — Gemini explains the live decision, on the dashboard + radio.

Owner directive: use the live Gemini API to analyse the engine's data and
surface the answer on the dashboard (and let the radio speak it). This is the
Cortex "explainer" role, but CACHED so it costs almost nothing:

  • the cache key is (symbol, decision-band, market-open) — while the engine's
    decision hasn't materially changed, repeated dashboard polls return the
    SAME cached answer with zero new Gemini calls;
  • a minimum interval also guards against rapid band flips.

So the dashboard can poll every 60s cheaply; a fresh Gemini call happens only
when the decision actually changes (or on manual refresh). Doctrine intact:
the engine decides, Gemini only phrases; Safety + Cost caps wrap every call.
"""
from __future__ import annotations

import time
from typing import Any

from ...core.state import state
from . import context_builder
from .provider import cortex, cortex_status

_cache: dict[str, Any] = {"key": None, "ts": 0.0, "result": None}
_MIN_INTERVAL = 180.0  # seconds — never re-call Gemini for the same view faster than this


def _key(snap: dict[str, Any]) -> str:
    m = snap.get("market") or {}
    st = snap.get("status") or {}
    return f"{m.get('symbol')}|{m.get('decision')}|{st.get('market')}|{st.get('data_quality')}"


def analyze(force: bool = False) -> dict[str, Any]:
    """Return a natural-language analysis of the CURRENT decision (cached)."""
    if not cortex_status().get("enabled"):
        return {"ok": False, "disabled": True,
                "error": "AI Cortex not configured (no API key).",
                "cached": False}

    snap = context_builder.build_snapshot()
    key = _key(snap)
    age = time.time() - _cache["ts"]
    # Serve cache when the decision-view is unchanged (or too soon to re-call).
    if not force and _cache["result"] and (_cache["key"] == key or age < _MIN_INTERVAL):
        out = dict(_cache["result"])
        out["cached"] = True
        out["cache_age_sec"] = int(age)
        return out

    question = (
        "In 3-4 short sentences, explain the engine's CURRENT decision to the "
        "trader: what the trend/liquidity/structure show, why the decision is "
        f"'{(snap.get('market') or {}).get('decision')}', and the single most "
        "important thing to watch next. Use the snapshot only; if the market is "
        "closed or data is null, say so plainly. Do NOT tell the trader to "
        "buy/sell — explain the engine's reasoning. Tanglish."
    )
    res = cortex.ask("explainer", {"snapshot": snap}, question, max_tokens=500)
    res["cached"] = False
    res["decision_key"] = key
    if res.get("ok"):
        _cache.update(key=key, ts=time.time(), result=res)
    return res


def latest_text() -> str | None:
    """The last analysis text (for the radio to speak), or None."""
    r = _cache.get("result")
    return r.get("text") if r and r.get("ok") else None
