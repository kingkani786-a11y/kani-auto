"""Data Quality Engine (Module 13).

Validates every data stream the platform depends on and produces a
per-stream report. The overall verdict feeds the safety engine's
data-quality veto.
"""
from __future__ import annotations

import time
from typing import Any

from ..core.state import state


def _check_quotes() -> dict:
    spot = state.spot
    if not spot.get("ltp"):
        return {"status": "MISSING", "detail": "No quote received yet"}
    age = time.time() - spot.get("ts", 0)
    if age > 15:
        return {"status": "DELAYED", "detail": f"Last quote {age:.0f}s old"}
    if spot["ltp"] <= 0:
        return {"status": "CORRUPT", "detail": "Non-positive price"}
    return {"status": "OK", "detail": f"{age:.1f}s fresh"}


def _check_candles() -> dict:
    candles = state.candles
    if len(candles) < 30:
        return {"status": "MISSING", "detail": f"Only {len(candles)} candles loaded"}
    bad = sum(1 for c in candles[-100:]
              if not (c["high"] >= max(c["open"], c["close"])
                      and c["low"] <= min(c["open"], c["close"]) and c["low"] > 0))
    if bad:
        return {"status": "CORRUPT", "detail": f"{bad} malformed bars in last 100"}
    # gap check on the most recent stretch (1m bars)
    times = [c["time"] for c in candles[-60:]]
    gaps = sum(1 for a, b in zip(times, times[1:]) if b - a > 180)
    if gaps > 5:
        return {"status": "DEGRADED", "detail": f"{gaps} time gaps in last hour"}
    return {"status": "OK", "detail": f"{len(candles)} candles, contiguous"}


def _check_chain() -> dict:
    # V24 universal: judged by chain PRESENCE — an MCX contract with a live
    # chain validates like an index; a chain-less one is honestly N/A
    a = state.analytics
    if not a.get("chain"):
        if state.market_type != "INDEX":
            return {"status": "N/A", "detail": "No option chain for this contract"}
        return {"status": "MISSING", "detail": "No chain snapshot yet"}
    pcr = a.get("pcr") or 0
    if not (0.2 <= pcr <= 4.0):
        return {"status": "CORRUPT", "detail": f"PCR {pcr} outside sane range"}
    if not (a.get("call_oi") and a.get("put_oi")):
        return {"status": "DEGRADED", "detail": "OI fields empty"}
    return {"status": "OK", "detail": f"{len(a['chain'])} strikes, PCR {pcr}"}


def _check_greeks() -> dict:
    g = state.greeks
    if not (state.analytics or {}).get("chain") and state.market_type != "INDEX":
        return {"status": "N/A", "detail": "No option chain for this contract"}
    ce = (g or {}).get("ce") or {}
    if ce.get("delta") is None:
        return {"status": "MISSING", "detail": "No Greeks computed yet"}
    if not (0 < abs(float(ce["delta"])) <= 1):
        return {"status": "CORRUPT", "detail": f"ATM delta {ce['delta']} out of range"}
    return {"status": "OK", "detail": f"ATM Δ {ce['delta']}, IV {ce.get('iv')}"}


def _check_signals() -> dict:
    ts = state.heartbeats.get("signal_engine")
    if not ts:
        return {"status": "MISSING", "detail": "Signal engine has not run"}
    age = time.time() - ts
    if age > 420:
        return {"status": "DELAYED", "detail": f"Last cycle {age:.0f}s ago"}
    return {"status": "OK", "detail": f"Cycle {age:.0f}s ago"}


def _check_futures() -> dict:
    # Futures Intelligence is derived from the option/OI book (confirmation
    # layer). Healthy when the chain + OI it depends on are present.
    a = state.analytics
    fut = (state.intelligence.get("layers", {}) or {}).get("futures")
    if not fut:
        return {"status": "MISSING", "detail": "Futures layer not computed yet"}
    if not (a.get("call_oi") or a.get("oi")):
        return {"status": "DEGRADED", "detail": "OI inputs sparse"}
    return {"status": "OK", "detail": f"Bias {fut.get('futures_bias')}, "
                                      f"confirm {fut.get('confirmation_score')}%"}


def report() -> dict[str, Any]:
    checks = {
        "quotes": _check_quotes(),
        "candles": _check_candles(),
        "option_chain": _check_chain(),
        "oi": _check_chain(),
        "greeks": _check_greeks(),
        "futures": _check_futures(),
        "market_feed": _check_quotes(),
        "signals": _check_signals(),
    }
    statuses = [c["status"] for c in checks.values() if c["status"] != "N/A"]
    if any(s == "CORRUPT" for s in statuses):
        overall = "POOR"
    elif statuses.count("MISSING") + statuses.count("DELAYED") >= 2:
        overall = "POOR"
    elif any(s in ("MISSING", "DELAYED", "DEGRADED") for s in statuses):
        overall = "DEGRADED"
    else:
        overall = "GOOD"
    # data completeness: share of applicable feeds reporting OK
    completeness = round(statuses.count("OK") / len(statuses) * 100, 0) if statuses else 0
    # `overall` is the internal verdict the safety gate consumes — UNCHANGED.
    # `overall_display` is the spec's GOOD / FAIR / POOR for the UI only.
    display = {"GOOD": "GOOD", "DEGRADED": "FAIR", "POOR": "POOR"}[overall]
    return {"overall": overall, "overall_display": display,
            "completeness": completeness, "checks": checks, "ts": time.time()}
