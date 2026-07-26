"""Decision Synthesis Engine (V10).

The backend is complex; the trader's view must be trivially simple. This
engine collapses the full intelligence packet + lifecycle + portfolio into
the handful of fields the ultra-simple terminal shows, so a trader
understands the call in 3 seconds. It NEVER invents a trade — it only
restates what the confluence engine already decided, in plain language.
"""
from __future__ import annotations

from typing import Any


def _market_state(regime: str, phases: list[str], adx: float, atr_pct: float) -> tuple[str, str]:
    """Returns (state, emoji-label). SCALPING when fast/volatile but tradable."""
    if regime in ("VOLATILE", "EXPIRY_PINNING") or atr_pct > 1.5:
        return "AVOID", "🚫 AVOID"
    if regime in ("HIGH_MOMENTUM",) and atr_pct > 0.6:
        return "SCALPING", "⚡ SCALPING"
    if regime in ("TRENDING", "HIGH_MOMENTUM") or "MARKUP" in phases or "MARKDOWN" in phases:
        return "TRENDING", "🔥 TRENDING"
    if regime in ("RANGE_BOUND", "LOW_MOMENTUM"):
        return "RANGE", "🔄 RANGE"
    return "RANGE", "🔄 RANGE"


def _opportunity(grade: str, prob: float, opp_state: str) -> str:
    if opp_state == "AVOID" or grade in ("NO TRADE", ""):
        return "🚫 LOW OPPORTUNITY"
    if grade == "A" and prob >= 75:
        return "🔥 VERY HIGH OPPORTUNITY"
    if grade in ("A", "B"):
        return "⚡ MEDIUM OPPORTUNITY"
    return "🚫 LOW OPPORTUNITY"


def _conviction(grade: str) -> tuple[str, str]:
    if grade == "A":
        return "HIGH", "🔥 HIGH CONVICTION"
    if grade == "B":
        return "MODERATE", "⚡ MODERATE CONVICTION"
    if grade == "C":
        return "LOW", "⚠ LOW CONVICTION"
    return "NONE", "🚫 NO CONVICTION"


def _action(signal_name: str) -> str:
    return {"BUY CE": "BUY CALL", "BUY PE": "BUY PUT",
            "BUY FUTURES": "BUY", "SELL FUTURES": "SELL",
            "BUY STOCK": "BUY", "SELL STOCK": "SELL"}.get(signal_name, "WAIT"
            if signal_name == "NO TRADE" else signal_name)


def _entry_window(lifecycle: dict, spot: float, entry: float, atr: float) -> str:
    state = lifecycle.get("state")
    if state in ("ENTRY", "TRIGGERED"):
        # price already past trigger — chasing risk grows with distance
        if entry and atr and abs(spot - entry) > 1.5 * atr:
            return "⚠ LAST CHANCE ENTRY"
        return "🚀 ENTRY WINDOW OPEN"
    if state == "ARMED":
        return "🚀 ENTRY WINDOW OPEN"
    return "⏳ WAIT"


def _action_state(lifecycle: dict) -> str:
    hit = lifecycle.get("targets_hit", 0)
    state = lifecycle.get("state")
    if state == "EXIT":
        return "🛑 EXIT"
    if hit >= 1:
        return "💰 BOOK PARTIAL"
    if state in ("ENTRY", "TARGET"):
        return "📈 HOLD FOR T3"
    if state == "ARMED":
        return "➕ ADD ON TRIGGER"
    return "📈 HOLD"


def _one_line_reason(is_trade: bool, state: str, action: str,
                     sig: dict, layers: dict) -> str:
    """One short, plain-English line — the only explanation the trader needs."""
    if not is_trade:
        vetoes = sig.get("vetoes") or []
        if state == "RANGE":
            return "Range Market – Wait"
        if not vetoes:
            return "Conditions Unclear – Wait"
        v = vetoes[0].replace("SAFETY: ", "")
        if "volatility" in v:
            return "Too Volatile – Stand Aside"
        if "liquidity" in v:
            return "Thin Liquidity – Avoid"
        if "confidence" in v or "threshold" in v or "confluence" in v:
            return "Weak Setup – No Trade"
        if "probability" in v:
            return "Low Probability – Wait"
        return "Confirmation Missing – Wait"
    # trade: lead with the strongest evidence
    of = layers.get("order_flow", {})
    flow = layers.get("smart_money", {})
    bull = action in ("BUY CALL", "BUY")
    if of.get("score", 50) > 62:
        return "Strong Buyers Active" if bull else "Sellers In Control"
    if "PUT_WRITING" in flow.get("activities", []) and bull:
        return "Support Being Defended"
    if "CALL_WRITING" in flow.get("activities", []) and not bull:
        return "Upside Being Capped"
    if layers.get("structure", {}).get("event") == "BREAKOUT":
        return "Breakout Probability Rising"
    if layers.get("structure", {}).get("event") == "BREAKDOWN":
        return "Breakdown Underway"
    return "Trend Aligned – Momentum Building" if bull else "Downtrend Aligned"


def build(packet: dict[str, Any], lifecycle: dict[str, Any],
          spot: float) -> dict[str, Any]:
    sig = packet["signal"]
    layers = packet["layers"]
    regime = layers.get("regime", {}).get("regime", "")
    phases = layers.get("regime", {}).get("phases", [])
    adx = float(layers.get("trend", {}).get("adx") or 0)
    atr = float(sig.get("tech", {}).get("atr") or 0)
    atr_pct = (atr / spot * 100) if spot else 0.0
    prob = float(layers.get("probability", {}).get("prob_success") or 0)
    grade = sig.get("grade", "NO TRADE")

    state, state_label = _market_state(regime, phases, adx, atr_pct)
    conviction, conviction_label = _conviction(grade)
    action = _action(sig.get("signal", "WAIT"))
    is_trade = sig.get("signal") not in (None, "NO TRADE")

    # AVOID market locks the action to WAIT regardless of signal
    if state == "AVOID":
        action = "NO TRADE" if not is_trade else "WAIT"

    # Owner Step 7 (Risk Panel Final, 2026-07-26): removed the "recommended
    # lots"/"max safe lots" sizing that used to live here — it multiplied the
    # UNDERLYING index's point-risk by lot_size, as if that were an option
    # buyer's rupee risk, which is wrong (an option buyer's actual risk is
    # the PREMIUM difference, not the index's point move). This disagreed
    # with the correct premium-based sizing market_service.py separately
    # computes into decision["position_sizing"] (portfolio_risk.position_size
    # fed the real premium entry/stop) — RiskApproval.tsx and routes.py's
    # /portfolio/risk now both read that single correct source instead.

    reason = _one_line_reason(is_trade, state, action, sig, layers)

    # single PRIMARY ACTION — 9-state master hierarchy from lifecycle + targets
    lc = (lifecycle or {}).get("state", "")
    hit = int((lifecycle or {}).get("targets_hit") or 0)
    warn = (packet.get("warning") or {})
    if lc == "EXIT":
        primary = "FULL EXIT"
    elif lc == "TARGET":
        primary = "PARTIAL EXIT" if hit == 1 else "TRAIL"   # book first target, trail after
    elif lc == "ENTRY":
        primary = "HOLD"
    elif lc in ("ARMED", "TRIGGERED") and is_trade and state != "AVOID":
        primary = "ENTER"
    elif warn.get("setup") not in (None, "NONE") and float(warn.get("preparation") or 0) >= 70:
        primary = "PREPARE"                                  # setup nearly armed
    elif warn.get("setup") not in (None, "NONE"):
        primary = "WATCH"                                    # setup forming
    elif is_trade and state != "AVOID":
        primary = "ENTER"
    else:
        primary = "WAIT"

    return {
        "primary_action": primary,
        "market_state": state,
        "market_state_label": state_label,
        "opportunity": _opportunity(grade, prob, state),
        "conviction": conviction,
        "conviction_label": conviction_label,
        "action": action,
        "is_trade": is_trade and state != "AVOID",
        "next_add_levels": [sig.get("target1")] if is_trade else [],
        "entry": sig.get("entry"),
        "stop_loss": sig.get("stop_loss"),
        "target1": sig.get("target1"),
        "target2": sig.get("target2"),
        "target3": sig.get("target3"),
        "reward_risk": sig.get("reward_risk"),
        "entry_window": _entry_window(lifecycle, spot, sig.get("entry") or 0, atr),
        "action_state": _action_state(lifecycle),
        "reason": reason,
        "grade": grade,
    }
