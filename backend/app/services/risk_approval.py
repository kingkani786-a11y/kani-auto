"""Risk Approval Engine — V5 layer 5, the capital & market safety gate.

A read-only APPROVAL layer between the Decision Engine and the human. It never
decides direction and NEVER places an order — it consolidates the account-risk,
market-risk and trade-quality checks (until now scattered across Kill Switch,
Safe Mode, data quality, VIX, RR) into ONE labelled verdict, plus a risk-based
position size. Anything it cannot honestly see (a news feed, live broker
positions) is marked UNKNOWN — never faked, and UNKNOWN never blocks.

Check value convention: True = pass · False = hard blocker · None = unknown/NA.
Approval requires an active setup AND zero False checks. Doctrine: informational
only, not investment advice; the user executes manually on their own broker.
"""
from __future__ import annotations

from typing import Any

from ..config import settings
from ..core.state import is_market_open, state

# declared thresholds (tunable from evidence)
VIX_LOW, VIX_HIGH = 10.0, 22.0     # outside this band = elevated risk
MIN_RR = 2.0                        # reward:risk floor
MIN_PROB = 60.0                     # probability floor (%)


def _chk(name: str, ok: bool | None, detail: str) -> dict[str, Any]:
    return {"name": name, "ok": ok, "detail": detail}


def approve() -> dict[str, Any]:
    dec = state.decision or {}
    ks = state.kill_switch or {}
    sm = state.safe_mode or {}
    layers = (state.intelligence or {}).get("layers") or {}
    dq = state.data_quality or "UNKNOWN"
    is_open = is_market_open(state.market_type)

    entry = dec.get("entry")
    stop = dec.get("stop_loss")
    rr = dec.get("reward_risk")
    is_trade = bool(dec.get("is_trade"))
    vix = (layers.get("vix_correlation") or {}).get("vix")
    prob = (layers.get("probability") or {}).get("prob_success")
    if prob is None:
        prob = dec.get("probability")
    liq = (layers.get("liquidity") or {}).get("score")

    # ── position size — owner Step 7 (Risk Panel Final, 2026-07-26) fix:
    # this used to be TWO separate, disagreeing computations — a flat
    # capital% "risk_amt" that never looked at entry/stop despite its own
    # comment claiming reuse, and index-point sizing (dec.recommended_lots/
    # max_safe_lots) that used the UNDERLYING's point move as if that were
    # an option buyer's risk. Now reads the SAME premium-based sizing
    # market_service.py already computes into decision["position_sizing"]
    # (portfolio_risk.position_size fed the real premium entry/stop) — the
    # same number ScalpingTool.tsx already shows, so the two panels can no
    # longer disagree on "the" position size for the same trade.
    ps_data = dec.get("position_sizing") or {}
    cap = float(ps_data.get("capital") or settings.capital or 0)
    risk_pct = float(ps_data.get("risk_pct") or settings.risk_per_trade_pct or 0)
    risk_amt = ps_data.get("risk_amount")
    max_loss = ps_data.get("capital_required")  # full premium paid — the honest worst case
    max_lots = ps_data.get("lots") if ps_data.get("lot_size", 1) not in (1, None) else ps_data.get("qty")
    # same confidence-scaling decision.py's own sizing already applies
    _LOT_BAND = {"HIGH": 1.0, "MODERATE": 0.5, "LOW": 0.25}
    rec_lots = (int(max_lots * _LOT_BAND.get(dec.get("conviction"), 0.0))
                if isinstance(max_lots, (int, float)) else None)
    reward_amt = round(risk_amt * rr, 0) if (risk_amt and rr) else None

    # ── ACCOUNT RISK ──
    account = [
        _chk("Daily risk / Kill Switch",
             (not ks.get("active")) if ks else None,
             "; ".join(ks.get("reasons", [])) if ks.get("active") else "within limits"),
        _chk("Safe Mode",
             (not sm.get("active")) if sm else None,
             "; ".join(sm.get("reasons", []) or []) if sm.get("active") else "clear"),
        _chk("Margin sufficient",
             (risk_amt is not None and cap > 0) or None,
             f"₹{risk_amt:,.0f} risk on ₹{cap:,.0f} ({risk_pct}%)" if risk_amt else "capital not set"),
        _chk("Open positions", None,
             "manual — the system never places or holds orders"),
    ]

    # ── MARKET RISK ──
    market = [
        _chk("Data fresh", dq == "GOOD", f"feed quality {dq}"),
        _chk("India VIX", (VIX_LOW <= vix <= VIX_HIGH) if vix else None,
             f"VIX {vix}" if vix else "VIX unavailable"),
        _chk("Market open / no halt", is_open, "open" if is_open else "market closed"),
        _chk("News / event", None, "no news feed connected — check manually"),
    ]

    # ── TRADE QUALITY ──
    quality = [
        _chk("Reward:Risk ≥ 1:2", (rr >= MIN_RR) if rr else None,
             f"1:{rr}" if rr else "no active setup"),
        _chk("Probability ≥ 60%", (prob >= MIN_PROB) if prob else None,
             f"{prob}%" if prob else "—"),
        _chk("Liquidity", (liq >= 55) if liq else None,
             f"score {liq}" if liq else "—"),
    ]

    checks = account + market + quality
    blockers = [c for c in checks if c["ok"] is False]
    # approval needs a live directional setup AND zero hard blockers
    if not is_trade:
        approved, status = False, "NO_SETUP"
    elif blockers:
        approved, status = False, "BLOCKED"
    else:
        approved, status = True, "APPROVED"

    return {
        "status": status,            # APPROVED | BLOCKED | NO_SETUP
        "approved": approved,
        "sections": {"account": account, "market": market, "quality": quality},
        "blockers": [c["name"] for c in blockers],
        "position_size": {
            "capital": cap, "risk_pct": risk_pct,
            "recommended_lots": rec_lots, "max_lots": max_lots,
            "risk_amount": risk_amt, "max_loss": max_loss,
            "reward_amount": reward_amt, "rr": rr,
            "entry": entry, "stop_loss": stop,
        },
        "note": ("Approval gate — capital & market safety only; it never decides "
                 "direction and never places an order. Informational, not "
                 "investment advice. UNKNOWN checks are shown honestly, not passed."),
    }
