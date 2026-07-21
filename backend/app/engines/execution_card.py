"""V24.5 — One-Click Execution Card + Dual-Mode Opportunity Radar.

Composes ONE complete actionable instruction (the GOLDEN RULE) from outputs the
platform already computes — strike, premium forecast, expected move, probability,
maturity. Plus a Micro/Swing opportunity radar with expected points + premium +
probability + ETA + entry tier. Derivation-only; probabilities, never certainty.

Example actionable line:
  BUY 23850 PE @ ₹118 · exp ₹132–145 · +18–32 NIFTY pts · 84% · hold 8–15m ·
  SL ₹111 · exit on VWAP reclaim or prob < 60%
"""
from __future__ import annotations

import math
from typing import Any

_TIER = [(850, "Institutional ★★★★★"), (700, "Platinum ★★★★"), (600, "Gold ★★★"),
         (500, "Silver ★★"), (0, "Bronze ★")]
_POINT_LADDER = [5, 10, 20, 30, 50, 100]


_LADDER = [
    ("⚡ Quick", "QUICK", 5, 10, "2–5 min"),
    ("🔥 Fast", "FAST", 10, 20, "5–10 min"),
    ("⭐ Trend", "TREND", 20, 40, "10–30 min"),
    ("💎 Runner", "RUNNER", 40, 80, "30–60 min"),
    ("🚀 Mega", "MEGA", 80, 150, "1–3 hr"),
]


def _opportunity_ladder(em: float, base_prob: float, runner: float) -> list[dict[str, Any]]:
    """5-tier opportunity ladder Quick→Mega; probability decays with distance
    (point-capture model), runner prob lifts the far tiers."""
    if em <= 0:
        em = 40.0
    edge = max(0.4, min(1.0, base_prob / 100.0))
    out = []
    prev = 100.0
    for label, mode, lo, hi, t in _LADDER:
        # 2026-07-21: this was the SECOND copy of the fabricated decay curve
        # (the first lived in _point_capture). Measured against 1694 real
        # ignitions it overstated badly — "Runner 40-80pts 49%" when reaching
        # 50pt happened 4.8% of the time, "Mega 32%" when 100pt happened 0.5%.
        # Prefer the OBSERVED reach-rate for this tier's lower bound; fall back
        # to the model only when the black box has no sample.
        _obs = None
        try:
            from ..services.opportunity_metrics import observed_reach_pct as _orp
            _obs = _orp(lo)
        except Exception:
            _obs = None
        p = _obs if _obs is not None else 100.0 * math.exp(-0.55 * (lo / em)) * (0.6 + 0.4 * edge)
        if _obs is None and mode in ("RUNNER", "MEGA") and runner:
            # only lift a MODELLED number; never inflate an observed frequency
            p = max(p, runner * (0.9 if mode == "RUNNER" else 0.7))
        # capturing 40 pts implies first capturing 5 — a far tier can never be
        # more probable than a nearer one (keeps runner lift honest on
        # small-expected-move instruments)
        p = min(p, prev)
        p = max(5.0, min(96.0, p))
        prev = p
        out.append({"mode": mode, "label": label, "expected_points": [lo, hi],
                    "probability": round(p, 0), "observed": _obs is not None, "time": t})
    return out


# indicative time band per point tier — the same declared bands the
# Opportunity Ladder already publishes (not a computed ETA)
_POINT_TIME = {5: "2–5 min", 10: "5–10 min", 20: "10–30 min",
               30: "10–30 min", 50: "30–60 min", 100: "1–3 hr"}


def _point_capture(em: float, base_prob: float) -> list[dict[str, Any]]:
    """V25 §3 — probability of capturing N points, from expected move (~1σ)."""
    if em <= 0:
        return []
    edge = max(0.4, min(1.0, base_prob / 100.0))
    out = []
    for pts in _POINT_LADDER:
        p = 100.0 * math.exp(-0.7 * (pts / em)) * (0.6 + 0.4 * edge)
        out.append({"points": pts, "probability": round(max(3.0, min(96.0, p)), 0),
                    "time": _POINT_TIME.get(pts, "")})
    return out


def _tier(trade_score: float) -> str:
    for thr, label in _TIER:
        if trade_score >= thr:
            return label
    return "Bronze ★"


def build(layers: dict[str, Any], signal: dict[str, Any], decision: dict[str, Any],
          strike: dict[str, Any], spot: float) -> dict[str, Any]:
    di = decision.get("intelligence_synthesis") or {}
    sm = decision.get("signal_maturity") or {}
    pf = decision.get("premium_forecast") or {}
    eg = decision.get("execution_gate") or {}
    prob_layer = layers.get("probability") or {}
    exp = (layers.get("intelligence") or {}).get("expansion") or {}
    direction = signal.get("direction") or "NEUTRAL"
    em = float(prob_layer.get("expected_move") or 0)

    # the gate is authoritative for whether to act
    gated = eg.get("final_decision") or decision.get("primary_action") or "WAIT"
    is_buy = gated in ("BUY CALL", "BUY PUT")

    # --- Opportunity Ladder: 5 tiers Quick→Mega (probability decays with distance) ---
    runner = float(exp.get("runner_probability") or 0)
    base_prob = float(di.get("conviction") or signal.get("dynamic_confidence") or 0)
    radar = _opportunity_ladder(em, base_prob, runner)
    # V25 §3 replaced 2026-07-21: the declared decay curve overstated reality
    # 3x-50x, so this now serves OBSERVED black-box frequencies. Falls back to
    # the old curve only if the black box has no sample yet (honest: an empty
    # dataset must not silently render as 0%).
    try:
        from ..services.opportunity_metrics import outcome_stats as _os
        _obs = _os()
        point_capture = (_obs if (_obs.get("sample_n") or 0) >= 100
                         else {"observed": False, "sample_n": _obs.get("sample_n", 0),
                               "rows": [{"points": r["points"], "reached_pct": r["probability"]}
                                        for r in _point_capture(em, base_prob)],
                               "note": "Insufficient black-box sample — declared model, not observed."})
    except Exception:
        point_capture = {"observed": False, "sample_n": 0, "rows": [],
                         "note": "Outcome statistics unavailable."}

    # V19 §2 — trade style suited to the current tape (derived from regime +
    # runner conviction; this is an intraday engine, so SWING/POSITION are N/A)
    regime_name = (layers.get("regime") or {}).get("regime") or ""
    trade_style = ("INTRADAY TREND" if regime_name in ("TRENDING", "HIGH_MOMENTUM") and runner >= 40
                   else "SCALP")
    style_reason = (f"{regime_name.replace('_', ' ').title() or 'Current'} regime, "
                    f"runner {runner:.0f}% — "
                    + ("ride the move" if trade_style == "INTRADAY TREND" else "quick captures only"))

    if not is_buy:
        reason = eg.get("blocking_reasons") or [decision.get("reason", "confluence not aligned")]
        return {
            "ready": True, "is_trade": False,
            "actionable": f"WAIT — {('; '.join(reason))[:140]}",
            "opportunity_radar": radar,
            "point_capture": point_capture,
            "trade_style": trade_style, "style_reason": style_reason,
            "note": "No high-quality setup — protecting capital. Quality over quantity.",
        }

    # --- the actionable execution card (GOLDEN RULE) ---
    opt = "PE" if direction == "BEAR" else "CE"
    pe = strike.get("premium_entry")
    # Dead-key fix 2026-07-21: this read `premium_sl` and `premium_targets`,
    # which strike_selector NEVER writes (it writes premium_stop_loss and
    # premium_target1/2/3). sl was therefore always None — the actionable line
    # rendered "SL Rs None" — and ptargets always [], silently falling through
    # to the forecast branch. Grepped: those two names appear nowhere as writes.
    sl = strike.get("premium_stop_loss")
    ptargets = [t for t in (strike.get("premium_target1"), strike.get("premium_target2"),
                            strike.get("premium_target3")) if t is not None]
    # expected premium range: stored targets, else premium-forecast 30m/60m
    if isinstance(ptargets, list) and ptargets:
        prem_lo, prem_hi = ptargets[0], ptargets[-1]
    elif pf.get("ready"):
        prem_lo = pf["forecasts"].get("30m", {}).get("premium")
        prem_hi = pf["forecasts"].get("60m", {}).get("premium")
    else:
        prem_lo = prem_hi = None
    pts_lo, pts_hi = round(em * 0.2) or 8, round(em * 0.4) or 20
    prob = int(round(base_prob))
    hold = micro["eta_min"]
    grade = (di.get("trade_quality") or {}).get("score", 0)

    card = {
        "action": gated, "strike": strike.get("strike"), "type": opt,
        "entry_premium": pe, "stop_premium": sl,
        "expected_premium": [prem_lo, prem_hi],
        "expected_points": [pts_lo, pts_hi],
        "probability": prob,
        "hold_minutes": [max(3, hold - 4), hold + 7] if hold else [5, 15],
        "tier": _tier(grade),
        "exit_rule": "Exit on VWAP reclaim or probability < 60%",
        "targets": [decision.get("target1"), decision.get("target2"), decision.get("target3")],
        "alternate_strikes": [s.get("strike") for s in (decision.get("strikes") or [])[:3]],
    }
    actionable = (f"{gated} {card['strike']} {opt} @ ₹{pe} · "
                  f"exp ₹{prem_lo}–{prem_hi} · +{pts_lo}–{pts_hi} NIFTY pts · "
                  f"{prob}% · hold {card['hold_minutes'][0]}–{card['hold_minutes'][1]}m · "
                  f"SL ₹{sl} · {card['exit_rule']}")

    return {
        "ready": True, "is_trade": True,
        "actionable": actionable,
        "card": card,
        "opportunity_radar": radar,
        "point_capture": point_capture,
        "trade_style": trade_style, "style_reason": style_reason,
        "note": "One actionable institutional instruction. Probabilities, not certainty; "
                "capital protection overrides.",
    }
