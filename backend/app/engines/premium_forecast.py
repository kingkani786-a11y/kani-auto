"""Phase 26 — Premium Forecast Engine.

Projects the recommended option's premium over 15 / 30 / 60 / 90 minutes by
combining the already-computed expansion potential (runner probability + class)
against theta decay and IV-crush risk. Derivation-only — no option re-pricing,
no new data. These are scenario estimates, never guarantees.
"""
from __future__ import annotations

from typing import Any

# fraction of the per-session expansion / decay realised by each horizon
_HORIZON_W = {"15m": 0.25, "30m": 0.45, "60m": 0.75, "90m": 1.0}


def forecast(layers: dict[str, Any], strike: dict[str, Any], spot: float) -> dict[str, Any]:
    cap = layers.get("capital_protection") or {}
    intel = layers.get("intelligence") or {}
    exp = intel.get("expansion") or {}
    premium = strike.get("premium_entry")

    if not premium or premium <= 0:
        return {"ready": False, "note": "INSUFFICIENT DATA — no live strike premium yet"}

    runner = float(exp.get("runner_probability") or 0)
    cls = (exp.get("class") or "").upper()
    # session expansion ceiling implied by class + runner probability (decimal)
    cls_ceiling = {"EXPLOSIVE": 1.4, "LARGE": 0.9, "MEDIUM": 0.5, "SMALL": 0.25}.get(cls, 0.4)
    exp_frac = cls_ceiling * (0.4 + 0.6 * runner / 100.0)

    # per-session decay from theta + IV-crush risk (decimal of premium)
    theta = float(cap.get("theta_risk") or 40) / 100.0
    iv_crush = float(cap.get("iv_crush") or 40) / 100.0
    decay_frac = min(0.85, 0.35 * theta + 0.25 * iv_crush)

    forecasts = {}
    for h, w in _HORIZON_W.items():
        net = exp_frac * w - decay_frac * w
        proj = max(premium * 0.1, premium * (1 + net))
        forecasts[h] = {"premium": round(proj, 2), "change_pct": round(net * 100, 1)}

    net60 = forecasts["60m"]["change_pct"]
    classification = ("EXPLOSIVE" if net60 >= 40 else "STRONG" if net60 >= 20
                      else "MODERATE" if net60 >= 5 else "WEAK" if net60 >= -10 else "AVOID")
    # probability the favourable expansion path plays out ~ runner prob, damped by decay
    prob = round(max(5.0, min(90.0, runner * (1 - 0.4 * decay_frac))), 0)

    return {
        "ready": True,
        "current_premium": round(premium, 2),
        "strike": strike.get("strike"), "type": strike.get("type"),
        "forecasts": forecasts,
        "expected_expansion_pct": round(exp_frac * 100, 1),
        "expected_decay_pct": round(decay_frac * 100, 1),
        "theta_risk": round(theta * 100, 0),
        "iv_crush_risk": round(iv_crush * 100, 0),
        "probability": prob,
        "classification": classification,
        "note": "Scenario estimate from expansion potential vs theta/IV decay — not a quote.",
    }
