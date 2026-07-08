"""Portfolio Risk Engine — position sizing and exposure over paper trades."""
from __future__ import annotations

from typing import Any


def position_size(capital: float, risk_pct: float, entry: float, stop: float, lot_size: int = 1) -> dict:
    """Risk-based sizing: how many units so a stop-out costs risk_pct of capital."""
    per_unit_risk = abs(entry - stop)
    if per_unit_risk <= 0 or capital <= 0:
        return {"qty": 0, "lots": 0, "risk_amount": 0}
    risk_amount = capital * risk_pct / 100.0
    qty = int(risk_amount / per_unit_risk)
    lots = max(qty // lot_size, 0) if lot_size > 1 else qty
    qty_final = lots * lot_size if lot_size > 1 else qty
    return {
        "qty": qty_final,
        "lots": lots if lot_size > 1 else None,
        "risk_amount": round(min(qty_final * per_unit_risk, risk_amount), 2),
        "risk_per_unit": round(per_unit_risk, 2),
    }


def portfolio(trades: list[dict], capital: float, risk_pct: float) -> dict[str, Any]:
    open_t = [t for t in trades if t["status"] == "OPEN"]
    closed = [t for t in trades if t["status"] == "CLOSED"]

    exposure = sum(t["entry"] * t["qty"] for t in open_t)
    open_risk = sum(abs(t["entry"] - (t["stop_loss"] or t["entry"] * 0.99)) * t["qty"] for t in open_t)

    # equity curve -> max drawdown
    eq, peak, max_dd = 0.0, 0.0, 0.0
    for t in sorted(closed, key=lambda x: x.get("closed_at") or ""):
        eq += t.get("pnl") or 0
        peak = max(peak, eq)
        max_dd = max(max_dd, peak - eq)

    realized = round(sum(t.get("pnl") or 0 for t in closed), 2)

    # ---- V7.5 Portfolio Intelligence ----
    # correlation risk: open positions pointing the same way are one bet
    longs = sum(1 for t in open_t if t["side"] == "LONG")
    shorts = len(open_t) - longs
    same_dir = max(longs, shorts)
    correlation_risk = round(same_dir / len(open_t) * 100, 0) if open_t else 0.0
    # concentration: largest single-symbol share of exposure
    by_sym: dict[str, float] = {}
    for t in open_t:
        by_sym[t["symbol"]] = by_sym.get(t["symbol"], 0) + t["entry"] * t["qty"]
    concentration = round(max(by_sym.values()) / exposure * 100, 0) if exposure else 0.0
    # portfolio heat: open risk vs a 6%-of-capital ceiling
    heat = round(min(open_risk / (capital * 0.06) * 100, 100), 0) if capital else 0.0
    # capital efficiency: realized PnL per unit of capital deployed
    efficiency = round(realized / capital * 100, 2) if capital else 0.0
    risk_clusters = [s for s, v in by_sym.items() if exposure and v / exposure > 0.5]

    return {
        "correlation_risk_pct": correlation_risk,
        "concentration_pct": concentration,
        "portfolio_heat_pct": heat,
        "capital_efficiency_pct": efficiency,
        "risk_clusters": risk_clusters,
        "capital": capital,
        "risk_per_trade_pct": risk_pct,
        "open_positions": len(open_t),
        "exposure": round(exposure, 2),
        "exposure_pct": round(exposure / capital * 100, 1) if capital else 0,
        "open_risk": round(open_risk, 2),
        "open_risk_pct": round(open_risk / capital * 100, 2) if capital else 0,
        "realized_pnl": realized,
        "max_drawdown": round(max_dd, 2),
        "equity": round(capital + realized, 2),
        "warnings": (["Portfolio exposure above 60% of capital"] if capital and exposure / capital > 0.6 else [])
        + (["Open risk exceeds 3% of capital"] if capital and open_risk / capital > 0.03 else []),
    }
