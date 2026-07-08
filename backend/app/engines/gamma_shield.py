"""V8 Step 8 — Gamma Shield (advisory risk layer).

The trader does not want gamma-spike trades. Derives a gamma-danger state from
outputs that ALREADY exist (expiry gamma wall + DTE + squeeze events, regime
phases, capital-protection theta/IV, greeks data-sanity) and recommends WAIT
when conditions resemble a gamma spike. Advisory only — it informs the trader
and the why-not list; it does not silently mutate the tested execution gate.
Historical failure-rate is reported honestly as 'building' until live data.
"""
from __future__ import annotations

from typing import Any

_STATES = ["SAFE", "WATCH", "HIGH", "SPIKE"]


def evaluate(layers: dict[str, Any], spot: float) -> dict[str, Any]:
    L = layers or {}
    expiry = L.get("expiry") or {}
    regime = L.get("regime") or {}
    cap = L.get("capital_protection") or {}
    greeks = L.get("greeks") or {}

    dte = expiry.get("days_to_expiry")
    wall = expiry.get("gamma_wall")
    events = set(expiry.get("events") or [])
    phases = set(regime.get("phases") or [])
    theta = float(cap.get("theta_risk") or 0)
    reasons: list[str] = []

    near_wall = False
    wall_distance = None
    if wall and spot:
        try:
            wall_distance = round(abs(spot - float(wall)), 1)      # points to the wall
            near_wall = wall_distance / spot < 0.0015              # within ~0.15%
        except (TypeError, ValueError, ZeroDivisionError):
            near_wall = False

    squeeze = "GAMMA_SQUEEZE" in phases or "EXPIRY_SQUEEZE_RISK" in events
    pinning = (regime.get("regime") == "EXPIRY_PINNING")
    greeks_bad = any("implausible" in str(n).lower() for n in (greeks.get("notes") or []))

    if squeeze and (dte == 0 or near_wall):
        state = "SPIKE"
        reasons.append("Gamma squeeze conditions at/near the wall on expiry — spike behaviour likely")
    elif (dte == 0 and near_wall) or squeeze:
        state = "HIGH"
        if dte == 0 and near_wall:
            reasons.append(f"Expiry day, price hugging gamma wall {wall} — dealer hedging dominates")
        if squeeze:
            reasons.append("Squeeze phase detected")
    elif pinning or dte == 0 or greeks_bad:
        state = "WATCH"
        if pinning:
            reasons.append("Expiry pinning — price magnetised to the wall; moves can trap")
        if dte == 0 and not pinning:
            reasons.append("Expiry day — theta/gamma dynamics elevated")
        if greeks_bad:
            reasons.append("Greeks data unreliable (IV artifact) — cannot rule gamma risk out")
    else:
        state = "SAFE"

    if theta >= 75 and state in ("WATCH", "HIGH", "SPIKE"):
        reasons.append(f"Theta risk {theta:.0f} — decay punishes hesitation in gamma zones")

    return {
        "ready": True,
        "state": state,
        "recommendation": ("WAIT — gamma-spike zone; skip this trade" if state in ("HIGH", "SPIKE")
                           else "Caution near expiry gamma" if state == "WATCH" else "Clear"),
        "gamma_wall": wall,
        "wall_distance_pts": wall_distance,
        "near_wall": near_wall,
        "dte": dte,
        "reasons": reasons,
        "historical_failure_rate": None,   # honest: populates from live validation data
        "note": "Advisory shield from existing expiry/regime/greeks state — does not alter the gate. "
                "Probabilities, not certainty.",
    }
