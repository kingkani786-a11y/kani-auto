"""Phase 22 — Weight Approval Engine (human-in-the-loop).

Closes the self-tuning loop SAFELY. The nightly audit (Phase 23) recommends
engine-weight changes; nothing reaches the live confluence gate until a human
walks each one through:

    QUEUE → APPROVE → SIMULATE (paper validation) → APPLY (production)

Golden Rule: MEASURE → VALIDATE → SIMULATE → APPROVE → DEPLOY. Weights are
NEVER auto-applied. Default state = every multiplier 1.0 = identical to the
current equal-weighted gate, so the system behaves exactly as before until a
human deliberately changes it. Applied weights persist (Supabase) + rehydrate.
"""
from __future__ import annotations

import logging
import time
from typing import Any

from . import memory
from .journal import _sb

log = logging.getLogger("weights")

# Only these engines have BOTH measured reliability AND a live confluence weight.
# (reliability layer name, lowercased) -> confluence WEIGHTS key
NAME_MAP = {"trend": "trend", "structure": "structure", "oi": "oi", "greeks": "greeks",
            "mtf": "mtf", "smart money": "smart_money", "volume profile": "volume_profile"}
MIN_SAMPLES_FOR_QUEUE = 20      # statistical-evidence gate before a change may queue
MULT_BOUNDS = (0.0, 1.5)

# weight_key -> {status, engine, current, suggested, multiplier, reason,
#                confidence, samples, simulation, history[], updated}
_state: dict[str, dict[str, Any]] = {}


def effective_multipliers() -> dict[str, float]:
    """Multipliers the LIVE gate should apply (only APPLIED entries; else 1.0).
    Consumed by confluence.run — defaults to all-1.0 (no behaviour change)."""
    return {wk: v["multiplier"] for wk, v in _state.items()
            if v.get("status") == "APPLIED" and v.get("multiplier") is not None}


def _suggested_multiplier(reliability: float, samples: int) -> tuple[float, str]:
    if samples < MIN_SAMPLES_FOR_QUEUE:
        return 1.0, "Insufficient evidence — maintain"
    if reliability > 75:
        return round(min(1.5, 1.0 + (reliability - 75) / 50), 2), "Reliability > 75% — increase"
    if reliability >= 60:
        return 1.0, "Reliability 60–75% — maintain"
    if reliability >= 40:
        return round(max(0.5, reliability / 60), 2), "Reliability 40–60% — reduce"
    return 0.0, "Reliability < 40% — disable candidate"


def build_queue() -> dict[str, Any]:
    """Phase 22 — populate the approval queue from current engine reliability.
    Only engines that map to a live weight AND meet the evidence gate, and only
    when the suggested multiplier differs from what's already applied/queued."""
    rel = memory.engine_reliability()
    queued = 0
    for name, v in rel.items():
        wk = NAME_MAP.get(name.lower())
        if not wk:
            continue
        n, r = v["n"], v["reliability"]
        if n < MIN_SAMPLES_FOR_QUEUE:
            continue
        mult, reason = _suggested_multiplier(r, n)
        applied = _state.get(wk, {})
        # skip if this exact change is already applied or already pending the same value
        if applied.get("status") == "APPLIED" and abs(applied.get("multiplier", 1.0) - mult) < 1e-9:
            continue
        if mult == 1.0 and applied.get("status") in (None, "APPLIED") and \
                abs(applied.get("multiplier", 1.0) - 1.0) < 1e-9:
            continue
        conf = "HIGH" if n >= 50 else "MEDIUM"
        _state[wk] = {"status": "PENDING", "engine": name, "weight_key": wk,
                      "current": applied.get("multiplier", 1.0), "suggested": mult,
                      "multiplier": None, "reason": reason, "confidence": conf,
                      "samples": n, "reliability": r, "simulation": None,
                      "history": applied.get("history", []), "updated": time.time()}
        queued += 1
    return {"queued": queued, "queue": queue()}


def _advance(wk: str, frm: tuple, to: str) -> dict[str, Any]:
    e = _state.get(wk)
    if not e:
        return {"error": f"No queued change for '{wk}'"}
    if e["status"] not in frm:
        return {"error": f"'{wk}' is {e['status']}; cannot move to {to}"}
    e["history"].append({"from": e["status"], "to": to, "ts": time.time()})
    e["status"] = to
    e["updated"] = time.time()
    return e


def approve(wk: str) -> dict[str, Any]:
    return _advance(wk, ("PENDING",), "APPROVED")


def reject(wk: str) -> dict[str, Any]:
    e = _advance(wk, ("PENDING", "APPROVED", "SIMULATED"), "REJECTED")
    return e


def simulate(wk: str) -> dict[str, Any]:
    """Paper-validation estimate from stored outcomes: how trades did when this
    engine was PASS vs the baseline. Honest estimate, not a guarantee."""
    e = _state.get(wk)
    if not e or e["status"] != "APPROVED":
        return {"error": f"'{wk}' must be APPROVED before simulation"}
    name = e["engine"]
    outs = list(memory._outcomes)
    if not outs:
        return {"error": "No outcomes to simulate against"}
    base = round(sum(o["win"] for o in outs) / len(outs) * 100, 1)
    passed = [o for o in outs if name in (o.get("engines_pass") or [])]
    pass_wr = round(sum(o["win"] for o in passed) / len(passed) * 100, 1) if passed else None
    # estimated impact: weighting toward a high-pass-winrate engine should help
    est = None
    if pass_wr is not None:
        est = round((pass_wr - base) * (e["suggested"] - 1.0), 2)
    e["simulation"] = {"baseline_win_rate": base, "engine_pass_win_rate": pass_wr,
                       "pass_samples": len(passed), "estimated_impact": est,
                       "note": "Paper estimate from stored outcomes — validate before apply."}
    return _advance(wk, ("APPROVED",), "SIMULATED")


def apply(wk: str) -> dict[str, Any]:
    """Production apply — only after APPROVE + SIMULATE. Writes the multiplier
    the live confluence gate will use, bounded for safety."""
    e = _state.get(wk)
    if not e or e["status"] != "SIMULATED":
        return {"error": f"'{wk}' must be SIMULATED before apply"}
    lo, hi = MULT_BOUNDS
    e["multiplier"] = max(lo, min(hi, e["suggested"]))
    res = _advance(wk, ("SIMULATED",), "APPLIED")
    _persist(wk, e)
    log.info("weight APPLIED: %s -> %.2f×", wk, e["multiplier"])
    return res


def revert(wk: str) -> dict[str, Any]:
    """Reset an applied weight back to 1.0 (neutral)."""
    e = _state.get(wk)
    if not e:
        return {"error": f"No entry for '{wk}'"}
    e["multiplier"] = 1.0
    e["status"] = "APPLIED"
    e["history"].append({"from": "APPLIED", "to": "REVERTED", "ts": time.time()})
    _persist(wk, e)
    return e


def queue() -> list[dict]:
    return [v for v in _state.values() if v["status"] in ("PENDING", "APPROVED", "SIMULATED")]


def status() -> dict[str, Any]:
    return {
        "queue": queue(),
        "applied": [v for v in _state.values() if v["status"] == "APPLIED"],
        "effective_multipliers": effective_multipliers(),
        "min_samples_for_queue": MIN_SAMPLES_FOR_QUEUE,
        "workflow": ["QUEUE", "APPROVE", "SIMULATE", "APPLY"],
        "note": "Weights never auto-apply — human approval + paper simulation required.",
    }


# ---- persistence (Phase 19) ----
def _persist(wk: str, e: dict) -> None:
    if not _sb:
        return
    try:
        _sb.table("engine_weights").upsert({
            "weight_key": wk, "engine": e["engine"], "multiplier": e["multiplier"],
            "status": e["status"], "updated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        }, on_conflict="weight_key").execute()
    except Exception as ex:
        log.debug("weight persist failed: %s", ex)


def rehydrate() -> int:
    """Restore APPLIED weights on startup so approved tuning survives restart."""
    if not _sb:
        return 0
    try:
        res = _sb.table("engine_weights").select("*").eq("status", "APPLIED").execute()
        for r in (res.data or []):
            wk = r.get("weight_key")
            if wk in NAME_MAP.values():
                _state[wk] = {"status": "APPLIED", "engine": r.get("engine", wk),
                              "weight_key": wk, "multiplier": float(r.get("multiplier", 1.0)),
                              "current": 1.0, "suggested": float(r.get("multiplier", 1.0)),
                              "reason": "restored", "confidence": "—", "samples": 0,
                              "reliability": None, "simulation": None, "history": [],
                              "updated": time.time()}
        return len(_state)
    except Exception as ex:
        log.warning("weight rehydrate failed: %s", ex)
        return 0
