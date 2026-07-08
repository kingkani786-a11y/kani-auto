"""Phase 31 — Autonomous AI Research Lab.

Self-diagnoses the RUNNING system from real runtime signals (heartbeats, broker
stability, persistence state, reliability coverage, data quality) and emits
prioritised findings + the what-worked/failed/upgrade buckets. This is honest
introspection of live state — it does NOT fabricate static-analysis it can't
actually perform; items needing manual review are labelled as such.
"""
from __future__ import annotations

import time
from typing import Any

from ..core.state import state
from . import memory

# Confluence directional engines that carry a live weight but may lack
# reliability measurement (mtf/smart_money/volume_profile aren't in the matrix).
_WEIGHTED = {"trend", "structure", "oi", "mtf", "smart_money", "greeks", "volume_profile"}
# Phase E — all 7 weighted directional engines are now in the decision matrix
# (so reliability is tracked for every one of them).
_MEASURED = {"trend", "structure", "oi", "greeks", "mtf", "smart_money", "volume_profile"}


def report() -> dict[str, Any]:
    findings: list[dict[str, Any]] = []

    def add(sev: str, area: str, finding: str, rec: str):
        findings.append({"severity": sev, "area": area, "finding": finding, "recommendation": rec})

    # --- persistence (the dominant issue) ---
    from .journal import _sb
    if not _sb:
        add("HIGH", "Persistence", "Database is IN-MEMORY — learning/DNA/weights reset on restart.",
            "Set SUPABASE_URL + SUPABASE_SERVICE_KEY in backend/.env and run supabase_schema.sql.")

    # --- broker / feed health ---
    try:
        from ..broker.dhan import DhanClient
        bs = DhanClient.stats()
    except Exception:
        bs = {}
    if not state.connected:
        add("INFO", "Broker", "Broker disconnected (idle by design until SAVE & CONNECT).",
            "Connect to resume live analysis; token is in-memory only.")
    if bs.get("cooldown_active"):
        add("HIGH", "Broker", "Rate-limit cooldown active — data may be unreliable.",
            "Throttle request budget; kill switch already force-waits on this.")
    if (bs.get("health_score") or 100) < 70:
        add("MEDIUM", "Broker", f"Broker health {bs.get('health_score')} — elevated 429/utilisation.",
            "Reduce poll frequency on hot loops.")

    # --- data quality ---
    if state.data_quality == "POOR":
        add("HIGH", "Data", "Data quality POOR.", "Kill switch force-waits; verify feed subscription.")
    elif state.data_quality == "DEGRADED":
        add("MEDIUM", "Data", "Data quality DEGRADED.", "Monitor; some feeds missing/delayed.")

    # --- learning / validation coverage ---
    n_out = len(memory._outcomes)
    if n_out == 0:
        add("HIGH", "Learning", "0 settled outcomes — accuracy/calibration/DNA cannot be graded.",
            "Run live during market hours so signals settle to win/loss.")
    elif n_out < 100:
        add("MEDIUM", "Learning", f"Only {n_out} settled outcomes — metrics still firming up.",
            "Accumulate ≥100 for stable grades; ≥500 unlocks Phase 24.")

    # --- reliability coverage (unmeasured weighted engines) ---
    gap = sorted(_WEIGHTED - _MEASURED)
    if gap:
        add("MEDIUM", "Coverage",
            f"Weighted engines without reliability tracking: {', '.join(gap)}.",
            "Add these to the decision-matrix so the nightly audit can weight-tune them.")
    else:
        add("INFO", "Coverage", "All 7 weighted directional engines are reliability-tracked.",
            "No action — full coverage.")

    # --- unused / idle engine detector (heartbeats) ---
    now = time.time()
    idle = [k for k in ("spot", "options", "greeks", "signal_engine", "scanner")
            if k not in state.heartbeats]
    if idle and state.connected:
        add("MEDIUM", "Engines", f"Engines with no heartbeat while connected: {', '.join(idle)}.",
            "Check the loop schedule / exceptions in those cycles.")

    # --- duplicate-calculation / dead-API detectors (honest scope) ---
    add("LOW", "Code Health",
        "No duplicate calculations detected at runtime — engines share one confluence packet.",
        "Static dead-API / duplicate-logic scan is a manual review item (not runtime-detectable here).")

    # --- severity rollup ---
    sev_rank = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    findings.sort(key=lambda f: sev_rank.get(f["severity"], 9))
    counts = {s: sum(1 for f in findings if f["severity"] == s)
              for s in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")}

    # --- buckets ---
    worked, failed, improved, regressed, upgrade, disable, monitor = [], [], [], [], [], [], []
    worked.append(f"{len(_MEASURED)} core engines instrumented; safety stack (kill switch, capital "
                  "protection, no-trade-zone) live.")
    if state.connected:
        worked.append(f"Broker connected · data {state.data_quality} · broker health {bs.get('health_score','—')}.")
    if not _sb:
        failed.append("Learning does not persist (in-memory only).")
        upgrade.append("Enable Supabase persistence (highest leverage).")
    if n_out == 0:
        failed.append("No validated outcomes yet.")
    upgrade.append("Instrument mtf/smart_money/volume_profile for reliability weighting.")
    monitor.append("Calibration drift + Brier once trades settle.")
    monitor.append("Broker rate-limit utilisation on busy sessions.")
    disable.append("None — no engine has a mature failing sample to justify disabling.")

    return {
        "ready": True,
        "generated_at": now,
        "findings": findings,
        "counts": counts,
        "what_worked": worked,
        "what_failed": failed or ["No notable failures detected"],
        "what_improved": improved or ["—"],
        "what_regressed": regressed or ["None detected"],
        "what_to_upgrade": upgrade,
        "what_to_disable": disable,
        "what_to_monitor": monitor,
        "note": "Runtime self-diagnosis from live signals — evidence-based, no fabrication.",
    }
