"""Phase 14 — Kill Switch Engine (capital protection first).

Trips a FORCE-WAIT when the environment is unsafe to trade, regardless of how
good a signal looks. Reads only existing state (no new data / no new API calls).
The Golden Rule: capital protection over profit.

Hard veto (FORCE WAIT) when ANY of:
  • 3 consecutive losses
  • calibration score < 55          (forecasts are mis-calibrated)
  • data completeness < 60          (feed too sparse to trust)
  • reliability collapse / broker cooldown
  • feed inconsistency (data quality POOR)
Soft caution (advisory only):
  • abnormal volatility, low-confidence regime, degraded data
"""
from __future__ import annotations

from collections import deque
from typing import Any

MAX_CONSECUTIVE_LOSSES = 3
MIN_CALIBRATION = 55
MIN_DATA_COMPLETENESS = 60


def evaluate(data_quality: str, atr_pct: float, regime_score: float,
             outcomes: deque | list, broker_cooldown: bool,
             calibration_score: float | None = None,
             data_completeness: float | None = None,
             market_closed: bool = False) -> dict[str, Any]:
    reasons: list[str] = []
    caution: list[str] = []
    recovery: list[str] = []

    # reliability collapse / broker failure
    if broker_cooldown:
        reasons.append("Broker in rate-limit cooldown — data unreliable")
        recovery.append("Broker cooldown clears")
    # feed inconsistency
    if data_quality == "POOR":
        reasons.append("Data quality POOR — feed inconsistent")
        recovery.append("Data quality returns to GOOD/FAIR")
    # sparse feed
    if data_completeness is not None and data_completeness < MIN_DATA_COMPLETENESS:
        reasons.append(f"Data completeness {data_completeness:.0f}% (< {MIN_DATA_COMPLETENESS}%)")
        recovery.append(f"Data completeness ≥ {MIN_DATA_COMPLETENESS}%")
    # forecast mis-calibration
    if calibration_score is not None and calibration_score < MIN_CALIBRATION:
        reasons.append(f"Calibration {calibration_score:.0f} (< {MIN_CALIBRATION}) — forecasts mis-tuned")
        recovery.append(f"Calibration recovers to ≥ {MIN_CALIBRATION}")
    # consecutive losses
    tail = list(outcomes)[-MAX_CONSECUTIVE_LOSSES:]
    if len(tail) >= MAX_CONSECUTIVE_LOSSES and all(o.get("win") == 0 for o in tail):
        reasons.append(f"{MAX_CONSECUTIVE_LOSSES} consecutive losses — step back")
        recovery.append("Next signal is a win, or new session")

    # soft cautions (never force wait on their own)
    if atr_pct > 1.8:
        caution.append(f"Abnormal volatility ({atr_pct:.2f}% ATR)")
    if regime_score < 35:
        caution.append("Low-confidence regime")
    # RC1.14 — data_quality.report()'s per-stream checks don't know about
    # market hours: pre/post-market MISSING quotes/candles/chain routinely
    # land it on "DEGRADED" even though nothing is actually wrong (same root
    # cause RC1.11 fixed for Self-Check/Feed Diagnostics — those two already
    # treat this as a calm pause; Kill Switch's soft caution did not, so it
    # showed "CAUTION — Degraded data" while the header said "Data: GOOD").
    # Hard veto conditions above (cooldown/POOR/completeness/calibration/
    # losses) are untouched — this only silences the soft advisory label.
    if data_quality == "DEGRADED" and not market_closed:
        caution.append("Degraded data")

    active = bool(reasons)
    level = "DANGER" if active else "CAUTION" if caution else "SAFE"
    # RC1.16.10 fix #6b — post-close context NOTE only (owner precedence
    # spec). When the market is closed, data-quality vetoes are expected
    # (feeds idle) and there is nothing to veto anyway; every hard trigger
    # above stays exactly as-is — this adds words, never removes a veto.
    note = ("Market closed — data feeds are idle, so data-quality triggers "
            "are expected and clear automatically at open. No fault."
            if market_closed and active and data_quality in ("POOR", "DEGRADED")
            else None)
    return {
        "active": active,
        "level": level,
        "reasons": reasons,
        "caution": caution,
        "recovery": recovery,
        "recovery_condition": "; ".join(recovery) if recovery else "—",
        "force_wait": active,
        "market_closed_note": note,
    }
