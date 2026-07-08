"""Futures Intelligence Layer (V13.1) — CONFIRMATION ONLY.

Derives a futures read from data the platform already computes (trend, OI
structure, order flow, smart money) and scores how strongly it CONFIRMS the
existing AI signal. It never alters, overrides, or feeds back into the
decision — it is a transparency/confirmation layer only. Cost of carry needs
a live futures price; when that's unavailable it is reported as N/A rather
than fabricated.
"""
from __future__ import annotations

from typing import Any

from . import smart_money


def _band(score: float) -> str:
    return ("VERY STRONG" if score >= 76 else "STRONG" if score >= 51
            else "MODERATE" if score >= 26 else "WEAK")


def compute(layers: dict[str, Any], analytics: dict[str, Any], win_dir: str,
            momentum_pct: float, futures_price: float | None = None,
            spot: float | None = None) -> dict[str, Any]:
    trend = layers.get("trend", {})
    of = layers.get("order_flow", {})

    # ---- OI change (net of the option book as a market-wide proxy) ----
    call_chg = float(analytics.get("call_oi_change") or 0)
    put_chg = float(analytics.get("put_oi_change") or 0)
    net_oi_chg = put_chg - call_chg          # put adds + / call adds - (bullish if puts written)
    total_oi = float((analytics.get("call_oi") or 0) + (analytics.get("put_oi") or 0)) or 1.0
    oi_chg_pct = net_oi_chg / total_oi * 100

    # ---- build-up classification (price vs OI), reuses the SM classifier ----
    underlying_flow = (layers.get("smart_money", {}) or {}).get("underlying")
    if not underlying_flow:
        underlying_flow = smart_money.classify_underlying(momentum_pct, oi_chg_pct)
    buildup = underlying_flow.replace("_", " ").title()

    # ---- directional lean from trend + build-up + order flow ----
    lean = 0.0
    td = trend.get("direction", "NEUTRAL")
    if td == "BULL": lean += 2
    elif td == "BEAR": lean -= 2
    if underlying_flow in ("LONG_BUILDUP", "SHORT_COVERING"): lean += 2
    elif underlying_flow in ("SHORT_BUILDUP", "LONG_UNWINDING"): lean -= 2
    ofs = float(of.get("score") or 50)
    if ofs > 58: lean += 1
    elif ofs < 42: lean -= 1

    futures_bias = ("BULLISH" if lean >= 2 else "BEARISH" if lean <= -2
                    else "MIXED" if abs(lean) == 1 else "NEUTRAL")

    # ---- OI / volume / futures trend descriptors ----
    oi_trend = "RISING" if oi_chg_pct > 0.2 else "FALLING" if oi_chg_pct < -0.2 else "FLAT"
    volume_trend = "EXPANDING" if ofs > 58 else "CONTRACTING" if ofs < 42 else "STEADY"
    futures_trend = trend.get("trend", "NEUTRAL")

    # ---- cost of carry (needs futures price) ----
    if futures_price and spot and spot > 0:
        cost_of_carry = round((futures_price - spot) / spot * 100, 2)
        coc_label = f"{cost_of_carry:+.2f}% ({'premium' if cost_of_carry >= 0 else 'discount'})"
    else:
        cost_of_carry = None
        coc_label = "N/A (futures price not in feed)"

    # ---- confirmation score: agreement of futures lean with the AI signal ----
    if win_dir in ("BULL", "BEAR"):
        want = 1 if win_dir == "BULL" else -1
        agree = lean * want                  # >0 agrees, <0 contradicts
        # map [-5..+5] agreement to 0..100, centred at 50
        confirmation = max(0.0, min(100.0, 50 + agree * 12))
        relation = ("CONFIRMS" if agree >= 2 else "CONTRADICTS" if agree <= -2 else "NEUTRAL ON")
    else:
        # no active trade — report standalone futures conviction
        confirmation = max(0.0, min(100.0, 50 + abs(lean) * 12 * (1 if lean else 0)))
        relation = "NO ACTIVE SIGNAL"

    notes: list[str] = []
    if underlying_flow != "NEUTRAL":
        notes.append(f"Futures positioning shows {buildup.lower()}")
    if oi_trend != "FLAT":
        notes.append(f"Open interest {oi_trend.lower()}")
    if win_dir in ("BULL", "BEAR"):
        notes.append(f"Futures {relation.lower()} the {'bullish' if win_dir=='BULL' else 'bearish'} signal")

    return {
        "futures_trend": futures_trend,
        "oi_trend": oi_trend,
        "buildup": buildup,
        "buildup_code": underlying_flow,
        "cost_of_carry": cost_of_carry,
        "cost_of_carry_label": coc_label,
        "volume_trend": volume_trend,
        "oi_change_pct": round(oi_chg_pct, 2),
        "futures_bias": futures_bias,
        "confirmation_score": round(confirmation, 0),
        "confirmation_label": _band(confirmation),
        "relation": relation,
        "notes": notes[:3],
    }


def explainer(layers: dict[str, Any], futures: dict[str, Any],
              final_confidence: float, win_dir: str) -> dict[str, Any]:
    """Decision transparency: per-engine contribution table (display only)."""
    score_key = "score_bull" if win_dir == "BULL" else "score_bear"

    def contrib(layer_key: str, weight: float) -> int:
        s = float((layers.get(layer_key, {}) or {}).get(score_key, 50))
        return round((s - 50) * weight)

    fut_contrib = round((futures.get("confirmation_score", 50) - 50) * 0.4)
    rows = [
        {"engine": "OPTIONS ANALYSIS", "contribution": contrib("oi", 1.0)},
        {"engine": "FUTURES ANALYSIS", "contribution": fut_contrib},
        {"engine": "MARKET STRUCTURE", "contribution": contrib("structure", 1.0)},
        {"engine": "SMART MONEY", "contribution": contrib("smart_money", 0.8)},
        {"engine": "RISK ANALYSIS", "contribution": contrib("trend", 0.5)},
    ]
    for r in rows:
        c = r["contribution"]
        r["bias"] = "Bullish" if c > 0 else "Bearish" if c < 0 else "Neutral"
        r["display"] = f"{'+' if c >= 0 else ''}{c}"
    return {"rows": rows, "final_confidence": round(final_confidence, 0)}
