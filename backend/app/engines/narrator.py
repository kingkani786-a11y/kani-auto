"""AI Market Narrator — hybrid Tamil + trading-English commentary.

Display-layer only: this authors the narrative sentences directly in Tamil
(no translation API, no extra work — same number of strings). Trading terms,
levels, percentages and signal names stay in ENGLISH inside Tamil sentences,
e.g. "Price தற்போது VWAP-க்கு கீழே trade ஆகிறது." Execution/analytics labels
and numbers elsewhere remain fully English.
"""
from __future__ import annotations

from typing import Any


def _veto_reason_ta(veto: str) -> str:
    v = veto.lower()
    if "volatility" in v:
        return "volatility அதிகமாக உள்ளது"
    if "probability" in v:
        return "probability குறைவாக உள்ளது"
    if "no trade zone" in v or "zone" in v:
        return "no-trade zone active-ஆக உள்ளது"
    if "trap" in v:
        return "trap risk காணப்படுகிறது"
    if "capital risk" in v:
        return "capital risk அதிகமாக உள்ளது"
    if "threshold" in v or "confidence" in v or "score" in v:
        return "confluence போதுமான அளவில் இல்லை"
    if "data quality" in v:
        return "data quality சரியில்லை"
    return "தெளிவான confirmation இல்லை"


def narrate(
    symbol: str, spot: float, layers: dict[str, Any], signal: dict[str, Any],
    strike: dict[str, Any] | None, warning: dict[str, Any] | None,
) -> list[str]:
    lines: list[str] = []
    sym = symbol or "சந்தை"

    regime = layers.get("regime", {})
    if regime.get("regime"):
        rg = regime["regime"].replace("_", " ").lower()
        lines.append(f"{sym} தற்போது {rg} regime-ல் உள்ளது.")

    # trend + VWAP location
    trend = layers.get("trend", {})
    td = trend.get("direction")
    if td == "BULL":
        lines.append("Trend தற்போது bullish-ஆக உள்ளது.")
    elif td == "BEAR":
        lines.append("Trend தற்போது bearish-ஆக உள்ளது.")
    elif td == "NEUTRAL":
        lines.append("தெளிவான trend இல்லை.")
    vwap = trend.get("vwap")
    if vwap and spot:
        side = "மேலே" if spot >= vwap else "கீழே"
        lines.append(f"Price தற்போது VWAP-க்கு {side} trade ஆகிறது.")

    # option-chain / smart money
    oi = layers.get("oi", {})
    acts = (layers.get("smart_money", {}) or {}).get("activities", [])
    if "PUT_WRITING" in acts:
        lines.append("Support-ல் put writing காணப்படுகிறது.")
    if "CALL_WRITING" in acts:
        lines.append("Resistance-ல் call writing காணப்படுகிறது — upside cap ஆகிறது.")
    if oi.get("pcr"):
        lines.append(f"PCR தற்போது {oi['pcr']}-ஆக உள்ளது.")

    # structure event
    ev = layers.get("structure", {}).get("event")
    if ev == "BREAKOUT":
        lines.append("Breakout உறுதியாகிக்கொண்டிருக்கிறது.")
    elif ev == "BREAKDOWN":
        lines.append("Breakdown நடந்துகொண்டிருக்கிறது.")

    # futures confirmation (V13.1)
    fut = layers.get("futures", {})
    if fut.get("buildup") and fut.get("buildup") != "Neutral":
        line = f"Futures பகுதியில் {fut['buildup'].lower()} காணப்படுகிறது."
        if fut.get("relation") == "CONFIRMS":
            line += " இது தற்போதைய bias-ஐ support செய்கிறது."
        elif fut.get("relation") == "CONTRADICTS":
            line += " இது தற்போதைய bias-க்கு எதிராக உள்ளது."
        lines.append(line)

    # MTF alignment
    mtf = layers.get("mtf", {})
    if mtf.get("alignment"):
        lines.append(f"Multi-timeframe alignment {mtf['alignment']:.0f}%-ஆக உள்ளது.")

    # expected range
    prob = layers.get("probability", {})
    if prob.get("expected_range"):
        lo, hi = prob["expected_range"]
        lines.append(f"Expected range: {lo:,.0f} – {hi:,.0f}.")

    # the call
    sig = signal.get("signal", "NO TRADE")
    if sig == "NO TRADE":
        vetoes = signal.get("vetoes") or []
        reason = _veto_reason_ta(vetoes[0]) if vetoes else "confluence போதவில்லை"
        lines.append(f"தற்போது trade இல்லை — {reason}.")
        if warning and warning.get("setup") not in (None, "NONE"):
            side = "bullish" if warning["setup"] == "BULLISH_FORMING" else "bearish"
            lines.append(
                f"ஒரு {side} setup உருவாகிக்கொண்டிருக்கிறது (preparation {warning['preparation']}%, "
                f"confidence {warning['confidence']}%) — confirmation வரும் வரை wait செய்யவும்."
            )
        else:
            lines.append("புதிய setup உருவாகும் வரை wait செய்வது சிறந்தது.")
    else:
        strike_txt = f" — {strike['strike']:.0f} {strike['type']} ~{strike['premium_entry']}" if strike else ""
        lines.append(
            f"பரிந்துரை: {sig}{strike_txt}, confidence {signal.get('confidence', 0)}% "
            f"({signal.get('confirmations_count', 0)}/12 layers confirm)."
        )

    return lines
