"""Decision Intelligence synthesis layer (additive, derivation-only).

Reads the layers/signal the platform ALREADY computed and derives higher-level
decision intelligence — Market Animal, Expansion/Runner, Decision Clarity,
Data Confidence, Failure Patterns, and a plain-language summary. It performs
NO new market fetch and NO heavy computation (simple arithmetic over existing
fields), so it adds negligible latency and never alters any engine output.
"""
from __future__ import annotations

from typing import Any


def _market_animal(atr_pct: float, momentum: float, adx: float,
                   events: list[str] | None = None, phases: list[str] | None = None) -> dict[str, Any]:
    """Classify the move's character (Animal Evolution Engine). Pure shape
    classification, not a signal. Adds Dragon/Wolf/Shark to the base four."""
    m = abs(momentum)
    events = events or []
    phases = phases or []
    inst = "INSTITUTIONAL_BUYING" in events or "INSTITUTIONAL_SELLING" in events
    sweep = any("LIQUIDITY_SWEEP" in e for e in events)

    if atr_pct > 1.0 and adx >= 30 and (inst or "GAMMA_SQUEEZE" in phases):
        animal, life, exp, conf = "Dragon", "Explosive (institutional)", "Extreme — institutional expansion", 82
    elif atr_pct > 0.9 and m > 0.4 and adx >= 28:
        animal, life, exp, conf = "Cheetah", "Very short (minutes)", "High — fast burst", 80
    elif sweep:
        animal, life, exp, conf = "Shark", "Short (predatory)", "Medium — liquidity hunting", 65
    elif adx >= 25 and m > 0.25:
        animal, life, exp, conf = "Wolf", "Medium (trend hunting)", "High — relentless trend", 74
    elif atr_pct > 0.7 and adx >= 25:
        animal, life, exp, conf = "Elephant", "Long (sustained)", "High — large grind", 75
    elif adx >= 20 and m > 0.1:
        animal, life, exp, conf = "Horse", "Medium (trending)", "Medium — steady run", 70
    else:
        animal, life, exp, conf = "Rabbit", "Short (quick hops)", "Low — small moves", 55
    return {"animal": animal, "confidence": conf, "lifespan": life, "expansion_potential": exp}


def _expansion(expected_move: float, atr: float, spot: float, momentum: float, adx: float) -> dict[str, Any]:
    em = expected_move or atr * 2
    em_pct = (em / spot * 100) if spot else 0
    if em_pct < 0.3:
        cls = "Small Move"
    elif em_pct < 0.6:
        cls = "Medium Move"
    elif em_pct < 1.0:
        cls = "Large Move"
    else:
        cls = "Explosive Runner"
    runner_prob = max(0, min(95, em_pct * 50 + abs(momentum) * 60 + max(adx - 20, 0) * 1.5))
    score = max(0, min(100, em_pct * 60 + max(adx - 15, 0) * 1.2))
    return {"expansion_score": round(score, 0), "class": cls,
            "expected_move": round(em, 1), "runner_probability": round(runner_prob, 0)}


def _decision_clarity(signal: dict, regime_score: float, dq_score: float) -> dict[str, Any]:
    spread = abs(float(signal.get("bull_score", 50)) - float(signal.get("bear_score", 50)))
    confirms = int(signal.get("confirmations_count", 0))
    conf = float(signal.get("dynamic_confidence") or signal.get("confidence") or 0)
    score = (0.35 * conf + 0.2 * min(spread * 2, 100) + 0.15 * min(confirms * 14, 100)
             + 0.15 * regime_score + 0.15 * dq_score)
    score = max(0, min(100, score))
    label = ("VERY CLEAR" if score >= 80 else "CLEAR" if score >= 65 else
             "MODERATE" if score >= 50 else "UNCLEAR" if score >= 35 else "AVOID")
    return {"score": round(score, 0), "label": label}


def _failure_patterns(layers: dict, signal: dict) -> list[str]:
    out: list[str] = []
    cp = layers.get("capital_protection", {})
    if cp.get("theta_risk", 0) >= 70:
        out.append("Theta risk")
    if cp.get("iv_crush_risk", 0) >= 70:
        out.append("IV-crush risk")
    if cp.get("reversal_risk", 0) >= 60:
        out.append("Reversal risk")
    of = layers.get("order_flow", {})
    if "LIQUIDITY_VACUUM" in of.get("events", []):
        out.append("Liquidity risk")
    if 45 <= float(of.get("score", 50)) <= 55:
        out.append("Participation failure")
    if layers.get("traps", {}).get("detected"):
        out.append("Trap probability")
    if "GAMMA_SQUEEZE" not in layers.get("regime", {}).get("phases", []) and \
            layers.get("regime", {}).get("regime") in ("LOW_MOMENTUM", "RANGE_BOUND"):
        out.append("Gamma exhaustion")
    return out[:5]


def _decision_matrix(layers: dict[str, Any], signal: dict[str, Any]) -> dict[str, Any]:
    """P1 — per-layer PASS/FAIL/NEUTRAL vs the dominant direction, each with a
    reason. Every verdict is explained (UI rule: no unexplained scores)."""
    dom = "BULL" if (signal.get("bull_score", 50) >= signal.get("bear_score", 50)) else "BEAR"
    key = "score_bull" if dom == "BULL" else "score_bear"

    def verdict(score: float) -> str:
        return "PASS" if score >= 55 else "FAIL" if score <= 45 else "NEUTRAL"

    # V15 instrument-aware: option-only layers show N/A (not WAITING) on
    # instruments without an option chain — they are excluded, not pending.
    no_chain = bool((layers.get("_instrument_mode") or {}).get("excluded"))

    rows: list[dict] = []
    def add(name: str, score: float, reason: str, na: bool = False):
        if na:
            # score stays neutral 50 so legacy consumers are unaffected;
            # the N/A verdict is what excludes the row from gating
            rows.append({"layer": name, "verdict": "N/A", "score": 50,
                         "reason": "No option chain for this instrument"})
        else:
            rows.append({"layer": name, "verdict": verdict(score), "score": round(score, 0), "reason": reason})

    add("Trend", float(layers.get("trend", {}).get(key, 50)),
        layers.get("trend", {}).get("trend", "—"))
    _st_l = layers.get("structure", {})
    _st_ev = _st_l.get("event")
    add("Structure", float(_st_l.get(key, 50)),
        (_st_ev if _st_ev and _st_ev != "NONE" else None)
        or _st_l.get("swing") or _st_l.get("state") or "holding structure")
    # Greeks reason: the skew note (the actual directional signal) when present;
    # bare ATM IV read like a data error in the gate's blocking reason
    _gk = layers.get("greeks", {})
    _gk_reason = ((_gk.get("notes") or [None])[0]
                  or f"ATM IV {_gk.get('atm_iv', '—')}")
    add("Greeks", float(_gk.get(key, 50)), _gk_reason, na=no_chain)
    add("OI", float(layers.get("oi", {}).get(key, 50)),
        f"PCR {layers.get('oi', {}).get('pcr', '—')}", na=no_chain)
    # Phase E — reliability coverage for the remaining weighted directional engines
    add("MTF", float(layers.get("mtf", {}).get(key, 50)),
        f"Alignment {layers.get('mtf', {}).get('alignment', '—')}")
    add("Smart Money", float(layers.get("smart_money", {}).get(key, 50)),
        (layers.get("smart_money", {}).get("activities") or ["—"])[0] if layers.get("smart_money", {}).get("activities") else "—",
        na=no_chain)
    add("Volume Profile", float(layers.get("volume_profile", {}).get(key, 50)),
        layers.get("volume_profile", {}).get("state", "—") or "—")
    fut = layers.get("futures", {})
    fut_score = 70 if fut.get("relation") == "CONFIRMS" else 30 if fut.get("relation") == "CONTRADICTS" else 50
    add("Futures", fut_score, fut.get("relation", "—").title() if fut.get("relation") else "—")
    inst = layers.get("institutional_activity", {})
    inst_score = 70 if inst.get("bias") == ("BULLISH" if dom == "BULL" else "BEARISH") else 30 if inst.get("bias") not in ("NEUTRAL", None) else 50
    add("Institutional", inst_score, inst.get("bias", "—"), na=no_chain)
    of = layers.get("order_flow", {})
    add("Liquidity", float(of.get("score", 50)) if dom == "BULL" else 100 - float(of.get("score", 50)),
        "Order flow " + ("buy" if float(of.get("score", 50)) > 50 else "sell") + "-side")
    risk = layers.get("risk", {}).get("risk_level", "")
    cap = layers.get("capital_protection", {}).get("category", "")
    risk_score = 70 if risk == "LOW" or cap == "SAFE" else 30 if risk == "HIGH" or cap in ("ELEVATED", "CRITICAL") else 50
    add("Risk", risk_score, f"{risk or cap or '—'}")

    passed = sum(1 for r in rows if r["verdict"] == "PASS")
    failed = sum(1 for r in rows if r["verdict"] == "FAIL")
    return {"direction": dom, "rows": rows, "passed": passed, "failed": failed,
            "total": sum(1 for r in rows if r["verdict"] != "N/A"),
            "decision": signal.get("signal", "WAIT")}


def _institutional_thoughts(layers: dict[str, Any]) -> dict[str, Any]:
    """P3 — what institutions are likely / not-yet doing, with confidence."""
    sm = layers.get("smart_money", {})
    acts = sm.get("activities", [])
    events = sm.get("events", [])
    fut = layers.get("futures", {})
    likely: list[dict] = []
    not_yet: list[dict] = []

    LABEL = {"PUT_WRITING": "Defending support (put writing)",
             "CALL_WRITING": "Capping upside (call writing)",
             "SHORT_COVERING": "Short covering", "LONG_BUILDUP": "Long build-up",
             "SHORT_BUILDUP": "Short build-up", "LONG_UNWINDING": "Long unwinding"}
    for a in acts:
        if a in LABEL:
            likely.append({"behaviour": LABEL[a], "confidence": 75})
    if "INSTITUTIONAL_BUYING" in events:
        likely.append({"behaviour": "Institutional buying prints", "confidence": 80})
    if "INSTITUTIONAL_SELLING" in events:
        likely.append({"behaviour": "Institutional selling prints", "confidence": 80})
    if fut.get("buildup") and fut["buildup"] != "Neutral":
        likely.append({"behaviour": f"Futures: {fut['buildup']}", "confidence": int(fut.get('confirmation_score') or 60)})

    # what's notably absent
    if "LONG_BUILDUP" not in acts and "INSTITUTIONAL_BUYING" not in events:
        not_yet.append("Aggressive long build-up")
    if "SHORT_BUILDUP" not in acts and "INSTITUTIONAL_SELLING" not in events:
        not_yet.append("Aggressive short build-up")
    return {"likely": likely[:4] or [{"behaviour": "No clear institutional footprint", "confidence": 40}],
            "not_yet": not_yet[:2]}


def analyze(layers: dict[str, Any], signal: dict[str, Any], spot: float,
            data_quality: str) -> dict[str, Any]:
    trend = layers.get("trend", {})
    tech_atr = float((signal.get("tech") or {}).get("atr") or 0)
    atr_pct = (tech_atr / spot * 100) if spot else 0
    momentum = float((signal.get("tech") or {}).get("momentum") or 0)
    adx = float(trend.get("adx") or 0)
    prob = layers.get("probability", {})
    regime_score = float(layers.get("regime", {}).get("score") or 50)
    dq_score = {"GOOD": 95, "DEGRADED": 60, "POOR": 25, "UNKNOWN": 50}.get(data_quality, 50)

    sm_events = (layers.get("smart_money", {}) or {}).get("events", [])
    phases = (layers.get("regime", {}) or {}).get("phases", [])
    animal = _market_animal(atr_pct, momentum, adx, sm_events, phases)
    expansion = _expansion(float(prob.get("expected_move") or 0), tech_atr, spot, momentum, adx)
    # Animal V3 — next evolution (what this move could become) + probability
    NEXT = {"Rabbit": "Horse", "Horse": "Wolf", "Wolf": "Cheetah", "Elephant": "Dragon",
            "Cheetah": "Dragon", "Shark": "Wolf", "Dragon": "Exhaustion"}
    animal["next_evolution"] = NEXT.get(animal["animal"], "—")
    animal["next_evolution_prob"] = int(max(10, min(85, expansion["runner_probability"] * 0.8)))
    clarity = _decision_clarity(signal, regime_score, dq_score)
    data_conf = "High" if dq_score >= 85 else "Medium" if dq_score >= 55 else "Low"
    failures = _failure_patterns(layers, signal)

    # plain-language answers to the Final Decision Panel's six questions
    is_trade = signal.get("signal") not in (None, "NO TRADE")
    bias = layers.get("global_context", {}).get("bias", "NEUTRAL")
    summary = {
        "whats_happening": f"{layers.get('regime', {}).get('regime', '—').replace('_', ' ').title()} · {bias.title()}",
        "move_type": f"{animal['animal']} ({animal['expansion_potential']})",
        "entry_ready": "Yes" if is_trade else "No — waiting",
        "how_far": f"{expansion['class']} · runner {expansion['runner_probability']:.0f}%",
        "what_fails": ", ".join(failures) if failures else "No major failure pattern",
        "clarity": clarity["label"],
    }
    return {
        "market_animal": animal,
        "expansion": expansion,
        "decision_clarity": clarity,
        "data_confidence": data_conf,
        "failure_patterns": failures,
        "summary": summary,
        "decision_matrix": _decision_matrix(layers, signal),
        "institutional_thoughts": _institutional_thoughts(layers),
    }
