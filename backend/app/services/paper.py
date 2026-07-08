"""Paper Trading Engine + Trade Review Engine.

Virtual trades only — nothing ever reaches the broker. Each trade stores
a snapshot of the signal that spawned it so the review engine can explain
afterwards why it worked or failed.
"""
from __future__ import annotations

import time
import uuid
from typing import Any

_trades: list[dict] = []


def open_trade(
    symbol: str, side: str, qty: float, entry: float,
    stop_loss: float | None, target: float | None,
    signal_snapshot: dict[str, Any] | None,
) -> dict:
    trade = {
        "id": str(uuid.uuid4())[:8],
        "symbol": symbol,
        "side": side.upper(),               # LONG | SHORT
        "qty": qty,
        "entry": entry,
        "stop_loss": stop_loss,
        "target": target,
        "opened_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "status": "OPEN",
        "exit": None,
        "closed_at": None,
        "pnl": None,
        "review": None,
        "snapshot": _trim_snapshot(signal_snapshot),
    }
    _trades.append(trade)
    return trade


def _trim_snapshot(s: dict | None) -> dict:
    if not s:
        return {}
    sig = s.get("signal", {})
    return {
        "signal": sig.get("signal"),
        "confidence": sig.get("confidence"),
        "confirmations": sig.get("confirmations", []),
        "regime": s.get("layers", {}).get("regime", {}).get("regime"),
        "alignment": s.get("layers", {}).get("mtf", {}).get("alignment"),
        "prob_success": s.get("layers", {}).get("probability", {}).get("prob_success"),
        "reasons": sig.get("reasons", [])[:4],
    }


def close_trade(trade_id: str, exit_price: float) -> dict | None:
    for t in _trades:
        if t["id"] == trade_id and t["status"] == "OPEN":
            t["exit"] = exit_price
            t["closed_at"] = time.strftime("%Y-%m-%d %H:%M:%S")
            sign = 1 if t["side"] == "LONG" else -1
            t["pnl"] = round((exit_price - t["entry"]) * sign * t["qty"], 2)
            t["status"] = "CLOSED"
            t["review"] = _review(t)
            return t
    return None


def _mentor_scores(t: dict, won: bool) -> dict:
    """AI Trade Mentor — grade the trader's process, not just the outcome."""
    snap = t.get("snapshot") or {}
    conf = float(snap.get("confidence") or 50)
    regime_v = snap.get("regime") or ""
    align = float(snap.get("alignment") or 50)

    # Entry quality: how good were the conditions at entry
    entry_q = min(100.0, conf * 0.6 + align * 0.4)
    if regime_v in ("TRENDING", "HIGH_MOMENTUM"):
        entry_q = min(100.0, entry_q + 10)
    elif regime_v in ("VOLATILE", "LOW_MOMENTUM", "EXPIRY_PINNING"):
        entry_q = max(0.0, entry_q - 15)

    # Exit quality: capture vs available range (target as proxy for available)
    exit_q = 50.0
    if t.get("exit") is not None and t.get("target") and t.get("entry"):
        avail = abs(t["target"] - t["entry"])
        got = (t["exit"] - t["entry"]) * (1 if t["side"] == "LONG" else -1)
        exit_q = max(0.0, min(100.0, 50 + (got / avail) * 50)) if avail else 50.0

    # Discipline: did the trade have a stop, and was the loss within it
    discipline = 80.0 if t.get("stop_loss") else 30.0
    if not won and t.get("stop_loss") and t.get("exit") is not None:
        d = 1 if t["side"] == "LONG" else -1
        if (t["exit"] - t["stop_loss"]) * d < -0.001 * t["entry"]:
            discipline = 20.0  # exited beyond the stop — the cardinal sin

    # Patience: hold time vs a scalp (rough heuristic from timestamps)
    patience = 60.0
    try:
        from datetime import datetime
        dt = (datetime.strptime(t["closed_at"], "%Y-%m-%d %H:%M:%S")
              - datetime.strptime(t["opened_at"], "%Y-%m-%d %H:%M:%S")).total_seconds()
        patience = 30.0 if dt < 120 else 60.0 if dt < 900 else 80.0
    except Exception:
        pass

    risk_mgmt = (80.0 if t.get("stop_loss") and t.get("target") else
                 55.0 if t.get("stop_loss") else 25.0)

    overall = round(0.30 * entry_q + 0.20 * exit_q + 0.20 * discipline
                    + 0.10 * patience + 0.20 * risk_mgmt, 1)
    return {
        "entry_quality": round(entry_q, 1),
        "exit_quality": round(exit_q, 1),
        "discipline": round(discipline, 1),
        "patience": round(patience, 1),
        "risk_management": round(risk_mgmt, 1),
        "overall": overall,
    }


def _review(t: dict) -> dict:
    """Trade Review Engine — explain success/failure, suggest improvement."""
    won = (t["pnl"] or 0) > 0
    snap = t.get("snapshot") or {}
    why: list[str] = []
    improve: list[str] = []

    conf = snap.get("confidence")
    regime_v = snap.get("regime")
    align = snap.get("alignment")
    confirms = snap.get("confirmations") or []

    if won:
        if confirms:
            why.append(f"Entry had {len(confirms)} confirming layers ({', '.join(confirms[:4])}) — confluence did its job.")
        if regime_v in ("TRENDING", "HIGH_MOMENTUM"):
            why.append(f"Trade ran with a {regime_v.replace('_', ' ').lower()} regime, the highest-probability environment.")
        if align and align >= 70:
            why.append(f"Timeframe alignment was {align}%, so all horizons pushed the same way.")
        if not why:
            why.append("Price moved with the position; entry conditions were favorable.")
        improve.append("Consider trailing the stop to T1 after first target to protect winners like this.")
    else:
        if conf is not None and conf < 70:
            why.append(f"Confidence at entry was only {conf}% — a marginal setup that didn't need to be taken.")
        if regime_v in ("RANGE_BOUND", "VOLATILE", "LOW_MOMENTUM", "EXPIRY_PINNING"):
            why.append(f"Regime was {regime_v.replace('_', ' ').lower()} — hostile conditions for directional trades.")
        if align is not None and align < 65:
            why.append(f"Timeframe alignment was just {align}% — higher timeframes weren't on side.")
        if not why:
            why.append("Conditions flipped after entry; the stop did its job limiting the damage.")
        improve.append("Wait for alignment ≥ 70% and a trending regime before the next entry.")
        if t.get("stop_loss") is None:
            improve.append("Always set a stop loss — undefined risk is the fastest way to ruin.")

    return {"outcome": "WIN" if won else "LOSS", "why": why, "improve": improve,
            "mentor": _mentor_scores(t, won)}


def stats() -> dict:
    closed = [t for t in _trades if t["status"] == "CLOSED"]
    wins = [t for t in closed if (t["pnl"] or 0) > 0]
    total_pnl = round(sum(t["pnl"] or 0 for t in closed), 2)
    return {
        "open": sum(1 for t in _trades if t["status"] == "OPEN"),
        "closed": len(closed),
        "wins": len(wins),
        "win_rate": round(len(wins) / len(closed) * 100, 1) if closed else 0.0,
        "total_pnl": total_pnl,
    }


def list_trades() -> list[dict]:
    return list(reversed(_trades))


def mark_to_market(spot_by_symbol: dict[str, float]) -> None:
    for t in _trades:
        if t["status"] == "OPEN":
            px = spot_by_symbol.get(t["symbol"])
            if px:
                sign = 1 if t["side"] == "LONG" else -1
                t["unrealized"] = round((px - t["entry"]) * sign * t["qty"], 2)
