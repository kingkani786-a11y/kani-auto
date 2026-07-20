"""Decision Contract — V2.1's unifier: entry/hold/exit in ONE object.

Every decision (BUY or WAIT) ships as a contract assembled purely from state
the engines already published (Rule 10: one source, many consumers — this
derives, never re-decides). A BUY carries its why, confidence, invalidations
and exit plan; a WAIT carries its why (Rule 5/11: explain before execute).
Read-only; the system still never places orders.
"""
from __future__ import annotations

import time
from typing import Any

from ..core.state import state


def _layers() -> dict[str, float]:
    # every level can be None/non-dict mid-cycle (live 500 on 2026-07-20:
    # layers.intelligence was None between engine publishes) — walk defensively
    node: Any = state.intelligence or {}
    for key in ("layers", "intelligence"):
        node = node.get(key) if isinstance(node, dict) else None
        if node is None:
            return {}
    rows = node.get("rows") if isinstance(node, dict) else None
    out: dict[str, float] = {}
    for r in rows or []:
        try:
            if isinstance(r, dict) and r.get("layer") is not None and r.get("score") is not None:
                out[str(r["layer"])] = float(r["score"])
        except (TypeError, ValueError):
            continue
    return out


def _invalidations(dec: dict, tech: dict) -> list[str]:
    """Pre-stated exit conditions from data we actually have — never invented."""
    inv: list[str] = []
    sl = dec.get("stop_loss")
    if sl:
        inv.append(f"Price crosses stop {round(float(sl), 1)}")
    vwap = tech.get("vwap")
    if vwap:
        side = "below" if (dec.get("action") or "").endswith("CALL") else "above"
        inv.append(f"Sustained break {side} VWAP {round(float(vwap), 1)}")
    ks = state.kill_switch or {}
    inv.append("Kill Switch / Safe Mode trips (capital protection)")
    if ks.get("active"):
        inv[-1] += " — ACTIVE NOW"
    return inv


def contract() -> dict[str, Any]:
    """Never 500s: any internal error degrades to an honest WAIT contract
    (Rule 1 — fail to WAIT, never to a broken card)."""
    try:
        return _contract()
    except Exception as e:  # pragma: no cover — belt and braces for live shapes
        return {"action": "WAIT", "is_trade": False, "confidence": None,
                "why": [f"Contract builder degraded ({type(e).__name__}) — engine unaffected"],
                "entry_grade": {"grade": None, "score": None, "parts": {}},
                "ledger": [], "ledger_total": None,
                "aging": {"age_s": None, "state": None, "decay_pct": 0, "aged_confidence": None},
                "entry_window_live": {"seconds_left": None, "state": None},
                "risk": None, "expected_move": None, "reward_risk": None,
                "entry": None, "entry_window": None,
                "exit_plan": {}, "trade_readiness": {"wave_direction": None, "premium_strength": None, "risk_approved": None},
                "trade_light": {"color": "RED", "dot": "🔴", "label": "NO TRADE"},
                "best_strike": None,
                "buy_checklist": [], "buy_checklist_score": {"passed": 0, "measured": 0, "total": 7},
                "invalidations": [], "instruction": "Standing aside.",
                "signal_ts": None, "as_of": int(time.time()),
                "note": "Degraded honest fallback — display layer only."}


def _contract() -> dict[str, Any]:
    dec = state.decision or {}
    sig = state.signal or {}
    tech = (sig.get("tech") or {})
    layers = _layers()

    action = dec.get("action") or "WAIT"
    is_trade = bool(dec.get("is_trade"))
    primary_action = dec.get("primary_action")

    # ── Master Decision reconciliation (owner, 2026-07-21 — "ஒரே Master
    # Decision மட்டும் இருக்க வேண்டும்; அதை எல்லா panels reference செய்ய
    # வேண்டும்"). Two separate gates exist upstream: decision.py's first-pass
    # is_trade/primary_action, and execution_gate.py's STRICTER, LATER "last
    # institutional checkpoint" (own doc: "authoritative gated verdict") that
    # adds quality bars (confidence>=80, fire>=85, trade quality>=800,
    # institutional>=70, data GOOD) on top. Until this fix, TradeNowCard's
    # trade_light read only the first pass — so it could show GREEN/BUY a
    # beat before the true final gate agreed, while a separate panel reading
    # execution_gate directly (LiveCandleCommand) could simultaneously show
    # AVOID for the exact same cycle. Capital protection > opportunity is
    # this project's own doctrine, so when the stricter gate is ready and
    # disagrees, ITS answer wins here. This only ever downgrades a fresh
    # entry call (primary_action == "ENTER") toward WAIT — it can never
    # invent a BUY the first pass didn't have, and it never touches
    # open-position states (HOLD/TRAIL/EXIT), which execution_gate doesn't
    # model at all.
    eg = dec.get("execution_gate") or {}
    if eg.get("ready") and primary_action == "ENTER" and eg.get("final_decision") not in ("BUY CALL", "BUY PUT"):
        is_trade = False
        action = "WAIT"
        primary_action = "WAIT"

    # live decision publishes conviction as a LABEL sometimes ("NONE"/"LOW") —
    # normalise: numeric or None, never a string (card showed "NONE%" 07-20)
    conviction = dec.get("conviction")
    if not isinstance(conviction, (int, float)):
        try:
            conviction = float(conviction)
        except (TypeError, ValueError):
            conviction = None

    # WHY (Rule 11 — explain before execute), for BUY and WAIT alike
    reason = dec.get("reason")
    why: list[str] = []
    if isinstance(reason, list):
        why = [str(r) for r in reason][:6]
    elif reason:
        why = [str(reason)]
    if not why:
        # fall back to the strongest confirming layers — honest, from scores
        top = sorted(((k, v) for k, v in layers.items() if v and v >= 65),
                     key=lambda kv: kv[1], reverse=True)[:4]
        why = [f"{k} {int(v)}" for k, v in top] or ["No published reason — engine idle"]

    # ── Unified Entry Grade (C2, charter L7): ONE grade instead of five
    # scattered scores. Declared blend of already-published numbers — conviction
    # (decision), signal confidence, and layer breadth. Not win-calibrated.
    # live shape: sig["signal"] is usually the NAME string ("NO TRADE") with
    # confidence as a sibling; older/packet shapes nest a dict. Handle both.
    sig_conf = None
    try:
        _sv = sig.get("signal")
        _src = _sv if isinstance(_sv, dict) else sig
        sig_conf = float(_src.get("confidence"))
    except (TypeError, ValueError, AttributeError):
        pass
    breadth = (sum(1 for v in layers.values() if v >= 55) / len(layers) * 100) if layers else None
    parts = [p for p in (conviction, sig_conf, breadth) if isinstance(p, (int, float))]
    entry_score = round(sum(parts) / len(parts)) if parts else None
    grade = (None if entry_score is None else
             "A+" if entry_score >= 90 else "A" if entry_score >= 80 else
             "B" if entry_score >= 70 else "C" if entry_score >= 60 else "D")
    entry_grade = {
        "grade": grade, "score": entry_score,
        "parts": {"conviction": conviction, "signal_confidence": sig_conf,
                  "layer_breadth": round(breadth) if breadth is not None else None},
    }

    # ── Evidence Ledger (C3, Rule 3): confidence decomposed into five named
    # pillars, /20 each — confidence is EVIDENCE, not a number. Pillars map to
    # published layer scores; a pillar with no data shows None, never 0.
    def _p20(*names: str) -> int | None:
        vals = [layers[n] for n in names if n in layers]
        return round(sum(vals) / len(vals) / 100 * 20) if vals else None
    ledger = [
        {"pillar": "Trend", "score": _p20("Trend")},
        {"pillar": "Price Action", "score": _p20("Structure", "MTF")},
        {"pillar": "Institutional", "score": _p20("Institutional", "Smart Money", "OI")},
        {"pillar": "Momentum/Flow", "score": _p20("Futures", "Liquidity", "Volume Profile")},
        {"pillar": "Risk", "score": _p20("Risk")},
    ]
    known = [e["score"] for e in ledger if e["score"] is not None]
    ledger_total = round(sum(known) / (len(known) * 20) * 100) if known else None

    # ── Signal Aging (C4, Rule 9): stale signals decay — never hold an old BUY.
    # Declared ramp: full strength ≤120s, then −2% per 30s. State labels:
    # Fresh<2m · Good<5m · Old<10m · Weak<15m · STALE≥15m.
    now = time.time()
    sig_ts = sig.get("ts")
    age_s = int(now - sig_ts) if sig_ts else None
    decay_pct = 0.0
    aged_conf = conviction
    aging_state = None
    if age_s is not None:
        decay_pct = max(0.0, (age_s - 120) / 30.0 * 2.0)
        if isinstance(conviction, (int, float)):
            aged_conf = round(max(0.0, conviction * (1 - decay_pct / 100)), 1)
        aging_state = ("Fresh" if age_s < 120 else "Good" if age_s < 300 else
                       "Old" if age_s < 600 else "Weak" if age_s < 900 else "STALE")
    aging = {"age_s": age_s, "state": aging_state,
             "decay_pct": round(decay_pct, 1), "aged_confidence": aged_conf}

    # ── Entry Window countdown (C5, Rule 8): seconds until the aged confidence
    # crosses the 60% floor under the SAME declared ramp — derived, not invented.
    # conf*(1-decay/100)=60 ⇒ decay*=(1-60/conf)*100 ⇒ age*=120+decay*/2*30.
    window_s = None
    if isinstance(conviction, (int, float)) and conviction > 0 and age_s is not None:
        if conviction <= 60:
            window_s = 0
        else:
            decay_star = (1 - 60.0 / conviction) * 100.0
            age_star = 120 + decay_star / 2.0 * 30.0
            window_s = max(0, int(age_star - age_s))
    entry_window_live = {
        "seconds_left": window_s,
        "state": (None if window_s is None else
                  "CLOSED" if window_s == 0 else
                  "CLOSING" if window_s <= 30 else "OPEN"),
    }

    exit_plan = {
        "stop_loss": dec.get("stop_loss"),
        "target1": dec.get("target1") or (dec.get("next_add_levels") or [None])[0],
        "target2": dec.get("target2"),
        "target3": dec.get("target3"),
        "trail": "After T1 — trail to cost, then EMA/structure" if is_trade else None,
    }

    # ── Trade Readiness (owner, 2026-07-21 — the "Simple Mode" hero fields):
    # a display-only alignment check over signals ALREADY computed elsewhere
    # (premium_radar's chain-wave + phase, Risk Approval's gate). NEVER a
    # second decision gate — the real gate stays Kill Switch/Risk Approval;
    # this only explains, in plain words, what's already true.
    _radar_live = False
    try:
        from . import premium_radar as _radar, risk_approval as _ra
        _rr = _radar.radar(top=1)
        # Is the radar actually seeing anything? With 0 strikes tracked (market
        # closed, or pre-first-tick after open) "premium isn't building" and
        # "no wave" are NOT findings — they are the absence of data. Same rule
        # already applied to Structure; applying it inconsistently is what made
        # the closed-market dashboard show ✗ Premium / ✗ Wave as if measured.
        _radar_live = bool(_rr.get("tracked"))
        _waves = _rr.get("chain_wave") or []
        wave_dir = _waves[0]["direction"] if _waves else None
        _leaders = (_rr.get("leaders") or []) + (_rr.get("watchlist") or [])
        _phase_code = _leaders[0].get("phase", {}).get("code") if _leaders else None
        premium_strength = ({"BUILDING": "Weak", "RUNNER_BUILDING": "Moderate",
                             "RUNNER_CONFIRMED": "Strong"}.get(_phase_code))
        risk_ok = _ra.approve().get("status") == "APPROVED"
    except Exception:
        wave_dir, premium_strength, risk_ok = None, None, None
    trade_readiness = {
        "wave_direction": wave_dir,               # "up" | "down" | None
        "premium_strength": premium_strength,      # Weak/Moderate/Strong | None
        "risk_approved": risk_ok,                  # True/False/None(unknown)
    }

    # ── AI Trade Light (owner, 2026-07-21 — a traffic signal a trader reads
    # without parsing anything): pure lookup over the decision engine's own
    # already-computed 9-state `primary_action` (decision.py) — no new state,
    # no new gate, just a color name for a state that already exists.
    _LIGHT = {
        "FULL EXIT": ("BLACK", "⚫", "EXIT"),
        "PARTIAL EXIT": ("BLUE", "🔵", "RUNNING"),
        "TRAIL": ("BLUE", "🔵", "RUNNING"),
        "HOLD": ("BLUE", "🔵", "RUNNING"),
        "ENTER": ("GREEN", "🟢", "BUY"),
        "PREPARE": ("YELLOW", "🟡", "PREPARE"),
        "WATCH": ("YELLOW", "🟡", "PREPARE"),
        "WAIT": ("RED", "🔴", "NO TRADE"),
    }
    _color, _dot, _label = _LIGHT.get(primary_action, ("RED", "🔴", "NO TRADE"))
    trade_light = {"color": _color, "dot": _dot, "label": _label}

    # ── Best Strike (owner, 2026-07-21 — "BEST STRIKE 7850 PE" in the Level-1
    # hero): the exact instrument the execution_card engine already selected
    # and gated — read-only, only surfaced once the gate has actually armed a
    # trade (honest: no strike identity is invented for a WAIT state).
    _card = (dec.get("execution_card") or {}).get("card") or {}
    best_strike = ({"strike": _card.get("strike"), "type": _card.get("type")}
                   if is_trade and _card.get("strike") else None)

    # ── BUY Checklist (owner, 2026-07-21 — "இந்த ஏழு PASS ஆனால் தான் BUY"):
    # her 4-item WHY-BUY checklist, each a pure boolean read of a number this
    # contract already computed above (ledger, trade_readiness) — display
    # only, no new gate. The real gate stays Kill Switch + Risk Approval.
    # ONE checklist object (owner 2026-07-21: "Hero மற்றும் AI Thinking இரண்டும்
    # ஒரே backend object-ஐ render செய்ய வேண்டும்"). Previously the hero rendered
    # these 4 booleans while AI Thinking rendered the radar's OWN 4 different
    # checks — two "checklists" that could disagree on screen. Both now render
    # this list. `ok` is True / False / None, where None means NOT MEASURABLE
    # YET — never shown as a ✗, because "we can't see it" is not "it failed".
    _inst_pillar = next((e["score"] for e in ledger if e["pillar"] == "Institutional"), None)
    _vol = layers.get("Volume Profile")
    _cal = ((dec.get("ai_trust") or {}).get("components") or {}).get("calibration")
    buy_checklist = [
        {"key": "premium_building", "label": "Premium Building",
         "ok": (premium_strength in ("Moderate", "Strong")) if _radar_live else None},
        {"key": "institutional_flow", "label": "Institutional Flow",
         "ok": _inst_pillar >= 14 if isinstance(_inst_pillar, (int, float)) else None},
        {"key": "wave_confirmed", "label": "Wave Confirmed",
         "ok": (wave_dir is not None) if _radar_live else None},
        {"key": "risk_gate", "label": "Risk Gate PASS", "ok": risk_ok},
        {"key": "volume", "label": "Volume",
         "ok": _vol >= 55 if isinstance(_vol, (int, float)) else None},
        {"key": "calibration", "label": "Calibration",
         "ok": _cal >= 55 if isinstance(_cal, (int, float)) else None},
        # Structure stays UNMEASURED on purpose. The owner's instruction was
        # explicit: BOS/CHOCH/HH/HL/LH/LL must exist first — "இவை வந்த பிறகுதான்
        # 'Structure ✔' checklist-ல் சேர்க்க வேண்டும்". A generic structure layer
        # score exists, but passing it off as this check would be exactly the
        # fabricated confirmation the charter forbids.
        {"key": "structure", "label": "Structure", "ok": None,
         "note": "Market Structure Engine not built — not measured"},
    ]
    _known = [c["ok"] for c in buy_checklist if c["ok"] is not None]
    buy_checklist_score = {"passed": sum(1 for v in _known if v),
                           "measured": len(_known), "total": len(buy_checklist)}

    return {
        "action": action,
        "is_trade": is_trade,
        "confidence": conviction,
        "why": why,
        "entry_grade": entry_grade,
        "ledger": ledger, "ledger_total": ledger_total,
        "aging": aging, "entry_window_live": entry_window_live,
        "risk": (state.risk or {}).get("capital_risk") or dec.get("grade"),
        "expected_move": dec.get("opportunity") or dec.get("market_state_label"),
        "reward_risk": dec.get("reward_risk"),
        "entry": dec.get("entry"),
        "entry_window": dec.get("entry_window"),
        "exit_plan": exit_plan,
        "trade_readiness": trade_readiness,
        "trade_light": trade_light,
        "best_strike": best_strike,
        "buy_checklist": buy_checklist,
        "buy_checklist_score": buy_checklist_score,
        "invalidations": _invalidations(dec, tech),
        "instruction": ("If ANY invalidation occurs → EXIT immediately."
                        if is_trade else
                        "Standing aside — re-evaluated every engine cycle."),
        "signal_ts": sig.get("ts"),
        "as_of": int(time.time()),
        "note": ("One contract = entry, hold and exit in one logic. Derived "
                 "from the published engine state; informational only — the "
                 "user executes manually, the system never places orders."),
    }
