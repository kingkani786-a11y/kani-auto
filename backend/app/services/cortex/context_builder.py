"""Context Builder — the ONLY bridge from the engine to the LLM.

Rule 10 (One State → One Source → One Truth → Many Consumers): the LLM is a
consumer. It receives ONLY the engine's already-published, structured snapshot
— never raw candles, never a broker payload. This is the owner's locked
Structured-Context contract (docs/AI_OS_VISION.md → #014 snapshot contract):

    { "market": {trend, trendScore, liquidity, liquidityScore,
                  structure, decision}, "blockers": [...],
      "confidence": N, "reason": [...] }

We enrich it with a few more published, non-sensitive fields (spot, symbol,
market status, kill-switch/safe-mode flags, module_stats) but NEVER anything
that lets the LLM originate a trade.
"""
from __future__ import annotations

from typing import Any

from ...core.state import market_status, state


def _f(v: Any) -> float | None:
    try:
        return round(float(v), 2)
    except (TypeError, ValueError):
        return None


def _layers() -> dict[str, Any]:
    return (state.intelligence or {}).get("layers") or {}


def _layer_score(*names: str) -> float | None:
    layers = _layers()
    for n in names:
        row = layers.get(n)
        if isinstance(row, dict):
            for k in ("score", "value", "pct", "strength"):
                if k in row:
                    return _f(row[k])
    return None


def build_snapshot() -> dict[str, Any]:
    """The owner's structured contract, assembled from published state only."""
    dec = state.decision or {}
    sig = state.signal or {}
    intel = state.intelligence or {}
    gate = (intel.get("execution_gate") or {})

    # Decision + blockers straight from the published decision/gate — the LLM
    # gets the engine's verdict, it does not compute one.
    decision = (dec.get("action") or dec.get("primary_action")
                or gate.get("band") or "WAIT")
    blockers = gate.get("blocking_reasons") or []
    if isinstance(blockers, dict):
        blockers = list(blockers.keys())
    reason = dec.get("reason")
    reason_list = (reason if isinstance(reason, list)
                   else [reason] if reason else [])

    conf = (_f(dec.get("conviction"))
            or _f((intel.get("confidence") or {}).get("value"))
            or _f(sig.get("confidence")))

    ms = market_status(state.market_type)

    snap = {
        "market": {
            "symbol": state.symbol,
            "spot": _f((state.spot or {}).get("ltp")),
            "trend": _layer_tag("trend"),
            "trendScore": _layer_score("Trend", "MTF Trend", "trend"),
            "liquidity": _layer_tag("liquidity"),
            "liquidityScore": _layer_score("Liquidity", "Order Flow", "liquidity"),
            "structure": _layer_tag("structure"),
            "decision": decision,
        },
        "blockers": list(blockers)[:8],
        "confidence": conf,
        "reason": [str(r) for r in reason_list][:8],
        "status": {
            "connected": state.connected,
            "market": ms["status"],
            "ist_time": ms["ist_time"],
            "data_quality": state.data_quality,
            "kill_switch_active": bool((state.kill_switch or {}).get("active")),
            "safe_mode_active": bool((state.safe_mode or {}).get("active")),
        },
    }
    return snap


def _layer_tag(kind: str) -> str | None:
    """A short human tag for a layer if the engine published one."""
    layers = _layers()
    keymap = {
        "trend": ("Trend", "MTF Trend"),
        "liquidity": ("Liquidity", "Order Flow"),
        "structure": ("Structure", "Market Structure"),
    }
    for n in keymap.get(kind, ()):
        row = layers.get(n)
        if isinstance(row, dict):
            for k in ("label", "state", "status", "verdict"):
                if row.get(k):
                    return str(row[k])
    return None


def build_context(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Snapshot + optional role-specific published extras (never raw data)."""
    ctx = {"snapshot": build_snapshot()}
    if extra:
        ctx.update(extra)
    return ctx
