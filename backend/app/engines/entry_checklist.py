"""Phase 2 (Live Entry Checklist) + Phase 3 (Fire Score band) + Phase 8 (WHY-NOT).

Derivation-only: turns the EXISTING decision matrix into a per-confirmation
checklist (PASS / FAIL / WAITING + remaining distance), a 0–100 Entry Fire Score
band, and — when there's no trade — the exact reasons it's held. No new
indicators, no duplicated calculation. Answers "what is missing?" and
"why no trade?" directly. Capital protection / kill switch / safe mode override.
"""
from __future__ import annotations

from typing import Any

CONFIRM_LEVEL = 55.0   # matches the confluence engine's confirm threshold


def build(layers: dict[str, Any], signal: dict[str, Any], decision: dict[str, Any],
          kill_switch: dict | None = None, safe_mode: dict | None = None) -> dict[str, Any]:
    L = layers or {}
    rows = ((L.get("intelligence") or {}).get("decision_matrix") or {}).get("rows", [])
    # V15 instrument-aware: option-only layers are N/A (not pending) on
    # chain-less instruments — exclude them from the checklist and fire score.
    rows = [r for r in rows if r.get("verdict") != "N/A"]
    if not rows:
        return {"ready": False, "note": "No live analysis yet."}

    checklist = []
    for r in rows:
        score = float(r.get("score", 50))
        verdict = r.get("verdict")
        if verdict == "PASS":
            status = "PASS"; remaining = 0.0
        elif verdict == "FAIL":
            status = "FAIL"; remaining = round(CONFIRM_LEVEL - score, 0)
        else:
            status = "WAITING"; remaining = round(max(0.0, CONFIRM_LEVEL - score), 0)
        checklist.append({"item": r.get("layer"), "status": status,
                          "score": round(score, 0), "threshold": CONFIRM_LEVEL,
                          "remaining": remaining, "note": r.get("reason", "")})

    passed = sum(1 for c in checklist if c["status"] == "PASS")
    total = len(checklist)
    # Phase 3 — Entry Fire Score (confirmation ratio, quality-weighted)
    pass_quality = (sum(c["score"] for c in checklist if c["status"] == "PASS") / passed) if passed else 0
    fire_score = int(round((passed / total) * 70 + (pass_quality / 100) * 30)) if total else 0
    fire_band = ("BUY NOW" if fire_score >= 90 else "ARMED" if fire_score >= 80
                 else "PREPARE" if fire_score >= 61 else "WAIT")
    # RC1.16.10 fix #7: the checklist headline read "BUY NOW · 92/100" while
    # the Kill Switch was ACTIVE and the gate BLOCKED — the words override
    # the gate in the reader's mind even though the code never does. When a
    # protection override is active, the headline states confluence without
    # commanding action. Scores/logic unchanged.
    if fire_band in ("BUY NOW", "ARMED") and (
            (kill_switch and kill_switch.get("active"))
            or (safe_mode and safe_mode.get("active"))):
        fire_band = "CONFIRMED — GATE BLOCKED"

    # Phase 8 — WHY-NOT (reasons a trade is held), with overrides first
    is_trade = bool(decision.get("is_trade"))
    why_not: list[str] = []
    if kill_switch and kill_switch.get("active"):
        why_not += [f"Kill switch: {r}" for r in kill_switch.get("reasons", [])]
    if safe_mode and safe_mode.get("active"):
        why_not += [f"Safe mode: {t}" for t in safe_mode.get("triggers", [])]
    if not is_trade:
        for c in checklist:
            if c["status"] == "FAIL":
                why_not.append(f"{c['item']} failed ({c['note'] or 'against'})")
            elif c["status"] == "WAITING":
                why_not.append(f"{c['item']} not confirmed (needs +{c['remaining']:.0f})")
        vetoes = signal.get("vetoes") or signal.get("warnings") or []
        why_not += list(vetoes[:3])
        if not why_not:
            why_not = ["Confluence not yet aligned — waiting for confirmation"]

    waiting_for = [f"{c['item']} +{c['remaining']:.0f}" for c in checklist
                   if c["status"] in ("WAITING", "FAIL") and c["remaining"] > 0][:5]

    return {
        "ready": True,
        "checklist": checklist,
        "passed": passed, "total": total,
        "fire_score": fire_score, "fire_band": fire_band,
        "is_trade": is_trade,
        "waiting_for": waiting_for,
        "why_not": why_not if not is_trade or why_not else [],
        "note": "Institutional confirmation overrides indicators; quality over quantity; "
                "capital protection overrides every BUY.",
    }
