"""Weekend AI — the cortex works when the market sleeps.

Owner (#013): "Weekend-ல AI தூங்கக்கூடாது — Weekend-ல தான் AI வேலை செய்யணும."
On Saturday/Sunday (and any market-closed stretch) this rotates through
Review → Research → Plan, each a single cost-capped Gemini call, and stores the
prose so the AI Workspace / Voice can show "Researching…" instead of "Paused".

Doctrine kept intact:
  • Uses the Cortex (cortex.ask) — same Structured-Context, Safety, Cost caps.
  • Never on the decision path; never emits trade instructions.
  • Grounded in existing measured ledgers — never fabricates numbers.
  • Cheap flash model + the Cost Controller's ₹/day cap bound the spend.
"""
from __future__ import annotations

import time
from typing import Any

from ..core.clock import now as clock_now
from ..core.state import market_status, state

# Rotating weekend jobs: (key, role, human status, question)
_JOBS = [
    ("review", "reviewer",
     "Reviewing last week…",
     "Review last week's trading performance from the numbers below. What "
     "worked, what didn't, and the single clearest lesson. Ground every claim "
     "in the measured figures — if something says 'building', say so. <200 words."),
    ("research", "research",
     "Researching market concepts…",
     "Pick ONE concept from {SMC, liquidity sweeps, gamma exposure, order "
     "flow, auction theory} and write a short research note: what it is, how it "
     "would show up in this engine's data, and one test idea. Research only — "
     "no trade calls. <200 words."),
    ("plan", "planner",
     "Building next week's plan…",
     "Write a short preparation plan for next week from the context: regime, "
     "what to watch, risk notes, and which engine signals to trust. Planning "
     "and preparation only, never a trade instruction. <180 words."),
]

_state: dict[str, Any] = {
    "status": "IDLE",
    "activity": "Sleeping until the weekend or a market-closed window.",
    "last_run_ts": 0.0,
    "job_index": 0,
    "outputs": {},        # key -> {text, ts, model, cost_inr, flagged}
    "runs_today": 0,
    "last_error": None,
}

# Minimum gap between auto-cycles (seconds). Weekend has ~48h; at 1h that is
# ≤24 cheap calls/day, comfortably under the Cost Controller ₹ cap.
_MIN_GAP = 3600.0


def _should_run() -> bool:
    ms = market_status(state.market_type)
    return bool(ms.get("weekend") or not ms.get("is_open"))


def _context(job_key: str) -> dict[str, Any]:
    from . import validation, verdicts
    from .cortex import context_builder
    ctx: dict[str, Any] = {"snapshot": context_builder.build_snapshot()}
    try:
        ctx["report_card"] = validation.report_card() or {}
    except Exception:
        ctx["report_card"] = {}
    try:
        vs = verdicts.report() or {}
        ctx["gate_verdicts"] = {k: v for k, v in vs.items() if not isinstance(v, list)}
    except Exception:
        ctx["gate_verdicts"] = {}
    if job_key in ("review", "plan"):
        try:
            from . import evolution
            ctx["weekly"] = evolution.report("weekly") or {}
        except Exception:
            ctx["weekly"] = {}
    return ctx


def run_cycle(force: bool = False) -> dict[str, Any]:
    """Run the next weekend job (one Gemini call). Safe to call anytime."""
    from .cortex.provider import cortex, cortex_status

    if not cortex_status().get("enabled"):
        _state["status"] = "OFF"
        _state["activity"] = "AI Cortex not configured — add a Gemini key."
        return status()
    if not force and not _should_run():
        _state["status"] = "IDLE"
        _state["activity"] = "Market open — weekend AI stands down (engine leads)."
        return status()
    if not force and (time.time() - _state["last_run_ts"]) < _MIN_GAP:
        return status()

    idx = _state["job_index"] % len(_JOBS)
    key, role, human, question = _JOBS[idx]
    _state["status"] = "WORKING"
    _state["activity"] = human
    res = cortex.ask(role, _context(key), question, max_tokens=900)
    _state["last_run_ts"] = time.time()
    _state["job_index"] = (idx + 1) % len(_JOBS)

    if res.get("ok"):
        _state["outputs"][key] = {
            "text": res.get("text", ""),
            "ts": time.time(),
            "model": res.get("model"),
            "cost_inr": (res.get("usage") or {}).get("cost_inr"),
            "flagged": (res.get("safety") or {}).get("flagged", False),
        }
        _state["runs_today"] += 1
        _state["last_error"] = None
        _state["status"] = "DONE"
        _state["activity"] = f"Last: {human.rstrip('…')} ✓ — next job queued."
    else:
        _state["last_error"] = res.get("error") or res.get("reason")
        # a transient upstream 503/429 (AI busy) is NOT a fault — don't flag it
        # as ERROR (which falsely degrades System Verify); it auto-retries.
        _state["status"] = ("CAPPED" if res.get("capped")
                            else "BUSY" if res.get("transient") else "ERROR")
        _state["activity"] = _state["last_error"] or "Weekend AI paused."
    return status()


def status() -> dict[str, Any]:
    ms = market_status(state.market_type)
    return {
        "weekend": bool(ms.get("weekend")),
        "market": ms.get("status"),
        "status": _state["status"],
        "activity": _state["activity"],
        "runs_today": _state["runs_today"],
        "next_job": _JOBS[_state["job_index"] % len(_JOBS)][2],
        "last_run_ago_min": (round((time.time() - _state["last_run_ts"]) / 60)
                             if _state["last_run_ts"] else None),
        "outputs": _state["outputs"],
        "last_error": _state["last_error"],
    }


def brain_activity_line() -> str | None:
    """A short 'what the AI is doing' line for the AI-Brain status (replaces
    'Paused' on weekends). None when nothing weekend-specific to show."""
    if _state["status"] in ("WORKING",):
        return _state["activity"]
    if _should_run() and _state["outputs"]:
        return _state["activity"]
    if _should_run():
        return "Weekend AI ready — Research · Review · Plan."
    return None
