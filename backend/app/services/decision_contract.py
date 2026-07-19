"""Decision Contract — V2.1's unifier: entry/hold/exit in ONE object.

Every decision (BUY or WAIT) ships as a contract assembled purely from state
the engines already published (Rule 10: one source, many consumers — this
derives, never re-decides). A BUY carries its why, confidence, invalidations
and exit plan; a WAIT carries its why (Rule 5/11: explain before execute).
Read-only; the system still never places orders.
"""
from __future__ import annotations

import time
from typing import Any

from ..core.state import state


def _layers() -> dict[str, float]:
    rows = ((state.intelligence or {}).get("layers", {}).get("intelligence", {})
            .get("rows", []))
    out: dict[str, float] = {}
    for r in rows:
        try:
            if r.get("layer") is not None and r.get("score") is not None:
                out[str(r["layer"])] = float(r["score"])
        except (TypeError, ValueError):
            continue
    return out


def _invalidations(dec: dict, tech: dict) -> list[str]:
    """Pre-stated exit conditions from data we actually have — never invented."""
    inv: list[str] = []
    sl = dec.get("stop_loss")
    if sl:
        inv.append(f"Price crosses stop {round(float(sl), 1)}")
    vwap = tech.get("vwap")
    if vwap:
        side = "below" if (dec.get("action") or "").endswith("CALL") else "above"
        inv.append(f"Sustained break {side} VWAP {round(float(vwap), 1)}")
    ks = state.kill_switch or {}
    inv.append("Kill Switch / Safe Mode trips (capital protection)")
    if ks.get("active"):
        inv[-1] += " — ACTIVE NOW"
    return inv


def contract() -> dict[str, Any]:
    dec = state.decision or {}
    sig = state.signal or {}
    tech = (sig.get("tech") or {})
    layers = _layers()

    action = dec.get("action") or "WAIT"
    is_trade = bool(dec.get("is_trade"))
    conviction = dec.get("conviction")

    # WHY (Rule 11 — explain before execute), for BUY and WAIT alike
    reason = dec.get("reason")
    why: list[str] = []
    if isinstance(reason, list):
        why = [str(r) for r in reason][:6]
    elif reason:
        why = [str(reason)]
    if not why:
        # fall back to the strongest confirming layers — honest, from scores
        top = sorted(((k, v) for k, v in layers.items() if v and v >= 65),
                     key=lambda kv: kv[1], reverse=True)[:4]
        why = [f"{k} {int(v)}" for k, v in top] or ["No published reason — engine idle"]

    # ── Unified Entry Grade (C2, charter L7): ONE grade instead of five
    # scattered scores. Declared blend of already-published numbers — conviction
    # (decision), signal confidence, and layer breadth. Not win-calibrated.
    sig_conf = None
    try:
        sig_conf = float((sig.get("signal") or {}).get("confidence"))
    except (TypeError, ValueError):
        pass
    breadth = (sum(1 for v in layers.values() if v >= 55) / len(layers) * 100) if layers else None
    parts = [p for p in (conviction, sig_conf, breadth) if isinstance(p, (int, float))]
    entry_score = round(sum(parts) / len(parts)) if parts else None
    grade = (None if entry_score is None else
             "A+" if entry_score >= 90 else "A" if entry_score >= 80 else
             "B" if entry_score >= 70 else "C" if entry_score >= 60 else "D")
    entry_grade = {
        "grade": grade, "score": entry_score,
        "parts": {"conviction": conviction, "signal_confidence": sig_conf,
                  "layer_breadth": round(breadth) if breadth is not None else None},
    }

    # ── Evidence Ledger (C3, Rule 3): confidence decomposed into five named
    # pillars, /20 each — confidence is EVIDENCE, not a number. Pillars map to
    # published layer scores; a pillar with no data shows None, never 0.
    def _p20(*names: str) -> int | None:
        vals = [layers[n] for n in names if n in layers]
        return round(sum(vals) / len(vals) / 100 * 20) if vals else None
    ledger = [
        {"pillar": "Trend", "score": _p20("Trend")},
        {"pillar": "Price Action", "score": _p20("Structure", "MTF")},
        {"pillar": "Institutional", "score": _p20("Institutional", "Smart Money", "OI")},
        {"pillar": "Momentum/Flow", "score": _p20("Futures", "Liquidity", "Volume Profile")},
        {"pillar": "Risk", "score": _p20("Risk")},
    ]
    known = [e["score"] for e in ledger if e["score"] is not None]
    ledger_total = round(sum(known) / (len(known) * 20) * 100) if known else None

    # ── Signal Aging (C4, Rule 9): stale signals decay — never hold an old BUY.
    # Declared ramp: full strength ≤120s, then −2% per 30s. State labels:
    # Fresh<2m · Good<5m · Old<10m · Weak<15m · STALE≥15m.
    now = time.time()
    sig_ts = sig.get("ts")
    age_s = int(now - sig_ts) if sig_ts else None
    decay_pct = 0.0
    aged_conf = conviction
    aging_state = None
    if age_s is not None:
        decay_pct = max(0.0, (age_s - 120) / 30.0 * 2.0)
        if isinstance(conviction, (int, float)):
            aged_conf = round(max(0.0, conviction * (1 - decay_pct / 100)), 1)
        aging_state = ("Fresh" if age_s < 120 else "Good" if age_s < 300 else
                       "Old" if age_s < 600 else "Weak" if age_s < 900 else "STALE")
    aging = {"age_s": age_s, "state": aging_state,
             "decay_pct": round(decay_pct, 1), "aged_confidence": aged_conf}

    # ── Entry Window countdown (C5, Rule 8): seconds until the aged confidence
    # crosses the 60% floor under the SAME declared ramp — derived, not invented.
    # conf*(1-decay/100)=60 ⇒ decay*=(1-60/conf)*100 ⇒ age*=120+decay*/2*30.
    window_s = None
    if isinstance(conviction, (int, float)) and conviction > 0 and age_s is not None:
        if conviction <= 60:
            window_s = 0
        else:
            decay_star = (1 - 60.0 / conviction) * 100.0
            age_star = 120 + decay_star / 2.0 * 30.0
            window_s = max(0, int(age_star - age_s))
    entry_window_live = {
        "seconds_left": window_s,
        "state": (None if window_s is None else
                  "CLOSED" if window_s == 0 else
                  "CLOSING" if window_s <= 30 else "OPEN"),
    }

    exit_plan = {
        "stop_loss": dec.get("stop_loss"),
        "target1": dec.get("target1") or (dec.get("next_add_levels") or [None])[0],
        "trail": "After T1 — trail to cost, then EMA/structure" if is_trade else None,
    }

    return {
        "action": action,
        "is_trade": is_trade,
        "confidence": conviction,
        "why": why,
        "entry_grade": entry_grade,
        "ledger": ledger, "ledger_total": ledger_total,
        "aging": aging, "entry_window_live": entry_window_live,
        "risk": (state.risk or {}).get("capital_risk") or dec.get("grade"),
        "expected_move": dec.get("opportunity") or dec.get("market_state_label"),
        "reward_risk": dec.get("reward_risk"),
        "entry": dec.get("entry"),
        "entry_window": dec.get("entry_window"),
        "exit_plan": exit_plan,
        "invalidations": _invalidations(dec, tech),
        "instruction": ("If ANY invalidation occurs → EXIT immediately."
                        if is_trade else
                        "Standing aside — re-evaluated every engine cycle."),
        "signal_ts": sig.get("ts"),
        "as_of": int(time.time()),
        "note": ("One contract = entry, hold and exit in one logic. Derived "
                 "from the published engine state; informational only — the "
                 "user executes manually, the system never places orders."),
    }
