"""Index analytics: PCR, Max Pain, OI structure, ATM Greeks aggregation."""
from __future__ import annotations

import datetime
from typing import Any

from ..config import settings
from .greeks import compute_greeks


def _years_to_expiry(expiry: str) -> float:
    exp = datetime.datetime.fromisoformat(expiry).replace(hour=15, minute=30)
    delta = exp - datetime.datetime.now()
    return max(delta.total_seconds() / (365.0 * 86400.0), 1e-5)


def chain_sane(analytics: dict, spot: float) -> bool:
    """V40 universal sanity: the ATM row must respect put-call parity
    (CE − PE ≈ Spot − Strike). A chain that fails belongs to the wrong
    expiry/underlying — every consumer must refuse it, for EVERY instrument."""
    rows = (analytics or {}).get("chain") or []
    atm = (analytics or {}).get("atm_strike")
    if not rows or not atm or not spot:
        return False
    row = next((r for r in rows if float(r.get("strike", 0)) == float(atm)), None)
    if not row:
        return False
    ce, pe = float(row.get("ce_ltp") or 0), float(row.get("pe_ltp") or 0)
    if ce <= 0 or pe <= 0:
        return True          # missing quotes ≠ wrong chain; other guards handle staleness
    return abs((ce - pe) - (spot - float(atm))) <= max(spot * 0.02, 2.0)


def analyze_chain(chain: dict, spot: float, expiry: str, strike_step: float) -> dict[str, Any]:
    """Digest a Dhan option-chain payload into dashboard metrics.

    chain["oc"] = {"24000.000000": {"ce": {...}, "pe": {...}}, ...}
    Each leg carries: last_price, oi, previous_oi, volume, implied_volatility,
    greeks {delta, gamma, theta, vega}.
    """
    oc: dict = chain.get("oc", {})
    if not oc or spot <= 0:
        return {}

    t = _years_to_expiry(expiry)
    total_ce_oi = total_pe_oi = 0.0
    ce_oi_chg = pe_oi_chg = 0.0
    ce_vol = pe_vol = 0.0
    strikes: list[float] = []
    rows: list[dict] = []

    for k, legs in sorted(oc.items(), key=lambda kv: float(kv[0])):
        strike = float(k)
        ce, pe = legs.get("ce") or {}, legs.get("pe") or {}
        ce_oi, pe_oi = float(ce.get("oi", 0)), float(pe.get("oi", 0))
        total_ce_oi += ce_oi
        total_pe_oi += pe_oi
        ce_oi_chg += ce_oi - float(ce.get("previous_oi", ce_oi))
        pe_oi_chg += pe_oi - float(pe.get("previous_oi", pe_oi))
        ce_vol += float(ce.get("volume", 0))
        pe_vol += float(pe.get("volume", 0))
        strikes.append(strike)
        rows.append({
            "strike": strike,
            "ce_ltp": ce.get("last_price", 0), "ce_oi": ce_oi,
            "ce_oi_chg": ce_oi - float(ce.get("previous_oi", ce_oi)),
            "ce_iv": ce.get("implied_volatility", 0), "ce_volume": ce.get("volume", 0),
            "ce_bid": ce.get("top_bid_price", 0), "ce_ask": ce.get("top_ask_price", 0),
            "pe_ltp": pe.get("last_price", 0), "pe_oi": pe_oi,
            "pe_oi_chg": pe_oi - float(pe.get("previous_oi", pe_oi)),
            "pe_iv": pe.get("implied_volatility", 0), "pe_volume": pe.get("volume", 0),
            "pe_bid": pe.get("top_bid_price", 0), "pe_ask": pe.get("top_ask_price", 0),
        })

    # Max pain: strike minimizing total intrinsic payout to option buyers
    max_pain, best_pain = spot, float("inf")
    for k in strikes:
        pain = 0.0
        for r in rows:
            pain += max(k - r["strike"], 0) * r["ce_oi"]
            pain += max(r["strike"] - k, 0) * r["pe_oi"]
        if pain < best_pain:
            best_pain, max_pain = pain, k

    pcr = total_pe_oi / total_ce_oi if total_ce_oi else 0.0

    # ATM Greeks (broker-provided when available, Black-Scholes fallback)
    atm = min(strikes, key=lambda k: abs(k - spot))
    atm_row = oc.get(f"{atm:.6f}") or oc.get(str(atm)) or {}
    greeks_out = {}
    for side, is_call in (("ce", True), ("pe", False)):
        leg = atm_row.get(side) or {}
        g = leg.get("greeks") or {}
        iv = float(leg.get("implied_volatility", 0)) / 100.0
        if g.get("delta") is not None:
            greeks_out[side] = {
                "delta": g.get("delta"), "gamma": g.get("gamma"),
                "theta": g.get("theta"), "vega": g.get("vega"),
                "iv": round(iv, 4),
            }
        else:
            greeks_out[side] = compute_greeks(
                spot, atm, t, settings.risk_free_rate,
                float(leg.get("last_price", 0)), is_call, iv_hint=iv,
            ).dict()

    # Trim the visible chain to ATM ± 10 strikes. Stocks register with
    # strike_step 0 — infer the real step from the chain itself so the
    # window never collapses to a single strike (V40 fix: bogus stock picks).
    if strike_step <= 0:
        diffs = [b - a for a, b in zip(strikes, strikes[1:]) if b > a]
        strike_step = min(diffs) if diffs else max(spot * 0.01, 1.0)
    lo, hi = atm - 10 * strike_step, atm + 10 * strike_step
    visible = [r for r in rows if lo <= r["strike"] <= hi]

    return {
        "expiry": expiry,
        "atm_strike": atm,
        "pcr": round(pcr, 3),
        "max_pain": max_pain,
        "call_oi": total_ce_oi,
        "put_oi": total_pe_oi,
        "call_oi_change": ce_oi_chg,
        "put_oi_change": pe_oi_chg,
        "call_volume": ce_vol,
        "put_volume": pe_vol,
        "greeks": greeks_out,
        "chain": visible,
    }
