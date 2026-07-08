"""Exit Intelligence + Trade Management (additive, derivation-only).

For an ACTIVE trade, derives exit confidence, a reversal-probability curve,
institutional profit-booking zones, S/R strength, re-entry zones, and
probability-weighted target projection — entirely from layers/lifecycle the
platform already computed. No new market data, no new signal logic.

Hard rule: NEVER predicts exact tops/bottoms or guarantees a target/reversal.
Everything is expressed as a probability or confidence.
"""
from __future__ import annotations

from typing import Any


def _reversal_base(layers: dict[str, Any], direction: str) -> float:
    sm = layers.get("smart_money", {})
    of = layers.get("order_flow", {})
    events = sm.get("events", [])
    base = 18.0
    if "EXHAUSTION_TOP" in events or "EXHAUSTION_BOTTOM" in events:
        base += 22
    if any("LIQUIDITY_SWEEP" in e for e in events):
        base += 12
    # order flow turning against the position
    ofs = float(of.get("score") or 50)
    if direction == "BULL" and ofs < 45:
        base += 12
    elif direction == "BEAR" and ofs > 55:
        base += 12
    cap = layers.get("capital_protection", {})
    base += max(0.0, (float(cap.get("reversal_risk") or 0) - 40) * 0.3)
    return max(5.0, min(75.0, base))


def _booking_zone(layers: dict[str, Any], spot: float, direction: str) -> dict[str, Any]:
    """Likely institutional profit-booking zone ahead of the position."""
    struct = layers.get("structure", {})
    gw = layers.get("expiry", {}).get("gamma_wall")
    if direction == "BULL":
        cand = [x for x in (struct.get("resistance"), gw, *(struct.get("liquidity_above") or [])) if x and x > spot]
        level = min(cand) if cand else None
    else:
        cand = [x for x in (struct.get("support"), gw, *(struct.get("liquidity_below") or [])) if x and x < spot]
        level = max(cand) if cand else None
    if not level:
        return {"zone": None, "strength": 0, "reason": "No clear booking zone ahead"}
    buf = max(abs(level) * 0.0006, 5)
    reasons = []
    if gw and abs(level - gw) < buf * 1.5:
        reasons.append("Gamma wall")
    if level in (struct.get("liquidity_above") or []) + (struct.get("liquidity_below") or []):
        reasons.append("Liquidity cluster")
    if level in (struct.get("resistance"), struct.get("support")):
        reasons.append("Prior " + ("supply" if direction == "BULL" else "demand"))
    pcr = layers.get("oi", {}).get("pcr")
    strength = min(95, 50 + len(reasons) * 14 + (10 if pcr and ((pcr < 0.9) == (direction == "BULL")) else 0))
    return {"zone": [round(level - buf, 1), round(level + buf, 1)], "strength": round(strength, 0),
            "reason": " + ".join(reasons) or "Structural level"}


def analyze(layers: dict[str, Any], lifecycle: dict[str, Any], signal: dict[str, Any],
            spot: float) -> dict[str, Any]:
    state = lifecycle.get("state", "")
    active = state in ("ENTRY", "TARGET")
    direction = lifecycle.get("direction") or signal.get("direction") or "NONE"
    entry = lifecycle.get("entry") or signal.get("entry")
    stop = lifecycle.get("stop") or signal.get("stop_loss")
    targets = lifecycle.get("targets") or [signal.get("target1"), signal.get("target2"), signal.get("target3")]
    hit = int(lifecycle.get("targets_hit") or 0)

    base_rev = _reversal_base(layers, direction)
    reversal_curve = {
        "current": round(base_rev, 0),
        "near_t1": round(min(95, base_rev + 18), 0),
        "near_t2": round(min(95, base_rev + 40), 0),
        "near_t3": round(min(96, base_rev + 58), 0),
    }
    booking = _booking_zone(layers, spot, direction) if active else {"zone": None, "strength": 0, "reason": "—"}
    mom = abs(float((signal.get("tech") or {}).get("momentum") or 0))
    adx = float(layers.get("trend", {}).get("adx") or 0)
    momentum_strength = round(max(0, min(100, 40 + mom * 50 + max(adx - 18, 0) * 1.2)), 0)

    # partial profit-booking plan (rule-based display, tied to targets hit)
    PLAN = {
        0: {"action": "Hold full position", "sl": "At original stop"},
        1: {"action": "Book 30% · move SL to cost", "sl": "Cost (breakeven)"},
        2: {"action": "Book 30% · move SL to T1", "sl": "Target 1"},
        3: {"action": "Book remaining position", "sl": "Trail / exit"},
    }
    partial = PLAN.get(min(hit, 3))

    # exit score: rises with reversal risk near the current target band, fading
    # momentum, and proximity to a booking zone
    near_rev = [base_rev, reversal_curve["near_t1"], reversal_curve["near_t2"], reversal_curve["near_t3"]][min(hit + (1 if active else 0), 3)]
    exit_score = 0.5 * near_rev + 0.3 * (100 - momentum_strength)
    if booking.get("zone") and spot:
        lo, hi = booking["zone"]
        if lo <= spot <= hi:
            exit_score += 15
    exit_score = round(max(0, min(100, exit_score)), 0)

    # V28 — banded exit ladder: Hold < Trail < Partial (book ~70%) < Full
    exit_band = ("FULL EXIT" if exit_score >= 95 else "PARTIAL EXIT" if exit_score >= 85
                 else "TRAIL" if exit_score >= 65 else "HOLD")
    if not active:
        action, reason = "NO ACTIVE TRADE", "Flat — waiting for a signal"
    elif hit >= 3 or near_rev >= 80 or exit_score >= 95:
        action, reason = "FINAL EXIT", "All targets / very high reversal risk"
    elif exit_score >= 85:
        action, reason = "PARTIAL EXIT", "Exit score high — book ~70%, hold the runner"
    elif exit_score >= 70:
        action = "EARLY EXIT" if hit == 0 else "TRAIL"
        reason = f"{booking['reason']} + rising reversal risk" if booking.get("zone") else "Rising reversal risk"
    elif hit >= 1:
        action, reason = "TRAIL", "In profit — trail the remainder"
    else:
        action, reason = "HOLD", "Thesis intact, momentum holding"

    # support / resistance strength
    struct = layers.get("structure", {})
    sr = {
        "support": struct.get("support"), "resistance": struct.get("resistance"),
        "support_strength": round(min(95, 50 + len(struct.get("liquidity_below") or []) * 12), 0),
        "resistance_strength": round(min(95, 50 + len(struct.get("liquidity_above") or []) * 12), 0),
    }
    sr["break_probability"] = round(min(90, momentum_strength * 0.7), 0)
    sr["reject_probability"] = round(100 - sr["break_probability"], 0)

    # V28 re-entry — SAFETY RULE FIRST: never suggest re-entry into a weakening
    # or flipped trend; otherwise score the pullback quality (trend strength +
    # order-flow recovery + right side of VWAP) before calling it READY.
    vwap = layers.get("trend", {}).get("vwap")
    reentry = None
    if active and hit >= 1:
        trend_dir = layers.get("trend", {}).get("direction")
        trend_ok = adx >= 18 and trend_dir in (direction, "NEUTRAL", None)
        if not trend_ok:
            reentry = {"status": "NO RE-ENTRY",
                       "reason": "Trend weakening — wait for a new setup"}
        elif vwap:
            ofs = float(layers.get("order_flow", {}).get("score") or 50)
            flow_ok = ofs >= 50 if direction == "BULL" else ofs <= 50
            vwap_ok = (spot >= vwap) if direction == "BULL" else (spot <= vwap)
            re_score = round(min(95, 30 + max(adx - 18, 0) * 2.5
                                 + (15 if flow_ok else 0) + (15 if vwap_ok else 0)), 0)
            reentry = {
                "status": "READY" if re_score >= 75 else "WAIT FOR PULLBACK",
                "reentry_score": re_score,
                "pullback_zone": [round(min(vwap, entry), 1), round(max(vwap, entry), 1)] if entry else None,
                "confidence": round(max(20, min(85, 40 + (adx - 18) * 2)), 0),
                "risk": "Low" if adx > 25 else "Medium" if adx > 18 else "High",
            }

    # probability-weighted target projection
    pos = float(layers.get("probability", {}).get("prob_success") or 50)
    projection = [
        {"zone": targets[0], "probability": round(min(92, pos), 0)},
        {"zone": targets[1], "probability": round(max(15, pos * 0.65), 0)},
        {"zone": targets[2], "probability": round(max(8, pos * 0.4), 0)},
    ] if all(targets) else []

    risk_remaining = round(abs((spot - stop)) , 1) if (active and stop and spot) else None
    profit_locked = "Yes (≥ cost)" if hit >= 1 else "No"

    # V29 — Trade Cycle Prediction: what the AI expects NEXT, with probability
    # and an INDICATIVE time band (momentum-based, same declared-band approach
    # as the opportunity ladder). Explicitly a forecast, never a schedule.
    cycle_forecast = None
    if active:
        t_band = ("2–5 min" if momentum_strength >= 70
                  else "5–10 min" if momentum_strength >= 45 else "10–20 min")
        why = [reason]
        if booking.get("zone"):
            why.append(booking["reason"])
        if reentry and reentry.get("status") == "READY":
            nxt, prob = "RE-ENTRY", reentry.get("reentry_score", 75)
        elif reentry and reentry.get("status") == "NO RE-ENTRY":
            nxt, prob = "FINAL EXIT", round(min(92, 55 + exit_score * 0.4))
        elif reentry:   # WAIT FOR PULLBACK
            nxt, prob = "RE-ENTRY (after pullback)", reentry.get("reentry_score", 50)
        elif action == "FINAL EXIT":
            nxt, prob = "FINAL EXIT", 90
        elif hit >= 1:
            nxt, prob = "PULLBACK", round(min(90, 40 + near_rev * 0.5))
        else:
            nxt, prob = "PARTIAL EXIT", round(max(20, min(92, exit_score + 10)))
        # 3-state re-entry outlook (never a promise)
        if reentry is None:
            outlook = None
        elif reentry.get("status") == "NO RE-ENTRY":
            outlook = {"state": "RED", "label": "No Re-entry Expected (Trend Weakening)"}
        elif (reentry.get("reentry_score") or 0) >= 75:
            outlook = {"state": "GREEN", "label": f"Re-entry Likely ({reentry['reentry_score']:.0f}%)"}
        else:
            outlook = {"state": "YELLOW", "label": f"Re-entry Uncertain ({reentry.get('reentry_score', 50):.0f}%)"}
        # V30 — 3-step chained outlook (each step CONDITIONAL on the previous;
        # all probabilities from the same real sources, prospective re-entry
        # uses the live trend/flow/VWAP state)
        ofs_now = float(layers.get("order_flow", {}).get("score") or 50)
        _flow_ok = ofs_now >= 50 if direction == "BULL" else ofs_now <= 50
        _vwap_ok = vwap and ((spot >= vwap) if direction == "BULL" else (spot <= vwap))
        prospective_re = round(min(95, 30 + max(adx - 18, 0) * 2.5
                                   + (15 if _flow_ok else 0) + (15 if _vwap_ok else 0)), 0)
        chain = []
        if hit == 0:
            chain = [
                {"step": "PARTIAL EXIT", "probability": round(max(20, min(92, exit_score + 10)), 0)},
                {"step": "PULLBACK", "probability": round(min(90, 40 + near_rev * 0.5), 0)},
                {"step": "RE-ENTRY", "probability": prospective_re},
            ]
        elif reentry and reentry.get("status") != "NO RE-ENTRY":
            chain = [
                {"step": "PULLBACK", "probability": round(min(90, 40 + near_rev * 0.5), 0)},
                {"step": "RE-ENTRY", "probability": reentry.get("reentry_score", prospective_re)},
                {"step": "FINAL EXIT", "probability": None},
            ]
        cycle_forecast = {
            "next_action": nxt, "probability": round(float(prob), 0),
            "time_band": t_band, "reasons": why[:3],
            "reentry_outlook": outlook,
            "chain": chain,
            "note": "Probability-based forecast, not a schedule — each step conditional "
                    "on the previous; recalculated every cycle.",
        }

    return {
        "active": active,
        "locked_levels": {"entry": entry, "stop": stop,
                          "t1": targets[0] if targets else None,
                          "t2": targets[1] if len(targets) > 1 else None,
                          "t3": targets[2] if len(targets) > 2 else None} if active else None,
        "exit_score": exit_score,
        "exit_band": exit_band,
        "exit_confidence": round(min(95, 50 + abs(exit_score - 50)), 0),
        "recommended_action": action,
        "reason": reason,
        "reversal_probability": reversal_curve,
        "momentum_strength": momentum_strength,
        "profit_booking_zone": booking,
        "partial_plan": partial,
        "support_resistance": sr,
        "re_entry": reentry,
        "cycle_forecast": cycle_forecast,
        "target_projection": projection,
        "trade_management": {
            "position": f"{direction} {'open' if active else 'flat'}",
            "targets_hit": hit, "risk_remaining": risk_remaining,
            "profit_locked": profit_locked,
            "trailing_stop": (lifecycle.get("stop") if hit >= 1 else None),
            "recommended_action": action,
        },
    }
