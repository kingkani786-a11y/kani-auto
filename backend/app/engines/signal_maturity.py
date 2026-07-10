"""Phase 7 (Signal Maturity) + Phase 6 (Entry Trigger).

Derivation-only: measures whether the CURRENT setup is mature/stable enough to
act on, and what the entry window looks like — using only outputs the platform
already computes (decision matrix, decision-intelligence, trend, capital
protection). No new indicators, no new data, no duplicated calculation.

A BUY-class trigger (READY / FIRE NOW) is withheld until maturity ≥ threshold,
which is raised on monthly expiry and tightened for scalping timeframes.
"""
from __future__ import annotations

import statistics
import time
from typing import Any

# per-symbol tracker: setup identity + history so we can measure age/persistence
_tracker: dict[str, dict[str, Any]] = {}

# maturity threshold + entry-window length (seconds) per timeframe class
_TF = {
    "scalp": {"threshold": 70, "window": 120},     # 1m/3m — fast, short window, rapid decay
    "normal": {"threshold": 61, "window": 600},    # 5m/15m — standard
}


def _stage(m: float) -> str:
    return ("Ready" if m >= 81 else "Armed" if m >= 61 else "Preparing" if m >= 41
            else "Developing" if m >= 21 else "Immature")


def evaluate(symbol: str, layers: dict[str, Any], signal: dict[str, Any],
             decision: dict[str, Any], tf: str = "normal",
             monthly_expiry: bool = False) -> dict[str, Any]:
    L = layers or {}
    rows = ((L.get("intelligence") or {}).get("decision_matrix") or {}).get("rows", [])
    # V15 instrument-aware: N/A layers (no option chain) can never confirm —
    # exclude them from maturity/confirmation counts instead of holding forever
    rows = [r for r in rows if r.get("verdict") != "N/A"]
    di = decision.get("intelligence_synthesis") or {}
    direction = signal.get("direction") or "NEUTRAL"
    sig_name = signal.get("signal") or "WAIT"
    now = time.time()
    tfc = _TF["scalp"] if tf == "scalp" else _TF["normal"]

    # ---- setup identity + age/persistence tracking ----
    key = f"{symbol}:{direction}:{sig_name}"
    t = _tracker.get(symbol)
    if not t or t.get("key") != key:
        t = {"key": key, "first_seen": now, "samples": [], "window_open": None}
        _tracker[symbol] = t
    age = now - t["first_seen"]
    persistence_cycles = len(t["samples"])

    # ---- component scores (all 0-100, from existing outputs) ----
    passed = [r for r in rows if r.get("verdict") == "PASS"]
    total = len(rows) or 1
    conf_ratio = len(passed) / total * 100
    conf_quality = (sum(r.get("score", 50) for r in passed) / len(passed)) if passed else 40.0
    strength = float((di.get("trade_quality") or {}).get("score", 0) / 10) or \
        float(signal.get("dynamic_confidence") or signal.get("confidence") or 40)
    adx = float((L.get("trend") or {}).get("adx") or 0)
    momentum = max(0.0, min(100.0, (adx - 12) * 4))

    # stability: low variance of recent strength = stable
    t["samples"].append(round(strength, 1))
    del t["samples"][:-8]
    stability = 100.0
    if len(t["samples"]) >= 3:
        sd = statistics.pstdev(t["samples"])
        stability = max(0.0, 100.0 - sd * 6)
    persistence = min(100.0, persistence_cycles * 14)

    # ---- maturity score (weighted) ----
    maturity = (conf_ratio * 0.28 + conf_quality * 0.20 + strength * 0.20
                + stability * 0.14 + persistence * 0.10 + momentum * 0.08)
    maturity = round(max(0.0, min(100.0, maturity)), 0)

    # ---- decay state (trend of recent strength) ----
    decay = "Fresh"
    if len(t["samples"]) >= 4:
        recent, older = t["samples"][-2:], t["samples"][-4:-2]
        ra, oa = sum(recent) / 2, sum(older) / 2
        if maturity < 25 or age > 3 * tfc["window"]:
            decay = "Expired"
        elif ra > oa + 3:
            decay = "Strengthening"
        elif ra < oa - 3:
            decay = "Weakening"
        else:
            decay = "Stable"
    false_signal_prob = round(max(5.0, min(95.0, 100 - (conf_ratio * 0.6 + stability * 0.4))), 0)

    # ---- monthly-expiry tightening ----
    threshold = tfc["threshold"] + (12 if monthly_expiry else 0)

    # ---- Phase 6 entry trigger ----
    is_dir = direction in ("BULL", "BEAR") and sig_name not in ("WAIT", "NO TRADE")
    window_len = tfc["window"]
    if maturity >= threshold and is_dir and decay not in ("Weakening", "Expired"):
        if t["window_open"] is None:
            t["window_open"] = now
    elif maturity < threshold - 10 or decay in ("Weakening", "Expired"):
        t["window_open"] = None
    window_remaining = (window_len - (now - t["window_open"])) if t["window_open"] else None

    if not is_dir:
        status = "NOT READY"
    elif window_remaining is not None and window_remaining <= 0:
        status = "ENTRY CLOSED"
    elif maturity >= threshold and decay not in ("Weakening", "Expired"):
        status = ("FIRE NOW" if (window_remaining or 0) > window_len * 0.6 else "READY")
    elif maturity >= threshold - 20:
        status = "ARMED"
    elif maturity >= 21:
        status = "PREPARING"
    else:
        status = "NOT READY"

    late_entry_risk = ("LOW" if window_remaining and window_remaining > window_len * 0.6
                       else "HIGH" if window_remaining is not None and window_remaining < window_len * 0.3
                       else "MEDIUM")
    missing = [r["layer"] for r in rows if r.get("verdict") != "PASS"]
    eta = max(0, int(threshold - maturity)) * 3 if maturity < threshold else 0  # rough secs to maturity

    # decay-adjusted view (display only — does NOT mutate source engines)
    decay_mult = {"Fresh": 1.0, "Strengthening": 1.0, "Stable": 0.95,
                  "Weakening": 0.8, "Expired": 0.5}.get(decay, 1.0)
    src_conv = int((di.get("conviction") or signal.get("dynamic_confidence") or 0))

    # final action label per spec (PREPARING/ARMED/READY/FIRE NOW/WAIT/SKIP)
    final = ("SKIP" if status == "ENTRY CLOSED" else status if is_dir and status != "NOT READY"
             else "WAIT")

    return {
        "ready": True,
        "maturity_score": maturity,
        # RC1.16.10 display-truth fix #3: an Expired setup can never reach
        # READY regardless of maturity (see buy_allowed) — showing the plain
        # maturity band ("Preparing"/"Armed") implied maturity was the only
        # missing thing. Display honesty only; gating logic unchanged.
        "stage": (f"STALE — setup outlived its window (was {_stage(maturity)})"
                  if decay == "Expired" else _stage(maturity)),
        "threshold": threshold,
        "buy_allowed": maturity >= threshold and is_dir and decay not in ("Weakening", "Expired"),
        "signal_age_sec": int(age),
        "persistence_cycles": persistence_cycles,
        "stability": round(stability, 0),
        "strength": round(strength, 0),
        "momentum_stability": round(momentum, 0),
        "confirmation_count": len(passed),
        "confirmation_total": total,
        "confirmation_quality": round(conf_quality, 0),
        "decay": decay,
        "false_signal_probability": false_signal_prob,
        "entry_trigger": {
            "status": status,
            "final_action": final,
            "missing_confirmations": missing,
            "remaining_confirmations": len(missing),
            "entry_window_sec": window_len,
            "window_remaining_sec": (int(window_remaining) if window_remaining is not None else None),
            "late_entry_risk": late_entry_risk,
            "trigger_eta_sec": eta,
            "trigger_confidence": int(maturity),
            "entry_score": int(round(maturity * decay_mult)),
        },
        "decay_adjusted": {"conviction": int(round(src_conv * decay_mult)),
                           "decay_multiplier": decay_mult},
        "monthly_expiry_mode": monthly_expiry,
        "note": "Maturity gates BUY; entry window prevents late chasing. Probabilities, not certainty.",
    }
