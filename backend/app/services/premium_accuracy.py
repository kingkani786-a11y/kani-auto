"""RC1.16.2/.3 — Premium-projection accuracy tracker (measurement only).

Owner-ordered live validation of the RC1.16.1 pricing engine: every cycle
records the active strike plan's projections; when the underlying later
trades within tolerance of a projected level, the projection is scored
against the live premium from the option chain. Read-only evidence — it
never touches trading logic.

Owner's production gate (docs/RC_STATUS.md):
  ≥50 scored touches · samples on BOTH expiry and non-expiry days ·
  entry reproduce median ≤ 1% · T1/SL median error ≤ 5% ·
  ordering violations = 0 · fallback usage < 5% · tracker errors = 0.
"""
from __future__ import annotations

import collections
import logging
import time
from typing import Any

from ..core.clock import now as ist_now, today_str

log = logging.getLogger("premium_accuracy")

# active plan per "symbol:strike:type" — one live projection set at a time
_plans: dict[str, dict[str, Any]] = {}
# scored level touches (newest last), capped
_hits: collections.deque = collections.deque(maxlen=500)
# rolling entry-reproduce checks (newest last), capped
_entries: collections.deque = collections.deque(maxlen=500)
_ordering_violations: int = 0
_observed: int = 0
_errors: int = 0

_LEVELS = ("stop_loss", "target1", "target2", "target3")
_PREM_KEY = {"stop_loss": "premium_stop_loss", "target1": "premium_target1",
             "target2": "premium_target2", "target3": "premium_target3"}

# Declared bands (not calibrated claims): session by IST hour, IV split at 15.
_HIGH_IV = 15.0


def _session_bucket() -> str:
    h, m = ist_now().hour, ist_now().minute
    hm = h * 60 + m
    if hm < 11 * 60:
        return "morning"
    if hm < 14 * 60:
        return "mid"
    if hm <= 15 * 60 + 30:
        return "closing"
    return "evening"          # MCX evening session


def note_error() -> None:
    """Called by the wiring's exception handlers — production-gate criterion."""
    global _errors
    _errors += 1


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
        # regime context captured at plan time (owner: regime-wise breakdown)
        "expiry_day": (strike.get("expiry") or "")[:10] == today_str(),
        "session": _session_bucket(),
        "iv_band": ("HIGH_IV" if (pr.get("iv_solved") or 0) >= _HIGH_IV else "LOW_IV"),
        "fit_mode": pr.get("fit_mode"),
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
                "expiry_day": plan["expiry_day"], "session": plan["session"],
                "iv_band": plan["iv_band"], "fit_mode": plan.get("fit_mode"),
            })
            log.info("premium projection scored %s %s%s %s: projected ₹%s actual ₹%.2f (%.1f%%)",
                     symbol, plan["strike"], plan["type"], name, proj, actual,
                     err / actual * 100)


def _dist(vals: list[float]) -> dict[str, Any] | None:
    """Owner-ordered: mean alone can mislead — median + p95 + max too."""
    if not vals:
        return None
    import math
    s = sorted(vals)
    n = len(s)
    return {
        "n": n,
        "mean": round(sum(s) / n, 2),
        "median": round(s[n // 2] if n % 2 else (s[n // 2 - 1] + s[n // 2]) / 2, 2),
        "p95": round(s[max(0, math.ceil(0.95 * n) - 1)], 2),   # nearest-rank
        "max": round(s[-1], 2),
    }


def _bucket_errors(hits: list[dict], key: str) -> dict[str, Any]:
    groups: dict[str, list[float]] = {}
    for h in hits:
        groups.setdefault(str(h.get(key)), []).append(h["rel_err_pct"])
    return {k: _dist(v) for k, v in sorted(groups.items())}


def report() -> dict[str, Any]:
    hits = list(_hits)
    entries = list(_entries)
    tgt = [h for h in hits if h["level"] != "stop_loss"]
    sls = [h for h in hits if h["level"] == "stop_loss"]
    n = len(hits)

    entry_dist = _dist([e["err_pct"] for e in entries])
    tgt_dist = _dist([h["rel_err_pct"] for h in tgt])
    sl_dist = _dist([h["rel_err_pct"] for h in sls])
    fallback_n = sum(1 for e in entries if e.get("fit_mode") != "BS")
    fallback_pct = round(fallback_n / len(entries) * 100, 1) if entries else 0.0
    exp_n = sum(1 for h in hits if h["expiry_day"])

    # Owner's production gate — every criterion computed, failures named
    gate_fails: list[str] = []
    if n < 50:
        gate_fails.append(f"touches {n}/50")
    if not (exp_n and n - exp_n):
        gate_fails.append("need samples on BOTH expiry and non-expiry days")
    if entry_dist and entry_dist["median"] > 1.0:
        gate_fails.append(f"entry median {entry_dist['median']}% > 1%")
    if tgt_dist and tgt_dist["median"] > 5.0:
        gate_fails.append(f"target median {tgt_dist['median']}% > 5%")
    if sl_dist and sl_dist["median"] > 5.0:
        gate_fails.append(f"SL median {sl_dist['median']}% > 5%")
    if _ordering_violations:
        gate_fails.append(f"ordering violations {_ordering_violations}")
    if fallback_pct >= 5.0:
        gate_fails.append(f"fallback usage {fallback_pct}% ≥ 5%")
    if _errors:
        gate_fails.append(f"tracker errors {_errors}")

    return {
        "ready": True,
        "status": "MEASURED" if n >= 20 else "LEARNING",
        "note": ("Owner criteria: entry reproduce < 1% · T1/SL premium error < 5% · "
                 "ordering always SL < entry < T1 < T2 < T3. LEARNING until ≥20 "
                 "scored touches — synthetic tests are not production evidence. "
                 "Session/IV buckets are declared bands, not calibrated claims."),
        "plans_observed": _observed,
        "ordering_violations": _ordering_violations,
        "tracker_errors": _errors,
        "entry_check": {
            "distribution_pct": entry_dist,
            "fallback_cycles": fallback_n,
            "fallback_pct": fallback_pct,
        },
        "level_touches": {
            "n": n,
            "targets_err_pct": tgt_dist,
            "stop_loss_err_pct": sl_dist,
        },
        "by_regime": {
            "expiry_vs_not": _bucket_errors(hits, "expiry_day"),
            "session": _bucket_errors(hits, "session"),
            "iv_band": _bucket_errors(hits, "iv_band"),
            "fit_mode": _bucket_errors(hits, "fit_mode"),
        },
        "production_gate": {
            "criteria": "≥50 touches · expiry+non-expiry samples · entry median ≤1% · "
                        "T1/SL median ≤5% · ordering violations 0 · fallback <5% · errors 0",
            "expiry_samples": exp_n,
            "non_expiry_samples": n - exp_n,
            "status": "PASS" if not gate_fails else "NOT YET",
            "blocking": gate_fails,
        },
        "recent": hits[-20:],
    }
