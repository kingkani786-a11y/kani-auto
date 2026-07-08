"""Missed Winner Engine — the evidence layer for calibrating the gate.

When the system says WAIT / NO TRADE but the market THEN moves favorably in the
predicted direction, that is a "missed winner". We log it with the reason that
blocked it (Kill Switch / Calibration / Institution / Greeks / …). After enough
samples the attribution shows which blocker costs the most — the evidence needed
to (later, with approval) loosen a too-conservative threshold.

Derivation-only: reads spot + the decision's bias/blocking reasons each cycle.
Changes NO trading behaviour — it only measures what the gate gave up.
"""
from __future__ import annotations

import time
from collections import deque
from typing import Any

_TIERS = [20, 40, 80, 120]
_obs: dict[str, Any] | None = None          # current open no-trade observation
_log: deque[dict] = deque(maxlen=500)       # finalised missed winners


def track(spot: float, is_trade: bool, bias: str, blocking_reasons: list[str]) -> None:
    """Call once per AI cycle."""
    global _obs
    d = 1 if bias == "BULLISH" else -1 if bias == "BEARISH" else 0

    # a trade was taken, or no clear direction → close the current observation
    if is_trade or d == 0 or not spot:
        _obs = None
        return

    reason = (blocking_reasons[0] if blocking_reasons else "Confluence pending")
    # start a fresh observation, or reset if the bias flipped
    if not _obs or _obs["dir"] != d:
        _obs = {"start": spot, "dir": d, "reason": reason, "ts": time.time(),
                "peak": 0.0, "tiers_logged": set()}
        return

    # track favourable excursion since we skipped the entry
    exc = (spot - _obs["start"]) * _obs["dir"]
    _obs["peak"] = max(_obs["peak"], exc)
    for tier in _TIERS:
        if _obs["peak"] >= tier and tier not in _obs["tiers_logged"]:
            _obs["tiers_logged"].add(tier)
            rec = {"ts": time.time(), "bias": bias, "reason": _obs["reason"],
                   "points": tier, "start": round(_obs["start"], 1),
                   "closed": time.time()}
            _log.append(rec)
            _persist(rec)


def _persist(rec: dict) -> None:
    """P1 — persist each missed winner so validation evidence survives restart.
    RC1.3: runs OFF the event loop (supabase-py is sync HTTP)."""
    from .journal import _sb
    if not _sb:
        return
    import asyncio

    def _do(r=dict(rec)):
        try:
            _sb.table("missed_winners").insert(r).execute()
        except Exception:
            pass
    try:
        asyncio.get_running_loop().run_in_executor(None, _do)
    except RuntimeError:
        _do()


def rehydrate(limit: int = 500) -> int:
    """Restore missed-winner evidence on startup (Supabase only)."""
    from .journal import _sb
    if not _sb:
        return 0
    try:
        res = (_sb.table("missed_winners").select("*")
               .order("closed", desc=True).limit(limit).execute())
        for r in reversed(res.data or []):
            _log.append(r)
        return len(_log)
    except Exception:
        return 0


def _blocker_key(reason: str) -> str:
    """Collapse verbose reasons into a stable blocker category for ranking."""
    r = (reason or "").lower()
    if "kill switch" in r:
        return "Kill Switch"
    if "data" in r or "completeness" in r or "feed" in r:
        return "Data Quality"
    if "institution" in r:
        return "Institution"
    if "greek" in r:
        return "Greeks"
    if "calibrat" in r:
        return "Calibration"
    if "risk" in r:
        return "Risk"
    if "'oi'" in r or r.startswith("oi") or "pcr" in r:
        return "OI"
    if "smart money" in r:
        return "Smart Money"
    if "liquidity" in r or "order flow" in r:
        return "Liquidity"
    if "structure" in r:
        return "Structure"
    if "trend" in r:
        return "Trend"
    if "mtf" in r:
        return "MTF"
    if "confirm" in r or "composite" in r or "threshold" in r or "maturity" in r:
        return "Confluence Bar"
    if "safe mode" in r:
        return "Safe Mode"
    if "trap" in r or "no trade zone" in r:
        return "Trap/NTZ"
    if "quality" in r or "conviction" in r or "fire score" in r:
        return "Quality Bar"
    return (reason or "Other")[:40]


def summary() -> dict[str, Any]:
    now = time.time()
    today = [m for m in _log if m.get("closed", 0) >= now - 86400]
    week = [m for m in _log if m.get("closed", 0) >= now - 7 * 86400]
    # collapse to one record per observation (highest tier reached)
    by_reason: dict[str, int] = {}
    for m in today:
        k = _blocker_key(m["reason"])
        by_reason[k] = by_reason.get(k, 0) + 1
    tiers = sorted(m["points"] for m in today)
    median = tiers[len(tiers) // 2] if tiers else None
    worst_reason = max(by_reason, key=by_reason.get) if by_reason else None
    # Potential profit lost = max tier reached per observation (grouped by start)
    best_per_obs: dict[float, float] = {}
    for m in today:
        k = m.get("start", 0)
        best_per_obs[k] = max(best_per_obs.get(k, 0), m["points"])
    potential_lost = round(sum(best_per_obs.values()), 0)
    return {
        "ready": True,
        "missed_today": len(today),
        "missed_week": len(week),
        "avg_missed_pts": round(sum(tiers) / len(tiers), 0) if tiers else None,
        "median_missed_pts": median,
        "max_missed_pts": max(tiers) if tiers else 0,
        "potential_lost_pts": potential_lost,
        "by_reason": by_reason,
        "worst_blocker": worst_reason,
        "recommendation": (f"'{worst_reason}' blocked the most winners — review its threshold "
                           "against live results before loosening (human-approved)." if worst_reason
                           else "No missed winners logged yet."),
        "note": "Evidence layer — measures winners the gate gave up. Does not change trading. "
                "Use to justify calibration; never auto-loosens capital protection.",
    }
