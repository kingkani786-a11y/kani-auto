"""Capital Protection Engine (V13).

Option-buyer-specific risk: theta bleed, IV-crush exposure, premium decay,
and reversal risk — blended into a 0-100 capital risk score with categories
and position rules. Consumes Greeks + IV state + structure the platform
already computes; degrades to neutral when option data is absent.
"""
from __future__ import annotations

from typing import Any


def assess(layers: dict[str, Any], market_type: str, spot: float) -> dict[str, Any]:
    greeks = (layers.get("greeks") or {})
    g = greeks  # _greeks_layer output: {atm_iv, score_bull,...}; ATM greeks live in oi layer
    expiry = layers.get("expiry") or {}
    vix = layers.get("vix_correlation") or {}
    regime = (layers.get("regime") or {}).get("regime", "")
    of = layers.get("order_flow") or {}

    notes: list[str] = []

    # ---- Theta risk: worse near expiry; options bleed fastest in last days ----
    dte = expiry.get("days_to_expiry")
    if dte is None:
        theta_risk = 35.0
    elif dte <= 0:
        theta_risk = 90.0; notes.append("Expiry day — theta decay is brutal for buyers")
    elif dte == 1:
        theta_risk = 75.0; notes.append("1 day to expiry — heavy time decay")
    elif dte <= 3:
        theta_risk = 55.0
    else:
        theta_risk = max(20.0, 50 - dte * 2)

    # ---- IV-crush risk: high IV + near expiry = crush after the event ----
    iv = float(g.get("atm_iv") or vix.get("vix") or 0)
    if iv >= 22 and (dte is not None and dte <= 2):
        iv_crush = 80.0; notes.append("Elevated IV into expiry — IV-crush risk on any cooldown")
    elif iv >= 20:
        iv_crush = 55.0
    elif iv <= 0:
        iv_crush = 40.0
    else:
        iv_crush = max(15.0, (iv - 10) / 12 * 60)

    # ---- Premium decay risk: chop + theta = premium melts with no move ----
    chop = regime in ("RANGE_BOUND", "LOW_MOMENTUM", "EXPIRY_PINNING")
    premium_decay = min(100.0, theta_risk * (0.8 if chop else 0.5)
                        + (20 if chop else 0))
    if chop:
        notes.append("Range/chop regime — premium decays while price goes nowhere")

    # ---- Reversal risk: exhaustion/sweeps/false-breakout footprints ----
    sm = layers.get("smart_money") or {}
    reversal = 30.0
    if "EXHAUSTION_TOP" in sm.get("events", []) or "EXHAUSTION_BOTTOM" in sm.get("events", []):
        reversal += 30; notes.append("Move exhaustion detected — reversal risk up")
    if any("LIQUIDITY_SWEEP" in e for e in sm.get("events", [])):
        reversal += 20; notes.append("Liquidity sweep — stop-hunt reversal risk")
    if of.get("delta_imbalance") is not None and abs(of["delta_imbalance"]) < 0.05:
        reversal += 10  # no conviction either way
    reversal = min(100.0, reversal)

    # ---- blended capital risk ----
    # V24: theta/IV risks apply whenever OPTIONS are the vehicle (chain
    # present) — including MCX option chains; futures/stocks keep the
    # reversal+volatility blend
    _has_chain = (layers.get("_instrument_mode") or {}).get("has_chain", market_type == "INDEX")
    if not _has_chain:
        capital_risk = 0.5 * reversal + 0.5 * float(vix.get("volatility_risk") or 40)
    else:
        capital_risk = (0.30 * theta_risk + 0.25 * iv_crush
                        + 0.20 * premium_decay + 0.25 * reversal)
    capital_risk = round(max(0.0, min(100.0, capital_risk)), 0)

    category = ("CRITICAL" if capital_risk >= 76 else "ELEVATED" if capital_risk >= 61
                else "ACCEPTABLE" if capital_risk >= 41 else "SAFE")
    if category == "CRITICAL":
        action = "EXIT_AND_BLOCK"
        notes.insert(0, "Capital risk CRITICAL — exit positions, block new trades")
    elif capital_risk > 60:
        action = "REDUCE_SIZE"
        notes.insert(0, "Capital risk elevated — reduce position size")
    else:
        action = "NORMAL"

    return {
        "capital_risk": capital_risk,
        "category": category,
        "action": action,
        "theta_risk": round(theta_risk, 0),
        "iv_crush_risk": round(iv_crush, 0),
        "premium_decay_risk": round(premium_decay, 0),
        "reversal_risk": round(reversal, 0),
        "notes": notes[:4],
    }
