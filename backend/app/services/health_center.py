"""System Health Center — single composite health score (A+ … D).

Rolls the platform's real signals (data quality, broker, AI heartbeats, memory,
learning, DNA, audit, persistence) into per-component scores and one overall
grade. Derivation-only, evidence-based; honest "BUILDING" when data is thin.
"""
from __future__ import annotations

import time
from typing import Any

from ..core.state import state
from . import memory


def _grade(score: float) -> str:
    return ("A+" if score >= 90 else "A" if score >= 80 else "B" if score >= 68
            else "C" if score >= 55 else "D")


def score() -> dict[str, Any]:
    now = time.time()
    comps: dict[str, dict[str, Any]] = {}

    def add(name: str, val: float, detail: str):
        comps[name] = {"score": round(val, 0), "detail": detail}

    # data quality
    dq = state.data_quality
    add("data_quality", {"GOOD": 100, "DEGRADED": 60, "POOR": 20}.get(dq, 50),
        dq or "UNKNOWN")

    # broker
    try:
        from ..broker.dhan import DhanClient
        bs = DhanClient.stats()
    except Exception:
        bs = {}
    if not state.connected:
        add("broker", 50, "Disconnected (idle by design)")
    else:
        add("broker", float(bs.get("health_score") or 100),
            f"util {bs.get('utilization_pct',0)}% · {bs.get('rate_limit_events',0)} 429s")

    # AI engine freshness
    if not state.connected:
        add("ai_engine", 50, "Idle — not connected")
    else:
        sig = state.heartbeats.get("signal_engine")
        fresh = sig and (now - sig) < 420
        add("ai_engine", 100 if fresh else 50, "Fresh" if fresh else "Stale/starting")

    # memory
    add("memory", 100 if len(memory._ring) > 0 else 60,
        f"{len(memory._ring)} snapshots")

    # learning (settled outcomes)
    n = len(memory._outcomes)
    add("learning", min(100, 20 + n) if n else 20,
        f"{n} settled outcomes" + ("" if n >= 100 else " (building)"))

    # DNA
    dna = state.market_dna or {}
    add("dna", (float(dna.get("match_score") or 60) if dna.get("ready") else 30),
        dna.get("verdict", "Insufficient DNA"))

    # audit / calibration
    try:
        from . import analytics
        cal = (analytics.performance().get("calibration") or {}).get("calibration_score")
    except Exception:
        cal = None
    add("audit", float(cal) if cal is not None else 40,
        f"calibration {cal}" if cal is not None else "Building")

    # persistence
    from .journal import _sb
    add("persistence", 100 if _sb else 40, "Supabase" if _sb else "In-memory")

    overall = round(sum(c["score"] for c in comps.values()) / len(comps), 0)
    # honest BUILDING flag when learning has no validated data yet
    building = n == 0
    # V28 §10 — production readiness (infra/feed ready vs data-validated)
    try:
        from ..broker.dhan import DhanClient
        latency = (DhanClient.stats() or {}).get("avg_latency_ms")
    except Exception:
        latency = None
    infra_ready = (comps["data_quality"]["score"] >= 60 and comps["broker"]["score"] >= 60
                   and state.connected)
    prod_ready = bool(infra_ready and not building and _sb is not None and n >= 100)
    # §10 — honest certification status (never fake "LIVE READY")
    if prod_ready:
        cert = "LIVE READY"
    elif infra_ready:
        cert = "VALIDATION IN PROGRESS"
    else:
        cert = "NOT READY"
    production = {
        "execution_ready": bool(infra_ready),
        "production_ready": prod_ready,
        "certification": cert,
        "validated_trades": n,
        "feed_pct": comps["data_quality"]["score"],
        "latency_ms": latency,
        "blockers": [b for b in [
            (None if state.connected else "broker disconnected"),
            (None if _sb else "persistence (Supabase) not active"),
            (None if n >= 100 else f"validated trades {n}/100"),
        ] if b],
    }
    return {
        "components": comps,
        "overall_score": overall,
        "overall_grade": "BUILDING" if building else _grade(overall),
        "building": building,
        "production": production,
        "note": "Composite of live signals. BUILDING until trades settle; no fabricated accuracy.",
        "ts": now,
    }
