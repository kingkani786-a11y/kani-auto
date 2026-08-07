"""Cloud AI Trader X — Confluence Engine.

Orchestrates the decision layers and applies the FINAL RULE:
  * never a signal from a single indicator,
  * mandatory layers must all confirm the same direction,
  * unclear conditions return NO TRADE with explicit vetoes,
  * quality over quantity.

SEVEN layers carry weight in the composite:
  trend .16 | structure .16 | oi .16 | mtf .16 | smart .12 | greeks .12 | vp .12
Regime acts as a quality multiplier; probability is derived from the edge;
risk qualifies the final output.

(This said "all ten layers" until the 2026-08-07 architecture audit counted
the literal WEIGHTS dict and found seven. The extra entries in `layers{}` —
candles, supertrend, evidence_rank, structural_targets, expiry, market_profile
and the rest — are OBSERVATIONAL or veto-only, deliberately outside the score.
The distinction matters: anyone designing against "ten weighted layers" would
be designing against a system that does not exist.)
"""
from __future__ import annotations

import time
from typing import Any

from ..config import settings
from ..core.text import truncate_at_word
from . import (
    candles as candle_eng, early_warning, evidence_rank, expiry as expiry_eng,
    market_profile, mtf, narrator, orderflow, probability, quality, regime,
    risk, smart_money, strike_selector, structure, supertrend as supertrend_eng,
    support_resistance, technicals, volume_profile,
)

# per-symbol context from the previous cycle (for phase detection deltas)
_prev_ctx: dict[str, dict] = {}

WEIGHTS = {
    "trend": 0.16, "structure": 0.16, "oi": 0.16, "mtf": 0.16,
    "smart_money": 0.12, "greeks": 0.12, "volume_profile": 0.12,
}
MANDATORY = ("trend", "structure", "mtf", "oi")
MIN_CONFIRMING_LAYERS = 5     # of the 7 directional layers
# option-chain-derived layers — permanently neutral on non-INDEX instruments
OPTION_ONLY_LAYERS = ("oi", "greeks", "smart_money")
CONFIRM_LEVEL = 55.0

# Adaptive Threshold Engine: the confirmation bar moves with the regime —
# easy tape earns a slightly lower bar, hostile tape demands much more.
REGIME_THRESHOLD_ADJ = {
    "HIGH_MOMENTUM": -3.0,
    "TRENDING": -2.0,
    "RANGE_BOUND": +5.0,
    "VOLATILE": +8.0,
    "LOW_MOMENTUM": +8.0,
    "EXPIRY_PINNING": +12.0,
}


def adaptive_threshold(base: float, regime_name: str, accuracy: float | None) -> tuple[float, str]:
    adj = REGIME_THRESHOLD_ADJ.get(regime_name, 0.0)
    why = f"{regime_name.replace('_', ' ').title()} regime {'lowers' if adj < 0 else 'raises'} the bar by {abs(adj):.0f}"
    # learning loop: poor historical accuracy in this regime raises the bar further
    if accuracy is not None and accuracy < 50:
        adj += 5.0
        why += "; weak historical accuracy adds +5"
    elif accuracy is not None and accuracy > 70:
        adj -= 2.0
        why += "; strong historical accuracy gives -2"
    return max(55.0, min(85.0, base + adj)), why


def _oi_layer(analytics: dict, flow: dict, market_type: str) -> dict:
    """Layer 3 — option-chain positioning condensed to a directional score."""
    notes: list[str] = []
    if not (analytics or {}).get("chain"):
        # no option chain in the data (chain-less contract or feed not
        # subscribed): use underlying build-up classification
        u = flow.get("underlying", "NEUTRAL")
        bull = 65.0 if u in ("LONG_BUILDUP", "SHORT_COVERING") else 35.0 if u in ("SHORT_BUILDUP", "LONG_UNWINDING") else 50.0
        if u != "NEUTRAL":
            notes.append(f"Futures OI shows {u.replace('_', ' ').title()}")
        return {"direction": "BULL" if bull > 55 else "BEAR" if bull < 45 else "NEUTRAL",
                "score_bull": bull, "score_bear": 100 - bull,
                "pcr": None, "max_pain": None, "notes": notes}

    score = flow.get("score", 0)
    bull = max(0.0, min(100.0, 50 + score * 11))
    pcr = analytics.get("pcr", 1.0)
    if "PUT_WRITING" in flow.get("activities", []):
        notes.append("Strong put writing — support being defended")
    if "CALL_WRITING" in flow.get("activities", []):
        notes.append("Call writing — upside being capped")
    if pcr and pcr > 1.15:
        notes.append(f"PCR {pcr:.2f} leans bullish")
    elif pcr and pcr < 0.85:
        notes.append(f"PCR {pcr:.2f} leans bearish")
    bear = 100 - bull
    return {"direction": "BULL" if bull - bear >= 10 else "BEAR" if bear - bull >= 10 else "NEUTRAL",
            "score_bull": round(bull, 1), "score_bear": round(bear, 1),
            "pcr": pcr, "max_pain": analytics.get("max_pain"), "notes": notes}


def _greeks_layer(analytics: dict) -> dict:
    g = (analytics or {}).get("greeks", {})
    ce_d = abs(float(g.get("ce", {}).get("delta") or 0.5))
    pe_d = abs(float(g.get("pe", {}).get("delta") or 0.5))
    skew = ce_d - pe_d
    bull = max(0.0, min(100.0, 50 + skew * 250))
    iv = float(g.get("ce", {}).get("iv") or 0)
    notes: list[str] = []
    # Data-sanity guard: an ATM IV under 3% on an index is a stale/settled-premium
    # artifact (seen after-hours: "ATM IV 1.3"). Garbage IV must not hard-FAIL or
    # hard-PASS the gate — neutralise the layer and say why.
    if iv and iv * 100 < 3.0:
        return {"direction": "NEUTRAL", "score_bull": 50.0, "score_bear": 50.0,
                "atm_iv": round(iv * 100, 1),
                "notes": ["ATM IV implausible (<3%) — stale-premium artifact; greeks neutralised"]}
    if skew > 0.04:
        notes.append("Positive delta skew — options pricing upside")
    elif skew < -0.04:
        notes.append("Negative delta skew — options pricing downside")
    return {"direction": "BULL" if bull >= 60 else "BEAR" if bull <= 40 else "NEUTRAL",
            "score_bull": round(bull, 1), "score_bear": round(100 - bull, 1),
            "atm_iv": round(iv * 100, 1) if iv else None, "notes": notes}


def run(
    spot: float,
    market_type: str,
    candles_1m: list[dict],
    analytics: dict,
    flow: dict,
    data_quality: str,
    threshold: float | None = None,
    symbol: str = "",
    historical_accuracy: float | None = None,
    levels: dict[str, Any] | None = None,
    breadth: dict[str, Any] | None = None,
    kill_switch: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Full Cloud AI Trader X analysis cycle. Returns the intelligence packet."""
    threshold = threshold if threshold is not None else settings.confidence_threshold
    c5 = mtf.resample(candles_1m, 5)
    atr_v = technicals.atr(c5)
    closes5 = [c["close"] for c in c5]
    vwap_v = technicals.vwap(candles_1m[-240:])
    mom = technicals.momentum(closes5)

    layers: dict[str, Any] = {}
    layers["trend"] = technicals.trend_engine(c5, vwap_v)
    layers["structure"] = structure.analyze(c5, atr_v)
    layers["oi"] = _oi_layer(analytics, flow, market_type)
    layers["smart_money"] = {**smart_money.analyze_tape(c5, layers["structure"]),
                             "flow": flow.get("activities", []),
                             "trap_zones": (layers["structure"].get("liquidity_above") or [])
                             + (layers["structure"].get("liquidity_below") or [])}
    # V24 Universal Strike Engine — option intelligence keys off CHAIN
    # PRESENCE, not market type: an MCX contract with a live option chain is
    # treated exactly like an index; a chain-less one keeps the honest N/A path.
    has_chain = bool((analytics or {}).get("chain"))
    layers["greeks"] = _greeks_layer(analytics)
    layers["volume_profile"] = volume_profile.analyze(c5[-80:])
    layers["mtf"] = mtf.analyze(candles_1m)
    layers["expiry"] = expiry_eng.analyze(symbol, analytics, spot) if has_chain else {"notes": [], "events": []}
    layers["market_profile"] = market_profile.analyze(candles_1m, layers["volume_profile"])
    layers["regime"] = regime.analyze(
        adx_v=layers["trend"].get("adx", 0), atr_pct=(atr_v / spot * 100) if spot else 0,
        momentum_pct=mom, alignment=layers["mtf"]["alignment"],
        expiry=(analytics or {}).get("expiry"), spot=spot,
        max_pain=(analytics or {}).get("max_pain"),
    )

    # ---- weighted composites ----
    # Phase 22 — apply human-APPROVED engine-weight multipliers (default 1.0 =
    # identical to the equal-weighted gate). Re-normalised so the confidence
    # scale is preserved. Wrapped so it can never break the signal.
    eff = dict(WEIGHTS)
    try:
        from ..services import weight_approval
        mult = weight_approval.effective_multipliers()
        if mult:
            eff = {k: WEIGHTS[k] * mult.get(k, 1.0) for k in WEIGHTS}
            tot = sum(eff.values()) or 1.0
            base_tot = sum(WEIGHTS.values())
            eff = {k: v / tot * base_tot for k, v in eff.items()}
    except Exception:
        eff = dict(WEIGHTS)

    # V15 Instrument-Aware Engine: non-INDEX instruments have no option chain,
    # so option-derived layers (oi/greeks/smart_money) sit at neutral 50
    # forever — scoring them dilutes, and gating on them structurally blocks,
    # every commodity trade. Score and gate only the applicable layers, at the
    # same ~71% confirmation ratio. All other vetoes/calibration unchanged.
    if has_chain:
        applicable = list(WEIGHTS)
        mandatory_eff = MANDATORY
        min_confirm = MIN_CONFIRMING_LAYERS
    else:
        applicable = [k for k in WEIGHTS if k not in OPTION_ONLY_LAYERS]
        mandatory_eff = tuple(m for m in MANDATORY if m not in OPTION_ONLY_LAYERS)
        min_confirm = 3        # of the 4 applicable — same bar as 5-of-7
        tot_a = sum(eff[k] for k in applicable) or 1.0
        eff = {k: (eff[k] / tot_a if k in applicable else 0.0) for k in WEIGHTS}
    layers["_instrument_mode"] = {
        "market_type": market_type, "applicable": applicable, "has_chain": has_chain,
        "excluded": [] if has_chain else list(OPTION_ONLY_LAYERS),
    }

    bull = sum(layers[k]["score_bull"] * eff[k] for k in WEIGHTS)
    bear = sum(layers[k]["score_bear"] * eff[k] for k in WEIGHTS)
    rq = layers["regime"]["score"] / 100.0
    quality_mult = 0.6 + 0.5 * rq             # 0.6x in chop … 1.1x in strong trend
    bull_adj, bear_adj = bull * quality_mult, bear * quality_mult
    win_dir = "BULL" if bull_adj >= bear_adj else "BEAR"
    win, lose = max(bull_adj, bear_adj), min(bull_adj, bear_adj)

    layers["probability"] = probability.analyze(
        win, lose, layers["regime"]["score"], spot,
        iv=float((analytics or {}).get("greeks", {}).get("ce", {}).get("iv") or 0),
        expiry=(analytics or {}).get("expiry"), atr_v=atr_v,
    )
    layers["probability"]["historical_accuracy"] = historical_accuracy

    # ---- V7.5: order flow + advanced regime phases (informational layers) ----
    layers["order_flow"] = orderflow.analyze(c5)
    # V7.1 Trade Explorer Phase 1 — Candle Pattern layer (owner, 2026-08-04).
    # OBSERVATIONAL ONLY: it is NOT in WEIGHTS, not in `applicable`, not in
    # `mandatory_eff`, and never appended to `vetoes` — so it cannot move the
    # composite, flip a confirmation count, or open/close the gate. It exists
    # so "what did the candles actually do" is a first-class, visible piece of
    # evidence instead of being implicit inside a blended score. Levels are
    # passed in so a pattern is reported AT a level when it is, per the spec's
    # "pattern + context" rule. Wrapped: a display layer must never be able to
    # break the decision path.
    try:
        _sr = layers["structure"]
        layers["candles"] = candle_eng.analyze(c5, atr=atr_v, levels={
            "support": (_sr.get("liquidity_below") or [None])[0],
            "resistance": (_sr.get("liquidity_above") or [None])[0],
            "vwap": vwap_v,
        })
    except Exception:
        layers["candles"] = {"ready": False, "patterns": [], "count": 0,
                             "bias": "NONE", "summary": "unavailable"}
    # Supertrend layer (owner, 2026-08-07) — the one absent evidence layer the
    # Master Architecture Audit found that was buildable from data already in
    # hand. OBSERVATIONAL ONLY, identical contract to the candles block above:
    # NOT in WEIGHTS, not in `applicable`, not in `mandatory_eff`, never
    # appended to `vetoes`. It cannot move the composite, flip a confirmation
    # count, or open/close the gate. It exists because the existing `trend`
    # layer is entirely level-based (EMA stack/VWAP/ADX) and structurally
    # cannot express a stateful trend ratchet — the two genuinely disagree at
    # turns, and that disagreement is information worth SEEING rather than
    # blending away. Promotion into the composite needs its own evidence and
    # its own approval. Wrapped: a display layer must never break the decision.
    try:
        layers["supertrend"] = supertrend_eng.analyze(c5)
    except Exception:
        layers["supertrend"] = {"ready": False, "direction": "NONE",
                                "supertrend": None, "summary": "unavailable"}
    iv_now = float((analytics or {}).get("greeks", {}).get("ce", {}).get("iv") or 0)
    prev = _prev_ctx.get(symbol, {})
    layers["regime"]["phases"] = regime.phases(
        c5, flow, iv_now, prev.get("iv", 0.0),
        layers["trend"].get("adx", 0), atr_v, prev.get("atr", 0.0))
    _prev_ctx[symbol] = {"iv": iv_now, "atr": atr_v}

    # ---- Probability Lab (M5): EV / drawdown / reward in points ----
    atr_eff = max(atr_v, spot * 0.0015)
    pos_frac = layers["probability"]["prob_success"] / 100.0
    layers["probability"].update({
        "expected_reward": round(2.5 * atr_eff, 2),
        "expected_drawdown": round(1.2 * atr_eff, 2),
        "expected_value": round(pos_frac * 2.5 * atr_eff - (1 - pos_frac) * 1.2 * atr_eff, 2),
        "regime_accuracy": historical_accuracy,
    })

    # expiry-day hostility feeds the gate
    if "EXPIRY_SQUEEZE_RISK" in layers["expiry"].get("events", []):
        layers["regime"]["score"] = min(layers["regime"]["score"], 45)

    # ---- V11 institutional context layers (additive, graceful) ----
    from . import global_context as gctx, institutional_scores as iscore, market_context
    layers["_tech"] = {"momentum": mom}
    is_expiry = (layers["expiry"].get("days_to_expiry") == 0) if has_chain else False
    v11_session = market_context.session_now(market_type, is_expiry)
    v11_vix = gctx.vix_correlation(layers["trend"].get("trend", "NEUTRAL"),
                                   market_context.get_vix(), layers["trend"].get("adx", 0))
    v11_gift = gctx.gift_correlation(market_context.get_gift(), win_dir)
    layers["session"] = v11_session
    layers["vix_correlation"] = v11_vix
    layers["gift_correlation"] = v11_gift
    layers["global_context"] = gctx.global_context(v11_vix, v11_gift, win_dir, layers["regime"]["regime"])
    layers["market_strength"] = iscore.market_strength(layers, breadth)
    v11_entry = iscore.entry_probability(layers, v11_vix, v11_gift, historical_accuracy, v11_session)
    layers["entry_probability"] = v11_entry
    layers["institutional_activity"] = iscore.institutional_activity(layers, analytics or {})
    layers["institutional_levels"] = levels or {}

    # ---- V13 protective layers ----
    from . import capital_protection, guards
    layers["capital_protection"] = capital_protection.assess(layers, market_type, spot)
    layers["no_trade_zone"] = guards.no_trade_zone(layers, spot)
    layers["traps"] = guards.traps(layers, spot)

    # ---- adaptive threshold (replaces the static bar) ----
    threshold, threshold_why = adaptive_threshold(
        threshold, layers["regime"]["regime"], historical_accuracy)

    # ---- Dynamic Confidence Engine: composed, each component displayed ----
    dq_score = {"GOOD": 95.0, "DEGRADED": 60.0, "UNKNOWN": 50.0, "POOR": 20.0}.get(data_quality, 50.0)
    components = {
        "signal_strength": round(win, 1),
        "market_alignment": round(layers["mtf"]["alignment"], 1),
        "historical_accuracy": round(historical_accuracy, 1) if historical_accuracy is not None else None,
        "data_quality": dq_score,
        "risk_environment": round(layers["regime"]["score"], 1),
    }
    dyn_conf = (0.40 * win + 0.20 * layers["mtf"]["alignment"]
                + 0.15 * (historical_accuracy if historical_accuracy is not None else 55.0)
                + 0.10 * dq_score + 0.15 * layers["regime"]["score"])
    # OWNER-LOCKED: global feed is CONTEXT ONLY — ±3 on confidence, listed as a
    # component, never a veto, never overrides Trend (docs/PROPOSALS.md)
    try:
        from ..services.global_feed import snapshot as _gsnap
        _g = _gsnap()
        if _g.get("available") and _g.get("adjust"):
            dyn_conf += float(_g["adjust"])
            components["global_context_adj"] = float(_g["adjust"])
            layers["global_feed"] = {"risk_state": _g["risk_state"],
                                     "adjust": _g["adjust"], "reasons": _g["reasons"]}
    except Exception:
        pass
    dyn_conf = round(max(0.0, min(100.0, dyn_conf)), 1)

    # ---- Engine 10: AI Confidence Calibration — a hard FORCE-WAIT gate.
    # A tradable signal cannot appear unless ALL five calibration checks pass.
    score_key = "score_bull" if win_dir == "BULL" else "score_bear"
    inst_conf = float((layers.get("oi", {}) or {}).get(score_key, 50)) if has_chain \
        else float((layers.get("order_flow", {}) or {}).get("score", 50))
    # OBS-11 fix (owner, 2026-08-05) — on chain-less instruments this reads
    # orderflow.py's genuine proxy score, whose own <30-candle guard returns
    # the same 50 a real quiet-market computation can also produce. Without
    # this flag "institutional 50" was ambiguous between "insufficient data"
    # and "computed, neutral". Display-only: value/min/pass are unchanged.
    inst_low_data = (not has_chain) and bool(
        (layers.get("order_flow", {}) or {}).get("low_data"))
    calibration = {
        "data_quality": {"value": round(dq_score, 0), "min": 90, "pass": dq_score > 90},
        "signal_confidence": {"value": round(win, 0), "min": 70, "pass": win > 70},
        "institutional": {"value": round(inst_conf, 0), "min": 60, "pass": inst_conf > 60,
                          "low_data": inst_low_data},
        "market_alignment": {"value": round(layers["mtf"]["alignment"], 0), "min": 60,
                             "pass": layers["mtf"]["alignment"] > 60},
        "risk_environment": {"value": round(layers["regime"]["score"], 0), "min": 60,
                             "pass": layers["regime"]["score"] > 60},
    }
    calibration_failed = [k for k, v in calibration.items() if not v["pass"]]
    calibration["passed"] = not calibration_failed
    calibration["force_wait"] = bool(calibration_failed)

    # ---- mandatory-confirmation gate ----
    vetoes: list[str] = []
    confirmations: list[str] = []
    # Phase 14 — Kill Switch overrides everything (capital protection first)
    if kill_switch and kill_switch.get("active"):
        vetoes.append("KILL SWITCH (FORCE WAIT): "
                       + truncate_at_word("; ".join(kill_switch.get("reasons", [])), 160))

    for name in applicable:
        s = layers[name][score_key]
        if s >= CONFIRM_LEVEL:
            confirmations.append(name)
        elif name in mandatory_eff:
            vetoes.append(f"mandatory layer '{name}' not confirming ({s:.0f} < {CONFIRM_LEVEL:.0f})")

    if len(confirmations) < min_confirm:
        vetoes.append(f"only {len(confirmations)}/{len(applicable)} applicable layers confirm (need {min_confirm})")
    if win < threshold:
        vetoes.append(f"composite {win:.0f} below threshold {threshold:.0f}")
    if win - lose < 12:
        vetoes.append("bull/bear scores too close — direction unclear")
    if layers["regime"]["score"] < 40:
        vetoes.append(f"hostile regime: {layers['regime']['regime'].replace('_', ' ').lower()}")
    if layers["probability"]["prob_success"] < 60:
        vetoes.append(f"probability of success {layers['probability']['prob_success']}% too low")
    if data_quality == "POOR":
        vetoes.append("data quality poor — refusing to signal on bad data")

    # ---- Advanced Safety Engine (M12): hard capital-preservation blocks ----
    atr_pct_now = (atr_v / spot * 100) if spot else 0.0
    if atr_pct_now > 1.5:
        vetoes.append(f"SAFETY: extreme volatility ({atr_pct_now:.2f}% ATR) — stand down")
    if dyn_conf < 60:
        vetoes.append(f"SAFETY: dynamic confidence {dyn_conf}% below the 60% floor")
    if "LIQUIDITY_VACUUM" in layers["order_flow"].get("events", []):
        vetoes.append("SAFETY: liquidity vacuum detected — fills would be unreliable")
    # ---- V11 multi-engine validation: India VIX + institutional entry score ----
    if v11_vix.get("available") and v11_vix["volatility_risk"] > 88:
        vetoes.append(f"SAFETY: India VIX risk extreme ({v11_vix['vix']}) — stand down")
    if v11_entry["band"] in ("AVOID", "WAIT"):
        vetoes.append(f"institutional entry score {v11_entry['score']:.0f}/100 "
                      f"({v11_entry['band']}) — below tradable threshold")
    # ---- V13 protective vetoes (capital preservation first) ----
    if layers["capital_protection"]["category"] == "CRITICAL":
        vetoes.append(f"SAFETY: capital risk CRITICAL ({layers['capital_protection']['capital_risk']:.0f}) "
                      "— no new trades")
    if layers["no_trade_zone"]["active"]:
        vetoes.append(f"NO TRADE ZONE: {layers['no_trade_zone']['reason']}")
    if layers["traps"]["detected"] and layers["traps"]["trap_confidence"] >= 55:
        vetoes.append(f"TRAP RISK: {layers['traps']['summary']} ({layers['traps']['trap_confidence']:.0f}%)")
    # Engine 10 signal gate: FORCE WAIT if any of the 5 declared thresholds
    # fail. Owner Step 8 (Remove Fake Metrics, 2026-07-26): this string used
    # to say "CALIBRATION", colliding with the unrelated, REAL outcome-based
    # calibration_score (services/analytics.py, shown in Calibration Watch)
    # — renamed here to avoid implying this declared-threshold gate is that
    # validated calibration. The dict key ("calibration") is left as-is to
    # avoid a wider payload-shape change; only user-facing text changed.
    if calibration_failed:
        names = {"data_quality": "data quality", "signal_confidence": "confidence",
                 "institutional": "institutional confirmation", "market_alignment": "market alignment",
                 "risk_environment": "risk environment"}
        vetoes.append("SIGNAL GATE (FORCE WAIT): " + ", ".join(names[k] for k in calibration_failed)
                      + " below required")

    # ---- trade levels (geometry chosen so T1 itself clears 1:2, V10) ----
    atr_eff = max(atr_v, spot * 0.0015)
    SL_MULT, T_MULTS = 1.0, (2.0, 3.0, 4.5)
    if win_dir == "BULL":
        sl = spot - SL_MULT * atr_eff
        targets = [spot + r * atr_eff for r in T_MULTS]
    else:
        sl = spot + SL_MULT * atr_eff
        targets = [spot - r * atr_eff for r in T_MULTS]
    risk_pts = abs(spot - sl)
    rr_t1 = abs(targets[0] - spot) / risk_pts if risk_pts else 0.0

    # ---- Risk-Reward filter (V10): first target must clear 1:2 ----
    # round to the displayed precision first: rr_t1 of 1.9999 printed as
    # "2.00:1 — below the 1:2 minimum" (float artifact, owner-spotted 07-17);
    # a ratio that DISPLAYS as 2.00 meets the minimum.
    if round(rr_t1, 2) < 2.0:
        vetoes.append(f"reward:risk to T1 only {rr_t1:.2f}:1 — below the 1:2 minimum")
    # ---- strict entry completeness: every level must be present & sane ----
    levels_ok = all(x > 0 for x in (spot, abs(sl), *targets)) and risk_pts > 0
    if not levels_ok:
        vetoes.append("incomplete trade levels — signal blocked")

    # V7.1 Trade Explorer Phase 2 — Evidence Ranking + Contradiction
    # (owner, 2026-08-04). Classifies the SAME layer scores already used above
    # into PRIMARY / CONFIRMING / CONTRADICTORY / INSUFFICIENT, so the trader
    # can see WHICH layer is driving the read rather than only a blended
    # number. Computes no new score and changes none: remove this block and
    # the decision is byte-identical. Runs on BOTH branches (blocked and
    # tradable) because "why this direction" matters most when the trade is
    # refused. Wrapped — an explainer must never break the decision path.
    try:
        layers["evidence_rank"] = evidence_rank.analyze(
            layers, win_dir, layers.get("candles"))
    except Exception:
        layers["evidence_rank"] = {"ready": False, "primary": None,
                                   "confirming": [], "contradicting": [],
                                   "insufficient": [], "conclusion": ""}

    # V7.1 Trade Explorer Phase 3A — Structural targets (owner, 2026-08-04).
    # MEASUREMENT ONLY. `targets`, SL_MULT, T_MULTS and the reward:risk veto
    # above are untouched — this records where the real touch/bounce-scored
    # S/R levels sit so the two can be compared on live data BEFORE anyone
    # proposes changing the tradable targets. That is Phase 3B and it needs
    # its own approval, because the R:R veto reads `targets` directly:
    # moving T1 would change WHICH TRADES ARE BLOCKED (a Trading Doctrine
    # change, not a display change).
    # Fed candles_1m — the SAME series exit_intelligence.py gives this engine
    # — so there is exactly one S/R source of truth, never a second
    # disagreeing one. Wrapped: a measurement layer must never be able to
    # break the decision path.
    try:
        layers["structural_targets"] = support_resistance.structural_targets(
            candles_1m, spot, win_dir, atr_targets=targets)
    except Exception:
        layers["structural_targets"] = {"available": False, "targets": [],
                                        "comparison": [],
                                        "reason": "unavailable"}

    tech_block = {
        "trend": layers["trend"]["trend"], "vwap": vwap_v, "atr": atr_v,
        "adx": layers["trend"].get("adx", 0), "momentum": mom,
        "volume_expansion": "INSTITUTIONAL_BUYING" in layers["smart_money"]["events"]
        or "INSTITUTIONAL_SELLING" in layers["smart_money"]["events"],
        "ema20": layers["trend"].get("ema20"), "ema50": layers["trend"].get("ema50"),
        "ema200": layers["trend"].get("ema200"),
    }

    if vetoes:
        signal: dict[str, Any] = {
            "signal": "NO TRADE",
            "direction": "NONE",
            "confidence": round(win, 1),
            "dynamic_confidence": dyn_conf,
            "confidence_components": components,
            "effective_threshold": round(threshold, 1),
            "threshold_reason": threshold_why,
            "calibration": calibration,
            "bull_score": round(bull_adj, 1),
            "bear_score": round(bear_adj, 1),
            "confirmations": confirmations,
            "confirmations_count": len(confirmations),
            "vetoes": vetoes,
            "reasons": [f"NO TRADE — {v}" for v in vetoes[:4]],
            "tech": tech_block,
        }
        # ---- V7.1 Signal <-> Execution separation (owner, 2026-08-04) ----
        # THE PROBLEM THIS SOLVES: above, `direction` is forced to "NONE" the
        # moment any veto fires, so a directional read the engine genuinely
        # HAD is erased before anything downstream can see it. The dashboard
        # then shows a bare "NO TRADE", which reads to a trader as "the system
        # found nothing" — when the truth is "the system found something and
        # execution was blocked". Those are completely different facts and the
        # 2026-08-04 session showed the cost of conflating them: the radar was
        # flagging Runner-90 BUY CANDIDATEs all day while the Hero read NO TRADE.
        #
        # `signal_candidate` records what the engine WOULD have called, exactly
        # as the non-veto branch below computes it, alongside why execution was
        # refused. It is additive metadata ONLY:
        #   * `signal` stays "NO TRADE" and `direction` stays "NONE" — every
        #     existing consumer (execution_gate, decision build, track_signal,
        #     every panel) sees byte-identical behaviour to V7.0.
        #   * NO threshold, veto, gate or scoring rule is changed. Nothing here
        #     can make a blocked trade tradable. Capital protection is untouched.
        # It exists so the UI can render SIGNAL / EXECUTION / REASON as three
        # separate lines instead of collapsing them into one misleading word.
        _cand_name = ("BUY CE" if win_dir == "BULL" else "BUY PE") \
            if (market_type == "INDEX" or has_chain) else (
                ("BUY STOCK" if win_dir == "BULL" else "SELL STOCK")
                if market_type == "STOCK" else
                ("BUY FUTURES" if win_dir == "BULL" else "SELL FUTURES"))
        signal["signal_candidate"] = {
            "would_be_signal": _cand_name,
            "direction": win_dir,
            "confidence": round(win, 1),
            "dynamic_confidence": dyn_conf,
            "bull_score": round(bull_adj, 1),
            "bear_score": round(bear_adj, 1),
            "confirmations": confirmations,
            "confirmations_count": len(confirmations),
            "execution": "BLOCKED",
            "blocked_by": vetoes,
            "blocked_count": len(vetoes),
            "note": ("Directional read the engine computed BEFORE execution was "
                     "refused. NOT a recommendation and NOT tradable — the "
                     "vetoes above are what actually govern. Recorded so a "
                     "blocked signal is visible as blocked, rather than "
                     "disappearing into a bare NO TRADE."),
        }
        strike = None
        strikes_top = []
        # V16 — PREPARING intel while the gate holds: the strike + levels the
        # AI is watching, from the SAME selector/level math as a live signal
        # (single source, already computed above). Labelled preparing — the
        # gate still decides; this is never an entry recommendation.
        signal["preparing_levels"] = {
            "direction": win_dir,
            "entry": round(spot, 2), "stop_loss": round(sl, 2),
            "target1": round(targets[0], 2), "target2": round(targets[1], 2),
            "target3": round(targets[2], 2),
            "reward_risk": round(abs(targets[1] - spot) / risk_pts, 2) if risk_pts else 0,
        }
        if has_chain:
            try:
                strikes_top = strike_selector.select_top(
                    (analytics or {}).get("chain", []), win_dir, spot,
                    (analytics or {}).get("expiry", ""),
                    {"stop_loss": round(sl, 2), "target1": round(targets[0], 2),
                     "target2": round(targets[1], 2), "target3": round(targets[2], 2)},
                    n=5,
                )
                strike = strikes_top[0] if strikes_top else None
            except Exception:
                strike, strikes_top = None, []
    else:
        if market_type == "INDEX" or has_chain:
            # options are the vehicle wherever a chain exists (incl. MCX)
            sig_name = "BUY CE" if win_dir == "BULL" else "BUY PE"
        elif market_type == "STOCK":
            sig_name = "BUY STOCK" if win_dir == "BULL" else "SELL STOCK"
        else:
            sig_name = "BUY FUTURES" if win_dir == "BULL" else "SELL FUTURES"
        # sl / targets / risk_pts already computed above (single source)
        reasons = []
        for name in confirmations:
            reasons.extend(layers[name].get("notes", [])[:1])
        signal = {
            "signal": sig_name,
            "direction": win_dir,
            "entry": round(spot, 2),
            "stop_loss": round(sl, 2),
            "target1": round(targets[0], 2),
            "target2": round(targets[1], 2),
            "target3": round(targets[2], 2),
            "confidence": round(win, 1),
            "dynamic_confidence": dyn_conf,
            "confidence_components": components,
            "effective_threshold": round(threshold, 1),
            "threshold_reason": threshold_why,
            "calibration": calibration,
            "bull_score": round(bull_adj, 1),
            "bear_score": round(bear_adj, 1),
            "reward_risk": round(abs(targets[1] - spot) / risk_pts, 2) if risk_pts else 0,
            "confirmations": confirmations,
            "confirmations_count": len(confirmations),
            "vetoes": [],
            "reasons": reasons,
            "tech": tech_block,
        }
        strike = None
        strikes_top = []
        if has_chain and sig_name in ("BUY CE", "BUY PE"):
            strikes_top = strike_selector.select_top(
                (analytics or {}).get("chain", []), win_dir, spot,
                (analytics or {}).get("expiry", ""),
                {"stop_loss": signal["stop_loss"], "target1": signal["target1"],
                 "target2": signal["target2"], "target3": signal["target3"]},
                n=5,
            )
            strike = strikes_top[0] if strikes_top else None

    signal.update(quality.grade(signal, historical_accuracy))

    # ---- V11 trade quality (A+/A/B/C/Avoid) + future path / roadmap ----
    layers["trade_quality"] = iscore.trade_quality(
        signal.get("grade", "NO TRADE"), layers["probability"]["prob_success"],
        layers.get("dom", {}), historical_accuracy,
        layers["mtf"]["alignment"], v11_entry["band"])
    layers["future_path"] = iscore.future_path(layers, spot, levels or {})

    # ---- V13.1 Futures Intelligence (confirmation only — never overrides) ----
    from . import futures as futures_eng
    layers["futures"] = futures_eng.compute(layers, analytics or {}, win_dir, mom)
    layers["decision_explainer"] = futures_eng.explainer(
        layers, layers["futures"], dyn_conf, win_dir)

    # ---- Decision Intelligence synthesis (derivation-only, additive) ----
    from . import intelligence as intel_eng
    layers["intelligence"] = intel_eng.analyze(layers, signal, spot, data_quality)

    # ---- Forward Intelligence: scenarios / next-move / ETA / war room ----
    from . import future as future_eng
    layers["future"] = future_eng.analyze(layers, spot, signal)

    # ---- AI Decision Audit (M11): full trace of the decision ----
    failed_layers = [n for n in WEIGHTS if layers[n][score_key] < CONFIRM_LEVEL]
    signal["audit"] = {
        "generated": signal["signal"] != "NO TRADE",
        "confirmed_layers": confirmations,
        "failed_layers": failed_layers,
        "historical_accuracy": historical_accuracy,
        "probability_score": layers["probability"]["prob_success"],
        "expected_value": layers["probability"]["expected_value"],
        "effective_threshold": signal["effective_threshold"],
        "phases": layers["regime"].get("phases", []),
        "order_flow_score": layers["order_flow"]["score"],
        "trace": signal["vetoes"] if signal["signal"] == "NO TRADE" else signal["reasons"],
    }
    warning = early_warning.analyze(layers, win_dir, win, threshold, bool(vetoes))
    layers["risk"] = risk.assess(signal, tech_block, data_quality, spot)
    narrative = narrator.narrate(symbol, spot, layers, signal, strike, warning)
    for extra in ("expiry", "market_profile"):
        for n in layers[extra].get("notes", [])[:1]:
            narrative.insert(1, n + ("." if not n.endswith(".") else ""))

    # ---- AI Market Coach: hybrid Tamil + trading-English guidance ----
    coach: list[str] = []
    if signal["signal"] == "NO TRADE":
        missing = [m for m in MANDATORY if layers[m][score_key] < CONFIRM_LEVEL]
        if missing:
            side = "bullish" if win_dir == "BULL" else "bearish"
            coach.append(f"Missing confirmation: entry-க்கு முன் {', '.join(missing)} "
                         f"{side}-ஆக மாற வேண்டும்.")
        res = layers["structure"].get("resistance")
        sup = layers["structure"].get("support")
        if win_dir == "BULL" and res:
            coach.append(f"அடுத்து என்ன நடக்க வேண்டும்: {res:,.0f}-க்கு மேலே volume-உடன் clean break தேவை.")
        elif win_dir == "BEAR" and sup:
            coach.append(f"அடுத்து என்ன நடக்க வேண்டும்: {sup:,.0f}-க்கு கீழே volume-உடன் clean break தேவை.")
        if warning.get("setup") not in (None, "NONE"):
            coach.append(f"எப்போது தயாராவது: setup {warning['preparation']}% உருவாகிவிட்டது — "
                         "trigger level-ஐ கவனிக்கவும், முந்திக்கொள்ள வேண்டாம்.")
        if layers["regime"]["score"] < 45:
            rg = layers["regime"]["regime"].replace("_", " ").lower()
            coach.append(f"எப்போது தவிர்ப்பது: {rg} நிலையில் entries பெரும்பாலும் chop ஆகும் — "
                         "capital-ஐ protect செய்து wait செய்யவும்.")
        if not coach:
            coach.append("நிலை தெளிவில்லை. சிறந்த நடவடிக்கை — பொறுமை (patience).")
    else:
        coach.append(f"Trade plan: entry {signal['entry']:,.1f}, stop {signal['stop_loss']:,.1f}, "
                     "targets-ல் scale out செய்யவும். Stop-ஐ தவறாமல் கடைபிடிக்கவும்.")
        if signal.get("grade") == "C":
            coach.append("C-grade setup: எடுத்தால் size குறைக்கவும் — இது A+ trade அல்ல.")
        coach.append(f"Threshold {signal['effective_threshold']}% ({signal['threshold_reason']}).")

    return {
        "ts": time.time(),
        "signal": signal,
        "layers": {k: v for k, v in layers.items()},
        "strike": strike,
        "strikes": strikes_top,
        "warning": warning,
        "narrative": narrative,
        "coach": coach,
        "risk": layers["risk"],
    }
