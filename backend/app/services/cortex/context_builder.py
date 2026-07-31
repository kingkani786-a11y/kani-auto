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


def _dm_rows() -> list[dict[str, Any]]:
    """The AI Decision Matrix's own per-layer rows (already computed once per
    cycle by engines/intelligence.py._decision_matrix) — the SAME structure
    opportunity_metrics.py/decision_contract.py/risk_approval.py already walk
    for this exact reason: 'Trend'/'Structure'/'Liquidity' only exist as
    `layer` entries here, never as top-level keys of _layers()."""
    return ((_layers().get("intelligence") or {})
            .get("decision_matrix") or {}).get("rows") or []


def _layer_score(*names: str) -> float | None:
    # Bug fix (2026-07-31): this used to look for row["score"/"value"/"pct"/
    # "strength"] on layers.get("Trend")/layers.get("Liquidity")/etc directly
    # — but no key named "Trend"/"Liquidity"/"Structure" has ever existed at
    # that level (the raw per-engine dicts are keyed lowercase — "trend",
    # "structure", "order_flow" — with entirely different field names). So
    # market.trendScore/liquidityScore were null in every Gemini call ever
    # made, confirmed live: Gemini correctly reported "trend data null" from
    # this same broken input while the dashboard's own AI Decision Matrix
    # showed real Trend/Structure/Liquidity values via decision_matrix.rows.
    rows = _dm_rows()
    for n in names:
        for r in rows:
            if r.get("layer") == n and r.get("score") is not None:
                return _f(r["score"])
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
            "trend": _layer_tag("Trend"),
            "trendScore": _layer_score("Trend"),
            "liquidity": _layer_tag("Liquidity"),
            "liquidityScore": _layer_score("Liquidity"),
            "structure": _layer_tag("Structure"),
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


def _layer_tag(*names: str) -> str | None:
    """A short human tag for a decision-matrix row, if one was published —
    the SAME `reason` text already shown on the AI Decision Matrix panel
    for this exact row (e.g. Trend's reason is its BULLISH/BEARISH/NEUTRAL
    read). See _dm_rows()'s docstring for why this reads decision_matrix.rows
    rather than a top-level _layers() key."""
    rows = _dm_rows()
    for n in names:
        for r in rows:
            if r.get("layer") == n:
                reason = r.get("reason")
                if reason and str(reason) not in ("—", "-"):
                    return str(reason)
    return None


def build_context(extra: dict[str, Any] | None = None) -> dict[str, Any]:
    """Snapshot + optional role-specific published extras (never raw data)."""
    ctx = {"snapshot": build_snapshot()}
    if extra:
        ctx.update(extra)
    return ctx
