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

    decision = (snap.get("market") or {}).get("decision")
    question = (
        "Output ONLY these 4 lines, nothing before or after, keep the labels "
        "EXACTLY, each one short Tanglish sentence:\n"
        f"WHY: why the engine decided '{decision}'\n"
        "NEXT: the likely near-term path\n"
        "WATCH: the single key level or signal to watch\n"
        "CHANGE: what would flip the decision (e.g. Liquidity >55 makes BUY ready)\n"
        "Rules: always emit all 4 lines with their labels even if the market is "
        "closed or data is null (then say that honestly inside the lines). Never "
        "tell the trader to buy or sell — explain the engine only."
    )
    res = cortex.ask("explainer", {"snapshot": snap}, question, max_tokens=700)
    res["cached"] = False
    res["decision_key"] = key
    if res.get("ok"):
        res["blocks"] = _parse_blocks(res.get("text", ""))
        _cache.update(key=key, ts=time.time(), result=res)
    return res


def _parse_blocks(text: str) -> dict[str, str]:
    """Split the 4-block reply into {why,next,watch,change}. Tolerant: falls
    back to leaving blocks empty (the card shows the raw text then)."""
    out: dict[str, str] = {}
    labels = {"why": "why", "next": "next", "watch": "watch", "change": "change"}
    for line in (text or "").splitlines():
        s = line.strip().lstrip("-*• ").strip()
        for lab in labels:
            pre = lab + ":"
            if s.lower().startswith(pre):
                out[lab] = s[len(pre):].strip()
                break
    return out


def latest_text() -> str | None:
    """The last analysis text (for the radio to speak), or None."""
    r = _cache.get("result")
    return r.get("text") if r and r.get("ok") else None
