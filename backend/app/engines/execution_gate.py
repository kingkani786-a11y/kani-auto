"""Section 24 — Final Execution Gate (+ Section 1 control-center synthesis).

The last institutional checkpoint before a BUY CALL / BUY PUT. Evaluates every
mandatory condition from the outputs the platform ALREADY computes; if ANY hard
condition fails, the gate's verdict is NO TRADE with the exact blocking reason.
Derivation-only and ADVISORY-authoritative: it reports the gated verdict (used by
the Execution Control Center) without mutating the tested decision pipeline, so
nothing downstream regresses. Capital protection overrides opportunity.
"""
from __future__ import annotations

from typing import Any

# directional confluence layers that must confirm (live PASS/FAIL from matrix)
_CORE = ["Trend", "MTF", "OI", "Greeks", "Liquidity", "Institutional", "Structure"]


def _truncate(text: str, limit: int = 80) -> str:
    """Word-boundary truncation — the plain `text[:80]` this replaced cut mid-
    word with no ellipsis (e.g. 'forecasts mis-tuned' -> 'forecasts mis-tun',
    live-observed 2026-07-24), reading as broken/cut-off text rather than an
    intentionally shortened reason."""
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return (cut or text[:limit]) + "…"


def evaluate(layers: dict[str, Any], signal: dict[str, Any], decision: dict[str, Any],
             data_quality: str, kill_switch: dict | None, safe_mode: dict | None,
             market_dna: dict | None) -> dict[str, Any]:
    L = layers or {}
    rows = {r.get("layer"): r for r in
            ((L.get("intelligence") or {}).get("decision_matrix") or {}).get("rows", [])}
    cap = (L.get("capital_protection") or {})
    ks = kill_switch or {}
    sm = safe_mode or {}
    conds: list[dict[str, Any]] = []

    def add(name: str, status: str, reason: str):
        conds.append({"name": name, "status": status, "reason": reason})

    # ---- hard overrides first (capital protection > opportunity) ----
    if ks.get("active"):
        add("Kill Switch", "FAIL", _truncate("; ".join(ks.get("reasons", []))) or "active")
    else:
        add("Kill Switch", "PASS", "clear")
    if sm.get("active"):
        add("Safe Mode", "FAIL", _truncate("; ".join(sm.get("triggers", []))) or "active")
    else:
        add("Safe Mode", "PASS", "nominal")
    # data quality
    if data_quality == "POOR":
        add("Data Quality", "FAIL", "feed poor")
    elif data_quality in ("DEGRADED", "CLOSED", "UNKNOWN"):
        add("Data Quality", "WAITING", data_quality.lower())
    else:
        add("Data Quality", "PASS", "good")
    # risk acceptable
    cat = (cap.get("category") or "").upper()
    if cat in ("HIGH", "CRITICAL", "EXTREME", "DANGER"):
        add("Risk", "FAIL", f"capital risk {cat}")
    elif cat in ("MODERATE", "MEDIUM", "ELEVATED"):
        add("Risk", "WAITING", f"capital risk {cat}")
    else:
        add("Risk", "PASS", cat or "acceptable")

    # V15 instrument-aware: option-only conditions (matrix rows marked N/A on
    # instruments without an option chain) are excluded — not "WAITING" —
    # so the gate can actually arm on commodities from the applicable layers.
    no_chain = bool((L.get("_instrument_mode") or {}).get("excluded"))
    core = [l for l in _CORE if rows.get(l, {}).get("verdict") != "N/A"]
    min_core = 5 if not no_chain else max(len(core) - 1, 3)   # same ~71% bar

    # ---- core directional confirmations (from the live matrix) ----
    for layer in core:
        r = rows.get(layer)
        if not r:
            add(layer, "WAITING", "not evaluated")
            continue
        v = r.get("verdict")
        add(layer, "PASS" if v == "PASS" else "FAIL" if v == "FAIL" else "WAITING",
            r.get("reason", "") or v)

    # ---- supporting (data-dependent → WAITING when absent, never hard-block) ----
    dna = market_dna or {}
    add("Market DNA", "PASS" if (dna.get("ready") and (dna.get("match_score") or 0) >= 50)
        else "WAITING", dna.get("verdict", "building"))
    if not no_chain:   # premium forecast is strike-based — option instruments only
        pf = (decision.get("premium_forecast") or {})
        if pf.get("ready"):
            add("Premium", "FAIL" if pf.get("classification") == "AVOID" else "PASS",
                pf.get("classification", ""))
        else:
            add("Premium", "WAITING", "building")

    # ---- verdict ----
    fails = [c for c in conds if c["status"] == "FAIL"]
    waiting = [c for c in conds if c["status"] == "WAITING"]
    core_pass = sum(1 for layer in core if rows.get(layer, {}).get("verdict") == "PASS")
    direction = signal.get("direction") or "NEUTRAL"
    wants_trade = bool(decision.get("is_trade")) and direction in ("BULL", "BEAR")

    # V28 §1 — Trade Confidence Lock (production-grade bar; quality over quantity).
    di = decision.get("intelligence_synthesis") or {}
    ec = decision.get("entry_checklist") or {}
    trade_q = float((di.get("trade_quality") or {}).get("score") or 0)
    fire = float(ec.get("fire_score") or 0)
    conviction = float(di.get("conviction") or signal.get("dynamic_confidence") or 0)
    # institutional bar: matrix row for options; order-flow proxy (Liquidity
    # row) on chain-less instruments where Institutional is N/A
    _inst_row = rows.get("Institutional") if not no_chain else rows.get("Liquidity")
    inst_score = float((_inst_row or {}).get("score") or 0)
    quality_block = []
    if wants_trade and not fails:
        if conviction < 80: quality_block.append(f"Confidence {conviction:.0f} < 80")
        if fire < 85: quality_block.append(f"Fire score {fire:.0f} < 85")
        if trade_q < 800: quality_block.append(f"Trade quality {trade_q:.0f} < 800")
        if inst_score < 70: quality_block.append(
            f"{'Institutional' if not no_chain else 'Order flow'} {inst_score:.0f} < 70")
        if data_quality != "GOOD": quality_block.append(f"Data quality {data_quality} (need GOOD)")

    passed = (not fails) and (not quality_block) and core_pass >= min_core and wants_trade
    if fails:
        final = "NO TRADE"
    elif passed:
        final = "BUY CALL" if direction == "BULL" else "BUY PUT"
    else:
        final = "WAIT"

    blocking = [f"{c['name']}: {c['reason']}" for c in fails] + quality_block
    return {
        "ready": bool(rows),
        "gate_passed": passed,
        "final_decision": final,
        "conditions": conds,
        "passed_count": sum(1 for c in conds if c["status"] == "PASS"),
        "total": len(conds),
        "blocking_reasons": blocking,
        "waiting_on": [c["name"] for c in waiting],
        "note": "Final execution gate — any hard condition fails ⇒ NO TRADE. "
                "Capital protection overrides opportunity. Probabilities, not certainty.",
    }
