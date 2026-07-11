"""AI Timeline (AI Journal) — the day's market story, written as it happens.

Owner: glance at the timeline after 30 minutes away and understand the whole
market story — Good Morning · Trend Turning Bullish · Liquidity Improving ·
Entry Ready · Target Hit · Exit. Engine-published transitions ONLY; the AI
narrates the moment, it never decides it.

scan() is called at the end of each AI cycle (market_service). It diffs the
current published state against the last snapshot and appends timestamped
events. Pure read of state + append — never touches the decision path.
"""
from __future__ import annotations

import time
from typing import Any

from ..core.clock import now as clock_now
from ..core.state import state

_events: list[dict[str, Any]] = []
_prev: dict[str, Any] = {}
_MAX = 200


def _push(kind: str, text: str) -> None:
    _events.append({
        "ts": time.time(),
        "time": clock_now().strftime("%H:%M"),
        "kind": kind,
        "text": text,
    })
    if len(_events) > _MAX:
        del _events[: len(_events) - _MAX]


def _tag(layers: dict, *names: str) -> str | None:
    for n in names:
        row = layers.get(n)
        if isinstance(row, dict):
            for k in ("label", "state", "status", "verdict"):
                if row.get(k):
                    return str(row[k])
    return None


def _score(layers: dict, *names: str) -> float | None:
    for n in names:
        row = layers.get(n)
        if isinstance(row, dict):
            for k in ("score", "value", "pct", "strength"):
                if isinstance(row.get(k), (int, float)):
                    return float(row[k])
    return None


def scan() -> None:
    """Detect and record engine-state transitions. Safe to call every cycle."""
    try:
        intel = state.intelligence or {}
        layers = intel.get("layers") or {}
        dec = state.decision or {}
        gate = intel.get("execution_gate") or {}
        exit_i = state.exit_intel or {}

        trend = _tag(layers, "Trend", "MTF Trend")
        structure = _tag(layers, "Structure", "Market Structure")
        liq = _score(layers, "Liquidity", "Order Flow")
        band = dec.get("action") or dec.get("primary_action") or gate.get("band")
        gate_ready = bool(gate.get("gate_passed"))
        targets = (exit_i.get("targets_hit") if isinstance(exit_i.get("targets_hit"), int)
                   else len([t for t in (exit_i.get("targets") or []) if isinstance(t, dict) and t.get("hit")]))

        first = not _prev
        if trend and trend != _prev.get("trend") and not first:
            _push("trend", f"Trend turning {trend}")
        if structure and structure != _prev.get("structure") and not first \
                and any(w in structure.lower() for w in ("confirm", "break", "bos")):
            _push("structure", f"Structure {structure}")
        if liq is not None and _prev.get("liq") is not None and liq - _prev["liq"] >= 8:
            _push("liquidity", "Liquidity improving")
        if gate_ready and not _prev.get("gate_ready") and not first:
            st = dec.get("strike") or {}
            _push("entry", f"Entry ready — {st.get('strike','')} {st.get('type','')}".strip())
        if not gate_ready and _prev.get("gate_ready"):
            _push("wait", "Setup no longer ready — back to waiting")
        if band and band != _prev.get("band") and not first:
            _push("decision", f"Decision: {band}")
        if isinstance(targets, int) and isinstance(_prev.get("targets"), int) and targets > _prev["targets"]:
            _push("target", f"Target {targets} hit")

        _prev.update(trend=trend, structure=structure, liq=liq, band=band,
                     gate_ready=gate_ready, targets=targets)
    except Exception:
        pass  # a timeline hiccup must never affect the AI cycle


def mark_session(kind: str, text: str) -> None:
    """Explicit session markers (market open/close, EOD) from callers."""
    _push(kind, text)


def timeline(limit: int = 60) -> dict[str, Any]:
    return {"events": list(reversed(_events[-limit:])), "count": len(_events)}
