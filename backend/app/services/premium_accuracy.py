"""RC1.16.2 — Premium-projection accuracy tracker (measurement only).

Owner-ordered live validation of the RC1.16.1 pricing engine: every cycle
records the active strike plan's projections; when the underlying later
trades within tolerance of a projected level, the projection is scored
against the live premium from the option chain. Read-only evidence — it
never touches trading logic.

Owner's pass criteria (docs/RELEASE_NOTES.md RC1.16.2):
  entry reproduce error < 1% · T1/SL premium error < 5% ·
  ordering SL < entry < T1 < T2 < T3 always · logged until n ≥ 20–30.
"""
from __future__ import annotations

import collections
import logging
import time
from typing import Any

log = logging.getLogger("premium_accuracy")

# active plan per "symbol:strike:type" — one live projection set at a time
_plans: dict[str, dict[str, Any]] = {}
# scored level touches (newest last), capped
_hits: collections.deque = collections.deque(maxlen=200)
# rolling entry-reproduce checks (newest last), capped
_entries: collections.deque = collections.deque(maxlen=200)
_ordering_violations: int = 0
_observed: int = 0

_LEVELS = ("stop_loss", "target1", "target2", "target3")
_PREM_KEY = {"stop_loss": "premium_stop_loss", "target1": "premium_target1",
             "target2": "premium_target2", "target3": "premium_target3"}


def observe(symbol: str, strike: dict[str, Any] | None, spot: float) -> None:
    """Record the current plan's projections + run the per-cycle checks."""
    global _ordering_violations, _observed
    if not strike or not spot:
        return
    lv = strike.get("level_underlying") or {}
    pr = strike.get("pricing") or {}
    if not lv:
        return
    _observed += 1

    e = strike.get("premium_entry")
    sl, t1 = strike.get("premium_stop_loss"), strike.get("premium_target1")
    t2, t3 = strike.get("premium_target2"), strike.get("premium_target3")
    ordered = None not in (e, sl, t1, t2, t3) and sl < e < t1 < t2 < t3
    if not ordered:
        _ordering_violations += 1
        log.warning("premium ordering VIOLATION %s %s%s: SL %s entry %s T1 %s T2 %s T3 %s",
                    symbol, strike.get("strike"), strike.get("type"), sl, e, t1, t2, t3)

    if pr.get("entry_reproduce_err_pct") is not None:
        _entries.append({"ts": time.time(), "err_pct": pr["entry_reproduce_err_pct"],
                         "fit_mode": pr.get("fit_mode"),
                         "iv_solved": pr.get("iv_solved"), "iv_chain": pr.get("iv_chain")})

    key = f"{symbol}:{strike.get('strike')}:{strike.get('type')}"
    prev = _plans.get(key)
    # keep the existing snapshot while the plan is unchanged so a level can
    # only be scored once per projection set
    if prev and prev["entry"] == e and prev["levels"] == lv:
        return
    _plans[key] = {
        "symbol": symbol, "strike": strike.get("strike"), "type": strike.get("type"),
        "entry": e, "entry_spot": spot, "levels": dict(lv),
        "projected": {n: strike.get(_PREM_KEY[n]) for n in _LEVELS},
        "scored": set(), "ts": time.time(),
    }
    if len(_plans) > 50:          # symbol switches — drop the oldest
        _plans.pop(next(iter(_plans)))


def check(symbol: str, spot: float, chain: list[dict] | None) -> None:
    """Score stored projections whose underlying level the spot has reached."""
    if not spot or not chain:
        return
    tol = max(2.0, spot * 0.0003)
    for plan in list(_plans.values()):
        if plan["symbol"] != symbol:
            continue
        side = "ce" if plan["type"] == "CE" else "pe"
        row = next((r for r in chain if float(r.get("strike", 0)) == float(plan["strike"])), None)
        if not row:
            continue
        actual = float(row.get(f"{side}_ltp") or 0)
        if actual <= 0:
            continue
        for name in _LEVELS:
            if name in plan["scored"]:
                continue
            lvl, proj = plan["levels"].get(name), plan["projected"].get(name)
            if lvl is None or proj is None or abs(spot - lvl) > tol:
                continue
            plan["scored"].add(name)
            err = abs(actual - proj)
            _hits.append({
                "ts": time.time(), "symbol": symbol,
                "strike": plan["strike"], "type": plan["type"], "level": name,
                "projected": proj, "actual": round(actual, 2),
                "abs_err": round(err, 2),
                "rel_err_pct": round(err / actual * 100, 2),
                "spot": round(spot, 2), "level_px": lvl,
                "mins_since_plan": round((time.time() - plan["ts"]) / 60, 1),
            })
            log.info("premium projection scored %s %s%s %s: projected ₹%s actual ₹%.2f (%.1f%%)",
                     symbol, plan["strike"], plan["type"], name, proj, actual,
                     err / actual * 100)


def report() -> dict[str, Any]:
    hits = list(_hits)
    entries = list(_entries)
    tgt = [h for h in hits if h["level"] != "stop_loss"]
    sls = [h for h in hits if h["level"] == "stop_loss"]

    def _avg(rows, k):
        return round(sum(r[k] for r in rows) / len(rows), 2) if rows else None

    n = len(hits)
    return {
        "ready": True,
        "status": "MEASURED" if n >= 20 else "LEARNING",
        "note": ("Owner criteria: entry reproduce < 1% · T1/SL premium error < 5% · "
                 "ordering always SL < entry < T1 < T2 < T3. LEARNING until ≥20 "
                 "scored touches — synthetic tests are not production evidence."),
        "plans_observed": _observed,
        "ordering_violations": _ordering_violations,
        "entry_check": {
            "n": len(entries),
            "avg_reproduce_err_pct": _avg(entries, "err_pct"),
            "max_reproduce_err_pct": max((e["err_pct"] for e in entries), default=None),
            "fallback_cycles": sum(1 for e in entries if e.get("fit_mode") != "BS"),
        },
        "level_touches": {
            "n": n,
            "targets": {"n": len(tgt), "avg_err_pct": _avg(tgt, "rel_err_pct"),
                        "worst_err_pct": max((h["rel_err_pct"] for h in tgt), default=None)},
            "stop_loss": {"n": len(sls), "avg_err_pct": _avg(sls, "rel_err_pct"),
                          "worst_err_pct": max((h["rel_err_pct"] for h in sls), default=None)},
        },
        "recent": hits[-20:],
    }
