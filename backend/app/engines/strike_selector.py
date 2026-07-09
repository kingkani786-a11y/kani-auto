"""Option Strike Selection Engine.

After a BUY CE / BUY PE decision, scores every visible strike on delta
band, OI, volume, bid-ask spread and ATM distance, then converts the
underlying entry/SL/targets into PREMIUM levels via delta (+half-gamma).
"""
from __future__ import annotations

from typing import Any

from ..config import settings
from ..core.clock import years_to_expiry as _years
from .greeks import bs_price, compute_greeks, implied_vol


def select_top(
    chain: list[dict], direction: str, spot: float, expiry: str,
    underlying_levels: dict[str, float], n: int = 5,
) -> list[dict[str, Any]]:
    """direction: BULL -> CE, BEAR -> PE. Returns the top-n ranked strikes."""
    if not chain or spot <= 0:
        return []
    side = "ce" if direction == "BULL" else "pe"
    is_call = side == "ce"
    t = _years(expiry)

    max_oi = max((r[f"{side}_oi"] for r in chain), default=1) or 1
    max_vol = max((r[f"{side}_volume"] for r in chain), default=1) or 1

    scored: list[tuple[float, dict, float, Any, float]] = []
    for r in chain:
        ltp = float(r[f"{side}_ltp"] or 0)
        if ltp <= 0:
            continue
        iv = float(r[f"{side}_iv"] or 0) / 100.0
        g = compute_greeks(spot, r["strike"], t, settings.risk_free_rate, ltp, is_call, iv_hint=iv)
        delta = abs(g.delta)

        # Delta band 0.35–0.60 is the sweet spot for directional buying
        delta_score = max(0.0, 1.0 - abs(delta - 0.45) / 0.30)
        oi_score = r[f"{side}_oi"] / max_oi
        vol_score = r[f"{side}_volume"] / max_vol
        bid, ask = float(r.get(f"{side}_bid") or 0), float(r.get(f"{side}_ask") or 0)
        spread_pct = (ask - bid) / ltp if (bid > 0 and ask > bid) else 0.02
        spread_score = max(0.0, 1.0 - spread_pct / 0.05)
        dist_score = max(0.0, 1.0 - abs(r["strike"] - spot) / (spot * 0.03))

        score = (0.30 * delta_score + 0.20 * oi_score + 0.15 * vol_score
                 + 0.15 * spread_score + 0.20 * dist_score)
        scored.append((score, r, ltp, g, spread_pct))

    scored.sort(key=lambda x: x[0], reverse=True)
    out: list[dict[str, Any]] = []
    for score, row, prem, g, spread_pct in scored[:n]:
        delta, gamma = abs(g.delta), g.gamma

        # RC1.17-hotfix — premium at an underlying level is a full Black-Scholes
        # reprice at the vol implied by the LIVE premium (exact at entry by
        # construction, intrinsic-bounded at every level). The previous
        # delta+half-gamma Taylor extrapolation exploded on expiry-day gamma:
        # 2026-07-09 live evidence — T1 claimed ₹381.94 where the exchange
        # printed ~₹230 (intrinsic ceiling), an SL "loss" projected as
        # ₹57.75→₹142.14 (SL above entry on a bought option), and a 62-lot size
        # derived from an ₹8 risk that was really ~₹55. A parabola is only
        # locally valid; a reprice cannot cross intrinsic or invert the P&L sign.
        _iv_mkt = implied_vol(prem, spot, row["strike"], t, settings.risk_free_rate, is_call) \
            or (g.iv if g.iv > 0 else 0.10)

        def prem_at(under_px: float, _k=row["strike"], _iv=_iv_mkt, _t=t) -> float:
            px = bs_price(under_px, _k, _t, settings.risk_free_rate, _iv, is_call)
            intrinsic = max(0.0, (under_px - _k) if is_call else (_k - under_px))
            return max(round(px, 2), round(intrinsic, 2), 0.05)

        out.append({
            "strike": row["strike"],
            "type": "CE" if is_call else "PE",
            "premium_entry": round(prem, 2),
            "premium_stop_loss": prem_at(underlying_levels["stop_loss"]),
            "premium_target1": prem_at(underlying_levels["target1"]),
            "premium_target2": prem_at(underlying_levels["target2"]),
            "premium_target3": prem_at(underlying_levels["target3"]),
            "delta": round(delta, 3),
            "gamma": round(gamma, 5),
            "iv": round(g.iv * 100, 1),
            "oi": row[f"{side}_oi"],
            "volume": row[f"{side}_volume"],
            "spread_pct": round(spread_pct * 100, 2),
            "selection_score": round(score * 100, 1),
            # crude probability proxy: |delta| ≈ chance of expiring ITM
            "prob_itm_pct": round(delta * 100, 1),
        })
    return out


def select(
    chain: list[dict], direction: str, spot: float, expiry: str,
    underlying_levels: dict[str, float],
) -> dict[str, Any] | None:
    top = select_top(chain, direction, spot, expiry, underlying_levels, n=1)
    return top[0] if top else None
