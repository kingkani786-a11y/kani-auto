"""Depth of Market engine (Module 7).

Works on the 5-level depth the broker quote API returns (when present).
Degrades gracefully to an empty result when depth isn't provided.
"""
from __future__ import annotations

from typing import Any


def analyze(depth: dict | None, ltp: float) -> dict[str, Any]:
    if not depth or not isinstance(depth, dict):
        return {"available": False}
    buys = depth.get("buy") or []
    sells = depth.get("sell") or []
    if not buys or not sells:
        return {"available": False}

    def levels(side: list) -> list[tuple[float, float]]:
        out = []
        for l in side[:5]:
            try:
                out.append((float(l.get("price") or 0), float(l.get("quantity") or 0)))
            except (TypeError, ValueError):
                pass
        return [l for l in out if l[0] > 0]

    b, s = levels(buys), levels(sells)
    if not b or not s:
        return {"available": False}

    bid_qty = sum(q for _, q in b)
    ask_qty = sum(q for _, q in s)
    bid_wall = max(b, key=lambda x: x[1])
    ask_wall = max(s, key=lambda x: x[1])
    imbalance = (bid_qty - ask_qty) / (bid_qty + ask_qty) if (bid_qty + ask_qty) else 0.0
    spread_pct = (s[0][0] - b[0][0]) / ltp * 100 if ltp else 0.0

    # Liquidity Score: tight spread + deep book + balance = healthy
    score = 50.0
    score += max(0.0, 25 - spread_pct * 250)            # tighter spread, higher score
    score += min((bid_qty + ask_qty) / 10000, 15)       # absolute depth
    score -= abs(imbalance) * 20                        # heavy skew = fragile
    notes: list[str] = []
    if bid_wall[1] > bid_qty * 0.5:
        notes.append(f"Bid wall at {bid_wall[0]:,.1f} ({bid_wall[1]:,.0f}) — visible support")
    if ask_wall[1] > ask_qty * 0.5:
        notes.append(f"Ask wall at {ask_wall[0]:,.1f} ({ask_wall[1]:,.0f}) — visible supply")
    if imbalance > 0.4:
        notes.append("Bids dominate the book — short-term upward pressure")
    elif imbalance < -0.4:
        notes.append("Asks dominate the book — short-term downward pressure")

    return {
        "available": True,
        "liquidity_score": round(max(0.0, min(100.0, score)), 1),
        "bid_qty": bid_qty,
        "ask_qty": ask_qty,
        "imbalance": round(imbalance, 3),
        "bid_wall": {"price": bid_wall[0], "qty": bid_wall[1]},
        "ask_wall": {"price": ask_wall[0], "qty": ask_wall[1]},
        "spread_pct": round(spread_pct, 4),
        "notes": notes,
    }
