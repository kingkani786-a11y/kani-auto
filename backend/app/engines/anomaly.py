"""Anomaly Detection Engine — unusual OI / volume / IV / price behaviour.

Keeps short rolling baselines per symbol and flags multi-sigma departures.
Anomalies are warnings, not signals: they feed the risk picture and the
alert engine, never a trade decision by themselves.
"""
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Any

_base: dict[str, dict[str, deque]] = defaultdict(
    lambda: {"oi": deque(maxlen=40), "vol": deque(maxlen=40),
             "iv": deque(maxlen=40), "px": deque(maxlen=40)})
_last_alert: dict[str, float] = {}
COOLDOWN = 900.0


def _zscore(series: deque, value: float) -> float:
    if len(series) < 10:
        return 0.0
    mean = sum(series) / len(series)
    var = sum((x - mean) ** 2 for x in series) / (len(series) - 1)
    # floor the scale at 2% of the mean so a dead-flat baseline still
    # flags a genuine shock instead of dividing by zero
    sd = max(var ** 0.5, abs(mean) * 0.02, 1e-9)
    return (value - mean) / sd


def observe(symbol: str, spot: float, analytics: dict[str, Any]) -> list[dict]:
    """Call on every option tick. Returns newly detected anomalies."""
    b = _base[symbol]
    total_oi = float((analytics.get("call_oi") or 0) + (analytics.get("put_oi") or 0))
    total_vol = float((analytics.get("call_volume") or 0) + (analytics.get("put_volume") or 0))
    iv = float((analytics.get("greeks", {}).get("ce") or {}).get("iv") or 0) * 100

    found: list[dict] = []
    now = time.time()

    def flag(kind: str, msg: str, severity: str) -> None:
        key = f"{symbol}:{kind}"
        if now - _last_alert.get(key, 0) > COOLDOWN:
            _last_alert[key] = now
            found.append({"kind": kind, "message": msg, "severity": severity,
                          "symbol": symbol, "ts": now})

    if total_oi:
        z = _zscore(b["oi"], total_oi)
        if abs(z) > 3:
            flag("UNUSUAL_OI", f"Total OI moved {z:+.1f}σ from its recent baseline — "
                 "heavy repositioning underway", "HIGH" if abs(z) > 4 else "MEDIUM")
        b["oi"].append(total_oi)
    if total_vol:
        z = _zscore(b["vol"], total_vol)
        if z > 3:
            flag("UNUSUAL_VOLUME", f"Option volume {z:+.1f}σ above baseline — "
                 "urgency in the options market", "MEDIUM")
        b["vol"].append(total_vol)
    if iv > 0:
        z = _zscore(b["iv"], iv)
        if abs(z) > 2.5:
            d = "spiking" if z > 0 else "collapsing"
            flag("UNUSUAL_IV", f"ATM IV {d} ({z:+.1f}σ, now {iv:.1f}%) — "
                 "expect violent moves" if z > 0 else f"ATM IV {d} ({z:+.1f}σ) — premium sellers in control",
                 "HIGH" if z > 0 else "MEDIUM")
        b["iv"].append(iv)
    if spot > 0:
        if len(b["px"]) >= 10:
            rets = [abs(b["px"][i] / b["px"][i - 1] - 1) for i in range(1, len(b["px"]))]
            avg_ret = sum(rets) / len(rets) or 1e-6
            last_ret = abs(spot / b["px"][-1] - 1)
            if last_ret > 5 * avg_ret and last_ret > 0.002:
                flag("SUDDEN_MOVE", f"Price jumped {last_ret * 100:.2f}% in one interval — "
                     "5x the recent norm; stand back until it settles", "HIGH")
        b["px"].append(spot)

    return found
