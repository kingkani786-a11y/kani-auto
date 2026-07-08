"""V40.1 / V40.2 — Decision Verdict Engine.

USER'S LOCKED RULE: every decision must eventually receive a verdict.

    taken   →  WINNER / LOSER                    (audit tracker, already live)
    blocked →  CAPITAL_SAVED / MISSED_WINNER / NEUTRAL   (this module)

For every blocked cycle that had a concrete preparing plan (entry/SL/T1), ONE
shadow trade per setup is opened at the plan's own levels. First touch decides:
T1 first → MISSED_WINNER (the block cost points), SL first → CAPITAL_SAVED
(the block saved capital), 90-min timeout → NEUTRAL. Each verdict is attributed
to every blocking module, so the Gate Efficiency table can answer the quant
question: which rule earns its keep? No thresholds are changed here — this is
the EVIDENCE that justifies (or refuses) future weight proposals.
"""
from __future__ import annotations

import logging
import time
from collections import deque
from typing import Any

from .missed_winner import _blocker_key

log = logging.getLogger(__name__)

WINDOW_SEC = 90 * 60
MIN_SAMPLES = 30          # below this, per-module ratios are labelled LEARNING

_open: dict[str, dict[str, Any]] = {}
_settled: deque = deque(maxlen=600)
module_stats: dict[str, dict[str, int]] = {}
regime_stats: dict[str, dict[str, int]] = {}     # V40.5 — "module|REGIME" buckets


def observe(decision: dict[str, Any], signal: dict[str, Any], spot: float,
            regime: str = "") -> None:
    """Once per AI cycle: settle open shadows on the tick, open new ones."""
    if not spot:
        return
    _tick(float(spot))
    if decision.get("is_trade"):
        return                              # taken side belongs to the audit tracker
    eg = decision.get("execution_gate") or {}
    blockers = eg.get("blocking_reasons") or []
    lv = (signal or {}).get("preparing_levels") or {}
    if not blockers or not lv.get("entry") or not lv.get("stop_loss") or not lv.get("target1"):
        return
    direction = lv.get("direction")
    if direction not in ("BULL", "BEAR"):
        return
    key = f"{direction}:{round(float(lv['stop_loss']), 1)}:{round(float(lv['target1']), 1)}"
    keys = {_blocker_key(b) for b in blockers}
    if key in _open:
        _open[key]["blockers"] |= keys      # setup persisting — union the blockers
        return
    _open[key] = {
        "ts": time.time(), "direction": direction,
        "entry": float(lv["entry"]), "sl": float(lv["stop_loss"]),
        "t1": float(lv["target1"]), "blockers": keys,
        "headline": _blocker_key(blockers[0]),
        "regime": regime or "UNKNOWN",       # V40.5 — regime at block time
    }


def _tick(spot: float) -> None:
    now = time.time()
    for k in list(_open):
        s = _open[k]
        up = s["direction"] == "BULL"
        hit_t = spot >= s["t1"] if up else spot <= s["t1"]
        hit_s = spot <= s["sl"] if up else spot >= s["sl"]
        verdict = ("MISSED_WINNER" if hit_t else "CAPITAL_SAVED" if hit_s
                   else "NEUTRAL" if now - s["ts"] > WINDOW_SEC else None)
        if not verdict:
            continue
        s["verdict"] = verdict
        s["settled_ts"] = now
        s["points"] = (round(abs(s["t1"] - s["entry"]), 1) if verdict == "MISSED_WINNER"
                       else round(abs(s["entry"] - s["sl"]), 1) if verdict == "CAPITAL_SAVED" else 0.0)
        # V40.4 — verdicts carry their OWN confidence: level-touch verdicts are
        # strong (stronger the deeper the touch); timeout verdicts are weak and
        # say so. Verdicts are never trusted blindly either.
        if verdict == "NEUTRAL":
            s["confidence"] = 54.0
            s["verdict_reason"] = "Neither SL nor T1 touched — time-based expiry"
        else:
            lvl = s["t1"] if verdict == "MISSED_WINNER" else s["sl"]
            rng = abs(s["t1"] - s["entry"]) or 1.0
            depth = abs(spot - lvl)
            s["confidence"] = round(min(97.0, 88.0 + min(depth / rng, 0.45) * 20), 0)
            s["verdict_reason"] = ("T1 touched before SL" if verdict == "MISSED_WINNER"
                                   else "SL touched before T1")
        _settled.append(dict(s))
        for b in s["blockers"]:
            m = module_stats.setdefault(b, {"blocked": 0, "saved": 0, "missed": 0, "neutral": 0})
            m["blocked"] += 1
            m["saved" if verdict == "CAPITAL_SAVED" else
              "missed" if verdict == "MISSED_WINNER" else "neutral"] += 1
            # V40.5 — the same ledger, split by regime (Trend vs Range etc.):
            # the ONLY basis on which a threshold may later become regime-aware
            rg = regime_stats.setdefault(f"{b}|{s.get('regime', 'UNKNOWN')}",
                                         {"blocked": 0, "saved": 0, "missed": 0, "neutral": 0})
            rg["blocked"] += 1
            rg["saved" if verdict == "CAPITAL_SAVED" else
               "missed" if verdict == "MISSED_WINNER" else "neutral"] += 1
        _persist(s)
        del _open[k]


def _persist(s: dict[str, Any]) -> None:
    """Best-effort durable log — OFF the event loop (supabase-py is sync HTTP;
    inline it froze the tick for a network RTT per settle — RC1.3 audit fix)."""
    import asyncio
    try:
        loop = asyncio.get_running_loop()
        loop.run_in_executor(None, _persist_sync, dict(s))
    except RuntimeError:
        _persist_sync(s)


def _persist_sync(s: dict[str, Any]) -> None:
    try:
        from . import journal
        _sb = getattr(journal, "_sb", None)
        if _sb:
            _sb.table("missed_winners").insert({
                "ts": s["settled_ts"], "bias": s["direction"],
                "reason": f"VERDICT:{s['verdict']}:" + ",".join(sorted(s["blockers"])),
                "points": s["points"], "start": s["entry"],
                "closed": s["t1"] if s["verdict"] == "MISSED_WINNER" else s["sl"],
            }).execute()
    except Exception as e:
        log.debug("verdict persist skipped: %s", e)


def report() -> dict[str, Any]:
    total = {"settled": len(_settled), "open_shadows": len(_open)}
    rows = []
    for mod, m in sorted(module_stats.items(), key=lambda kv: kv[1]["blocked"], reverse=True):
        decided = m["saved"] + m["missed"]
        rows.append({
            "module": mod, **m,
            "saved_pct": round(m["saved"] / decided * 100, 0) if decided else None,
            "missed_pct": round(m["missed"] / decided * 100, 0) if decided else None,
            "status": "LEARNING" if m["blocked"] < MIN_SAMPLES else "MEASURED",
        })
    by_regime = []
    for key, m in sorted(regime_stats.items(), key=lambda kv: kv[1]["blocked"], reverse=True):
        mod, _, reg = key.partition("|")
        decided = m["saved"] + m["missed"]
        by_regime.append({"module": mod, "regime": reg, **m,
                          "saved_pct": round(m["saved"] / decided * 100, 0) if decided else None,
                          "status": "LEARNING" if m["blocked"] < MIN_SAMPLES else "MEASURED"})
    return {
        "ready": True, **total,
        "gate_efficiency": rows,
        "by_regime": by_regime,
        "recent": [{"verdict": s["verdict"], "direction": s["direction"],
                    "points": s["points"], "confidence": s.get("confidence"),
                    "reason": s.get("verdict_reason"), "regime": s.get("regime"),
                    "blockers": sorted(s["blockers"])}
                   for s in list(_settled)[-10:]],
        "principle": "Evidence before Optimization: Observation → Evidence → Proposal → "
                     "Approval → Deployment → Monitoring. No rule changes outside this pipeline.",
        "note": f"Blocked-side verdicts (shadow trades at the plan's own SL/T1; 90-min window; "
                f"settled on ~30s cycle ticks — deep gaps can shave verdict confidence). "
                f"Taken-side WINNER/LOSER lives in the audit tracker. Ratios are opinion-free "
                f"evidence — meaningful from ~{MIN_SAMPLES} samples per bucket; thresholds "
                "change only via the human approval queue.",
    }
