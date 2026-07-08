"""Order Flow Intelligence (Module 6).

True tick-by-tick order flow isn't available from the REST feed, so this
engine derives flow proxies from candle anatomy: where bars close in their
range (aggression), signed volume (delta imbalance), and effort-vs-result
(absorption, vacuum, hidden accumulation/distribution). Output is an
informational Order Flow Score, never a standalone signal.
"""
from __future__ import annotations

from typing import Any


def analyze(candles: list[dict]) -> dict[str, Any]:
    if len(candles) < 30:
        return {"score": 50, "events": [], "notes": [], "delta_imbalance": 0}

    recent = candles[-20:]
    vols = [max(float(c.get("volume", 0)), 0.0) for c in candles[-40:]]
    avg_vol = sum(vols) / len(vols) or 1.0

    events: list[str] = []
    notes: list[str] = []
    score = 50.0

    # signed volume delta: close location within the bar weights the volume
    delta = 0.0
    buy_aggr = sell_aggr = 0
    for c in recent:
        rng = max(c["high"] - c["low"], 1e-9)
        loc = ((c["close"] - c["low"]) / rng) * 2 - 1     # -1 weak close … +1 strong
        v = max(float(c.get("volume", 0)), 0.0)
        delta += loc * v
        if v > 1.8 * avg_vol and loc > 0.5:
            buy_aggr += 1
        elif v > 1.8 * avg_vol and loc < -0.5:
            sell_aggr += 1

    total_v = sum(max(float(c.get("volume", 0)), 0.0) for c in recent) or 1.0
    imbalance = delta / total_v                            # -1 … +1
    score += imbalance * 30

    if buy_aggr >= 3:
        events.append("AGGRESSIVE_BUYING")
        notes.append("Repeated high-volume bars closing strong — aggressive buying")
        score += 8
    if sell_aggr >= 3:
        events.append("AGGRESSIVE_SELLING")
        notes.append("Repeated high-volume bars closing weak — aggressive selling")
        score -= 8

    # liquidity vacuum: big range on thin volume = nothing resting in the book
    last = recent[-1]
    last_rng = (last["high"] - last["low"]) / last["close"] if last["close"] else 0
    avg_rng = sum((c["high"] - c["low"]) / c["close"] for c in recent) / len(recent)
    if last_rng > 2.5 * avg_rng and float(last.get("volume", 0)) < 0.7 * avg_vol:
        events.append("LIQUIDITY_VACUUM")
        notes.append("Wide bar on thin volume — liquidity vacuum, slippage risk")

    # hidden accumulation/distribution: flat price, persistent one-sided delta
    px_chg = abs(recent[-1]["close"] / recent[0]["close"] - 1) * 100
    if px_chg < 0.15:
        if imbalance > 0.25:
            events.append("HIDDEN_ACCUMULATION")
            notes.append("Price flat while delta skews positive — hidden accumulation")
            score += 6
        elif imbalance < -0.25:
            events.append("HIDDEN_DISTRIBUTION")
            notes.append("Price flat while delta skews negative — hidden distribution")
            score -= 6

    return {
        "score": round(max(0.0, min(100.0, score)), 1),   # >50 buy-side flow
        "delta_imbalance": round(imbalance, 3),
        "events": events,
        "notes": notes,
    }
