"""Phase D — Disaster Recovery / Safe Mode.

Broader than the Kill Switch (which is about trade-quality risk): Safe Mode
watches for INFRASTRUCTURE failure — broker/API/feed/websocket/data collapse —
and, when any trips, freezes new signals into WAIT, alerts, and logs the
incident while preserving all learning/memory/logs. Derivation-only over signals
the platform already has. Fail-safe: any error → treat as not-triggered (the
normal gate + kill switch still protect capital).
"""
from __future__ import annotations

import logging
import time
from typing import Any

log = logging.getLogger("safe_mode")

_incidents: list[dict] = []          # last incidents (in-memory ring)
_active_since: float | None = None


def evaluate(connected: bool, data_quality: str, broker_stats: dict,
             ws_clients: int, signal_age_sec: float | None) -> dict[str, Any]:
    global _active_since
    triggers: list[str] = []

    # broker / API failure
    if broker_stats.get("cooldown_active"):
        triggers.append("BROKER: rate-limit cooldown active")
    if (broker_stats.get("health_score") or 100) < 40:
        triggers.append("API: broker health critical")
    # data quality collapse
    if data_quality == "POOR":
        triggers.append("DATA: quality collapsed (POOR)")
    # feed freeze — signal engine hasn't run well past its cycle while connected
    if connected and signal_age_sec is not None and signal_age_sec > 900:
        triggers.append("FEED: signal engine stalled (>15m)")
    # NOTE: websocket count is informational (0 clients just means no UI open),
    # so it is not a trigger on its own.

    active = bool(triggers)
    if active and _active_since is None:
        _active_since = time.time()
        inc = {"ts": _active_since, "triggers": list(triggers)}
        _incidents.append(inc)
        del _incidents[:-50]
        log.warning("SAFE MODE engaged: %s", "; ".join(triggers))
    elif not active and _active_since is not None:
        log.info("SAFE MODE cleared")
        _active_since = None

    return {
        "active": active,
        "triggers": triggers,
        "since": _active_since,
        "actions": (["Freeze new signals", "Force WAIT mode", "Alert user",
                     "Log incident", "Preserve learning/memory/logs"] if active else []),
        "recovery": ("Auto-clears when broker/data/feed recover" if active
                     else "Nominal — all systems healthy"),
        "force_wait": active,
        "preserved": ["learning", "memory", "logs", "DNA", "weights"],
    }


def incidents() -> list[dict]:
    return list(reversed(_incidents))[:20]
