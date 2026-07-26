"""Phase 30 — Options Professor.

Plain-language explanations of the trade the platform already chose: why CE/PE,
why this strike, why this premium, why this stop/target, and why wait/reject.
Derivation-only — it narrates existing state in simple trader words, no jargon,
no new data, no certainty.
"""
from __future__ import annotations

from typing import Any


def explain(layers: dict[str, Any], signal: dict[str, Any],
            decision: dict[str, Any], strike: dict[str, Any]) -> dict[str, Any]:
    direction = signal.get("direction") or "NEUTRAL"
    is_trade = bool(decision.get("is_trade"))
    structure = layers.get("structure") or {}
    cap = layers.get("capital_protection") or {}
    intel = layers.get("intelligence") or {}
    exp = intel.get("expansion") or {}
    out: dict[str, str] = {}

    side = "CE (call)" if direction == "BULL" else "PE (put)" if direction == "BEAR" else "—"

    # Owner Step 9 (Explainability Final, 2026-07-27) Golden Rule fix: these
    # used to read as imperative advice ("Buy a CE because...", "so don't
    # buy either") — this engine is reachable through brain.py/Voice, which
    # must never give a second opinion, only restate what the platform
    # already computed. Same real reasoning, descriptive instead of
    # imperative phrasing.
    if direction == "BULL":
        out["why_ce"] = ("CE (call) is favored: trend, structure and flow lean bullish, "
                         "so a call gains as price rises.")
        out["why_pe"] = "PE (put) is not favored — a put would lose money in an up-move, which is the current bias."
    elif direction == "BEAR":
        out["why_pe"] = ("PE (put) is favored: trend and flow lean bearish, "
                         "so a put gains as price falls.")
        out["why_ce"] = "CE (call) is not favored — a call would lose money in a down-move, which is the current bias."
    else:
        out["why_ce"] = out["why_pe"] = "No clear direction yet — neither side has an edge."

    if strike.get("strike"):
        out["why_strike"] = (f"Strike {strike.get('strike')} {strike.get('type','')} is picked for the best "
                             f"balance of liquidity and a delta that moves well with the underlying "
                             f"(score {strike.get('score','—')}). Closer/farther strikes either cost too much "
                             "or move too little.")
        out["why_premium"] = (f"Around ₹{strike.get('premium_entry','—')} — rich enough to react to the move "
                              f"but not so far out-of-the-money that it just bleeds time value. "
                              f"Expansion potential: {exp.get('class','—')}.")
    else:
        out["why_strike"] = out["why_premium"] = "No strike chosen yet — wait for a valid setup."

    if is_trade:
        out["why_stop"] = (f"Stop at {decision.get('stop_loss','—')} sits just beyond a level that, if broken, "
                           "means the idea is wrong — it caps the loss before theta and a reversal compound it.")
        out["why_target"] = (f"Targets {decision.get('target1','—')}/{decision.get('target2','—')}/"
                             f"{decision.get('target3','—')} are set where price has room to run before the next "
                             f"barrier ({structure.get('resistance') if direction=='BULL' else structure.get('support')}).")
    else:
        out["why_stop"] = out["why_target"] = "No live trade — levels appear once a setup triggers."

    out["why_wait"] = (f"{decision.get('reason','Confluence isn’t aligned yet')}. "
                       "Waiting for confirmation beats forcing a low-quality entry.")
    vetoes = signal.get("vetoes") or signal.get("warnings") or []
    risk = cap.get("category")
    out["why_reject"] = (("Rejected because: " + "; ".join(vetoes[:3])) if vetoes
                         else f"Would be rejected if risk turns high ({risk or '—'}) or a key level breaks against the trade.")

    return {
        "ready": True,
        "side": side,
        "direction": direction,
        "explanations": out,
        "note": "Plain-language narration of the existing decision — education, not advice; never a certainty.",
    }
