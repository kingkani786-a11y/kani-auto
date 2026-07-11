"""System Verify — one honest health view for the dashboard.

Owner: "Trust by Verification, not by Claims." Each subsystem reports a real
status derived from live state — never a hardcoded ✅. The score is computed
from the core subsystems that are actually up, so it can't be faked.

Statuses: ok · off · paused · degraded · client (verified in the browser, not
here) · building (measured, insufficient data).
"""
from __future__ import annotations

from typing import Any

from ..core.state import market_status, state


def _cortex() -> dict[str, Any]:
    try:
        from .cortex import cortex_status
        return cortex_status()
    except Exception:
        return {"enabled": False}


def verify() -> dict[str, Any]:
    cs = _cortex()
    ms = market_status(state.market_type)
    open_ = ms.get("is_open")

    subs: list[dict[str, Any]] = []

    def add(name, status, detail="", core=False):
        subs.append({"name": name, "status": status, "detail": detail, "core": core})

    # Backend — if this code runs, it's up.
    add("Backend", "ok", "API responding", core=True)

    # Decision Engine — up when the AI cycle has published a decision (or paused
    # when market closed, which is correct, not a fault).
    has_decision = bool(state.decision)
    add("Decision Engine",
        "ok" if has_decision else ("paused" if not open_ else "building"),
        "engine published" if has_decision else ("market closed" if not open_ else "warming up"),
        core=True)

    # Memory — ledgers present in-process.
    mem_ok = False
    try:
        from . import verdicts
        r = verdicts.report() or {}
        mem_ok = bool(r.get("settled") or r.get("total"))
    except Exception:
        pass
    add("Memory", "ok" if mem_ok else "building",
        "ledgers loaded" if mem_ok else "no settled samples yet", core=True)

    # Broker — real connection flag.
    add("Broker", "ok" if state.connected else "off",
        "connected" if state.connected else "disconnected (token daily-expires)", core=False)

    # Data feed — reflects real data quality / market state.
    if not state.connected:
        add("Data Feed", "off", "broker disconnected")
    elif not open_:
        add("Data Feed", "paused", "market closed — resumes at open")
    else:
        dq = state.data_quality or "UNKNOWN"
        add("Data Feed", "ok" if dq == "GOOD" else "degraded", f"quality {dq}")

    # Gemini / AI Cortex — real key + budget.
    b = cs.get("budget") or {}
    if cs.get("enabled"):
        left = b.get("budget_left_inr")
        add("AI Cortex (Gemini)", "ok" if (left is None or left > 0) else "off",
            f"{cs.get('model')} · ₹{b.get('cost_inr_today',0)}/{b.get('cost_cap_inr',0)}", core=True)
    else:
        add("AI Cortex (Gemini)", "off", "no key configured", core=True)

    # AI Timeline — module present.
    try:
        from . import ai_timeline
        tl = ai_timeline.timeline(1)
        add("AI Timeline", "ok", f"{tl.get('count',0)} events today")
    except Exception:
        add("AI Timeline", "off", "module error")

    # Research / Weekend AI.
    try:
        from . import weekend_ai
        w = weekend_ai.status()
        add("Research (Weekend AI)", "ok" if cs.get("enabled") else "off",
            f"{w.get('runs_today',0)} runs today · {w.get('status')}")
    except Exception:
        add("Research (Weekend AI)", "off", "module error")

    # Voice — TTS runs in the browser; the server cannot verify it.
    add("Voice / Radio", "client", "verified in the browser (SpeechSynthesis)")

    # Health score — fraction of CORE subsystems that are ok, as a %.
    core_subs = [s for s in subs if s["core"]]
    ok_core = sum(1 for s in core_subs if s["status"] == "ok")
    score = round(100 * ok_core / max(1, len(core_subs)))
    label = ("Stable" if score >= 90 else "Degraded" if score >= 60 else "Attention")

    return {
        "health_score": score,
        "health_label": label,
        "market_open": open_,
        "subsystems": subs,
        "note": "Statuses are derived from live state — paused/off on a closed "
                "market or disconnected broker is expected, not a fault.",
    }
