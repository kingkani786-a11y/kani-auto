"""ADD-ON Intelligence Layer (advisory only).

A self-contained supplementary signal generator. It reads data the platform
already holds in memory and returns the strict advisory JSON contract. It
NEVER changes existing engines, routes, UI, or decisions — it is a pure,
optional output layer the dashboard may display or ignore.

Flow Score = OI Strength × 40% + Volume Spike × 30% + Price Momentum × 30%
"""
from __future__ import annotations

from typing import Any

EMPTY: dict[str, Any] = {
    "addon_top_buy": [],
    "addon_top_sell": [],
    "addon_indices": {"nifty": "", "banknifty": ""},
    "addon_reasons": {"buy": "", "sell": "", "index": ""},
    "confidence": 0,
}


def _norm(value: float, peak: float) -> float:
    return max(0.0, min(100.0, (value / peak * 100) if peak else 0.0))


def _momentum_score(momentum_pct: float) -> float:
    # map ROC% to 0-100 (|0.5%| ~ full)
    return max(0.0, min(100.0, 50 + momentum_pct * 100))


def compute(symbol: str, analytics: dict[str, Any], tech: dict[str, Any],
            scanner_rows: list[dict] | None) -> dict[str, Any]:
    """Return the advisory JSON. Always valid, even with sparse data."""
    out = {k: (v.copy() if isinstance(v, (dict, list)) else v) for k, v in EMPTY.items()}
    out["addon_indices"] = dict(EMPTY["addon_indices"])
    out["addon_reasons"] = dict(EMPTY["addon_reasons"])

    chain = (analytics or {}).get("chain") or []
    momentum = float((tech or {}).get("momentum") or 0.0)
    mom_score = _momentum_score(momentum)

    # ---- per-strike flow scoring ----
    max_ce_oichg = max((abs(r.get("ce_oi_chg", 0)) for r in chain), default=0)
    max_pe_oichg = max((abs(r.get("pe_oi_chg", 0)) for r in chain), default=0)
    max_ce_vol = max((r.get("ce_volume", 0) for r in chain), default=0)
    max_pe_vol = max((r.get("pe_volume", 0) for r in chain), default=0)

    buy: list[dict] = []   # CE plays (bullish flow)
    sell: list[dict] = []  # PE plays (bearish flow)
    for r in chain:
        strike = r.get("strike")
        # CE candidate (bullish): call OI building or unwinding + volume + up-momentum
        ce_oi_strength = _norm(abs(r.get("ce_oi_chg", 0)), max_ce_oichg)
        ce_vol_spike = _norm(r.get("ce_volume", 0), max_ce_vol)
        ce_flow = round(0.40 * ce_oi_strength + 0.30 * ce_vol_spike + 0.30 * mom_score, 1)
        buy.append({"symbol": symbol, "strike": strike, "type": "CE",
                    "flow_score": ce_flow, "reason": _why(ce_oi_strength, ce_vol_spike, momentum, True)})
        # PE candidate (bearish): put OI building + volume + down-momentum
        pe_oi_strength = _norm(abs(r.get("pe_oi_chg", 0)), max_pe_oichg)
        pe_vol_spike = _norm(r.get("pe_volume", 0), max_pe_vol)
        pe_flow = round(0.40 * pe_oi_strength + 0.30 * pe_vol_spike + 0.30 * (100 - mom_score), 1)
        sell.append({"symbol": symbol, "strike": strike, "type": "PE",
                     "flow_score": pe_flow, "reason": _why(pe_oi_strength, pe_vol_spike, momentum, False)})

    buy.sort(key=lambda x: x["flow_score"], reverse=True)
    sell.sort(key=lambda x: x["flow_score"], reverse=True)
    out["addon_top_buy"] = buy[:2]
    out["addon_top_sell"] = sell[:2]

    # ---- index bias (NIFTY / BANKNIFTY) ----
    pcr = float((analytics or {}).get("pcr") or 0)
    scan = {r["symbol"]: r for r in (scanner_rows or [])}
    out["addon_indices"]["nifty"] = _index_bias("NIFTY", scan, symbol, momentum, pcr)
    out["addon_indices"]["banknifty"] = _index_bias("BANKNIFTY", scan, symbol, momentum, pcr)

    # ---- reasons + confidence ----
    top_buy = out["addon_top_buy"][0]["flow_score"] if out["addon_top_buy"] else 0
    top_sell = out["addon_top_sell"][0]["flow_score"] if out["addon_top_sell"] else 0
    out["addon_reasons"]["buy"] = (
        f"Strongest call flow at {out['addon_top_buy'][0]['strike']} "
        f"(flow {top_buy})" if out["addon_top_buy"] else "Insufficient call-side flow")
    out["addon_reasons"]["sell"] = (
        f"Strongest put flow at {out['addon_top_sell'][0]['strike']} "
        f"(flow {top_sell})" if out["addon_top_sell"] else "Insufficient put-side flow")
    out["addon_reasons"]["index"] = (
        f"Momentum {momentum:+.2f}%, PCR {pcr:.2f}" if chain else "Awaiting chain data")

    # confidence: separation between the dominant side and the other, scaled
    dominant = max(top_buy, top_sell)
    spread = abs(top_buy - top_sell)
    out["confidence"] = int(max(0, min(100, dominant * 0.6 + spread * 0.8)))
    return out


def _why(oi_strength: float, vol_spike: float, momentum: float, bullish: bool) -> str:
    bits = []
    if oi_strength > 60:
        bits.append("heavy OI shift")
    if vol_spike > 60:
        bits.append("volume spike")
    if bullish and momentum > 0.1:
        bits.append("upward momentum")
    elif not bullish and momentum < -0.1:
        bits.append("downward momentum")
    return ", ".join(bits).capitalize() if bits else "Moderate flow"


def _index_bias(name: str, scan: dict, selected: str, momentum: float, pcr: float) -> str:
    row = scan.get(name)
    if row:
        chg = row.get("change_pct", 0)
        if chg > 0.2:
            return "BULLISH"
        if chg < -0.2:
            return "BEARISH"
        return "NEUTRAL"
    if name == selected:  # use live analytics for the selected index
        if momentum > 0.1 and pcr > 1.0:
            return "BULLISH"
        if momentum < -0.1 and pcr < 1.0:
            return "BEARISH"
        return "NEUTRAL"
    return "NEUTRAL"
