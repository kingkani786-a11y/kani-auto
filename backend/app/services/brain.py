"""AI Market Brain (Rule 12) — natural-language Q&A over EXISTING state.

A rule-based reasoning layer (no external LLM, no new market data). It reads
the intelligence the platform already computed (layers, decision, exit, scalp,
future, war room) and answers trader questions in probabilities — never
certainty. If it can't map a question it explains what it can see instead.
"""
from __future__ import annotations

import re
from typing import Any

from ..core.state import state


def _layers() -> dict[str, Any]:
    return (state.intelligence.get("layers") or {})


def _num(q: str) -> float | None:
    m = re.findall(r"\d{3,6}(?:\.\d+)?", q.replace(",", ""))
    return float(m[0]) if m else None


AUTO_QUESTIONS = [
    "What is happening now?",
    "What is the next likely move?",
    "Should the trader enter, wait or exit?",
    "Is this a runner?",
    "Where are institutions trapped?",
    "Where should I exit?",
    "How far can premium expand?",
]

# Phase 25 — AI Chief Strategist: the permanent questions answered proactively.
CHIEF_QUESTIONS = [
    "What is happening now?",
    "What should I do now?",
    "What is the highest probability trade?",
    "What strike should I buy?",
    "What strike should I avoid?",
    "What premium should I buy?",
    "What premium should I avoid?",
    "Where should I enter?",
    "Where should I exit?",
    "Where should I re-enter?",
    "How much premium expansion is expected?",
    "What is the safest trade?",
    "What is the most aggressive trade?",
    "Where are institutions trapped?",
    "Where are buyers trapped?",
    "Where are sellers trapped?",
    "What is Market DNA saying?",
    "What happened in similar setups?",
    "Why is the confidence what it is?",
    "Why not 90%?",
    "What could invalidate this trade?",
    "Should I wait?",
]


def auto_brief() -> list[dict[str, Any]]:
    """S14 — auto-answer the key questions so the trader never has to ask."""
    return [{"q": q, **answer(q)} for q in AUTO_QUESTIONS]


def _market_dna() -> dict[str, Any]:
    """Phase 20 — real Market DNA match when available (≥10 comparable sessions),
    else a regime-based proxy so the card still shows something honest."""
    dna = state.market_dna or {}
    if dna.get("ready"):
        return {"match_pct": dna.get("match_score", 0),
                "matches": dna.get("samples", 0),
                "historical_win_rate": dna.get("historical_win_rate"),
                "regime": (_layers().get("regime") or {}).get("regime", ""),
                "verdict": dna.get("verdict"),
                "note": "Market DNA — stored historical similarity"}
    # proxy fallback (insufficient DNA): how the current regime has done
    from . import memory
    L = _layers()
    regime = (L.get("regime") or {}).get("regime", "")
    sub = [o for o in memory._outcomes if o.get("regime") == regime]
    wr = memory.historical_accuracy(regime)
    matches = len(sub)
    match_pct = min(95, matches * 6) if matches else 0
    return {"match_pct": match_pct, "matches": matches,
            "historical_win_rate": wr, "regime": regime,
            "verdict": dna.get("verdict", "NO MATCH"),
            "note": "Regime proxy — DNA builds toward ≥10 comparable sessions"}


def _evolution_summary() -> dict[str, Any]:
    """Phase 23 — surface the latest nightly self-tuning audit in the card."""
    from . import evolution
    nl = evolution.last_nightly()
    return {"system_grade": nl.get("system_grade"),
            "ran": bool(nl.get("nightly")),
            "top_recommendation": (nl.get("recommendations") or [{}])[0].get("title")
                                  if nl.get("recommendations") else None,
            "note": nl.get("note")}


def _status_brief() -> dict[str, Any]:
    """RC1.16.4 — honest AI-status block for when no live analysis exists yet.
    Owner: the bare 'no live data' fallback reads like a broken feature; say
    WHY there is no answer, what the first cycle will do, and when reliable
    analysis arrives. Every field comes from real state — nothing fabricated,
    no invented percentages or ETAs."""
    from ..config import settings
    from ..core.state import is_market_open, market_status

    connected = state.connected
    ms = market_status(state.market_type)
    open_ = ms["is_open"]
    if not connected:
        why = "Broker not connected — no market data has been received."
        nxt = "Enter Client ID + Access Token on Settings and connect; the first AI cycle starts automatically."
        eta = "First analysis lands within one AI cycle of connecting (market hours)."
    elif not open_:
        why = "Market closed — scanner paused. Calm expected state, not a fault."
        nxt = f"Analysis resumes automatically at open ({ms.get('next_open_ist') or 'next session'} IST)."
        eta = f"~{ms.get('seconds_to_open', 0) // 3600}h {(ms.get('seconds_to_open', 0) % 3600) // 60}m to open — no refresh needed."
    else:
        why = "Connected and market open — waiting for the first AI cycle to complete."
        nxt = "First cycle is running now."
        eta = f"Within ~{settings.ai_interval}s (one AI cycle)."
    # RC1.16.5 — pipeline stages from REAL state (owner: no percentages, no
    # fabricated progress — each stage's status is simply whether that data
    # actually exists in memory right now).
    an = state.analytics or {}
    stages = [
        ("Broker connected", connected),
        ("Spot + candles", bool(state.spot)),
        ("Option chain", bool(an.get("chain"))),
        ("OI analysis", bool(an.get("call_oi") or an.get("put_oi") or an.get("oi"))),
        ("Greeks", bool(state.greeks)),
        ("Confluence + gate", bool((state.intelligence or {}).get("layers"))),
    ]
    active = connected and open_
    first_pending = next((s for s, done in stages if not done), None)
    pipeline = [{"step": s,
                 "state": ("done" if done else
                           "loading" if active and s == first_pending else "pending")}
                for s, done in stages]
    waiting_for = [s for s, done in stages if not done]

    return {
        "ai_status": {
            "broker": "CONNECTED" if connected else "NOT CONNECTED",
            "market": ms["status"],
            "ist_time": ms["ist_time"],
            "data_quality": state.data_quality,
            "ai_cycle": "WAITING FOR FIRST CYCLE" if active else "PAUSED",
        },
        "reason": why,
        "next_action": nxt,
        "pipeline": pipeline,
        "waiting_for": waiting_for,
        "estimated": eta,
        "discipline": "No recommendation until real data exists — the gate never fires on assumptions.",
    }


def chief_strategist() -> dict[str, Any]:
    """Phase 25 — single structured decision card built entirely from the
    intelligence the platform already computed. Probabilities, never certainty."""
    L = _layers()
    if not L:
        return {"ready": False, **_status_brief()}
    sig = state.signal or {}
    dec = state.decision or {}
    intel = L.get("intelligence") or {}
    fut = L.get("future") or {}
    cap = L.get("capital_protection") or {}
    wr = fut.get("war_room") or {}
    strike = state.intelligence.get("strike") or {}
    ks = state.kill_switch or {}
    ex = intel.get("expansion") or {}
    it = intel.get("institutional_thoughts") or {}

    # market view
    gbias = (L.get("global_context") or {}).get("bias")
    tdir = (L.get("trend") or {}).get("direction")
    view = ("BULLISH" if (tdir == "BULL" or gbias == "BULLISH")
            else "BEARISH" if (tdir == "BEAR" or gbias == "BEARISH") else "NEUTRAL")
    conf = int(sig.get("dynamic_confidence") or sig.get("confidence") or 0)

    # risk view — kill switch overrides everything
    if ks.get("active"):
        risk = "DANGER"
    else:
        cat = (cap.get("category") or "").upper()
        risk = ("DANGER" if cat in ("HIGH", "DANGER", "EXTREME")
                else "MODERATE" if cat in ("MODERATE", "MEDIUM", "ELEVATED") else "SAFE")

    best_trade = {
        "is_trade": bool(dec.get("is_trade")),
        "strike": strike.get("strike"), "type": strike.get("type"),
        "premium": strike.get("premium_entry"),
        "entry": dec.get("entry"), "stop": dec.get("stop_loss"),
        "targets": [dec.get("target1"), dec.get("target2"), dec.get("target3")],
    }

    return {
        "ready": True,
        "market_view": view,
        "confidence": conf,
        "market_dna": _market_dna(),
        "best_trade": best_trade,
        "probability_ladder": dec.get("probability_ladder"),
        "entry_zone": dec.get("entry_zone"),
        "premium_forecast": dec.get("premium_forecast"),
        "confidence_breakdown": dec.get("confidence_breakdown"),
        "options_professor": dec.get("options_professor"),
        "simulator": state.simulator or {},
        "premium_expansion": {
            "class": ex.get("class"), "expected_move": ex.get("expected_move"),
            "runner_probability": ex.get("runner_probability"),
        },
        "institutional_view": {
            "dominance": wr.get("dominance"),
            "trapped": wr.get("trapped"),
            "likely": [f"{t['behaviour']} ({t['confidence']}%)" for t in it.get("likely", [])[:3]],
            "buyer_strength": wr.get("buyer_strength"),
            "seller_strength": wr.get("seller_strength"),
        },
        "risk_view": risk,
        "kill_switch": {"active": bool(ks.get("active")),
                        "reasons": ks.get("reasons", [])},
        "final_action": dec.get("primary_action") or dec.get("action") or "WAIT",
        "reason": dec.get("reason", ""),
        "decision_intelligence": dec.get("intelligence_synthesis"),
        "execution_gate": dec.get("execution_gate"),
        "signal_maturity": dec.get("signal_maturity"),
        "evolution": _evolution_summary(),
        "questions": [{"q": q, **answer(q)} for q in CHIEF_QUESTIONS],
        "disclaimer": "Probabilities, not certainty. Decision-support only — never places orders.",
    }


def answer(question: str) -> dict[str, Any]:
    q = (question or "").lower().strip()
    if not q:
        return {"answer": "Ask me about direction, a level, runners, premium, "
                          "institutions, or where to enter/exit.", "points": [], "confidence": 0}
    L = _layers()
    sig = state.signal or {}
    dec = state.decision or {}
    intel = L.get("intelligence") or {}
    fut = L.get("future") or {}
    cap = L.get("capital_protection") or {}
    conf = int(sig.get("dynamic_confidence") or sig.get("confidence") or 0)
    spot = float(state.spot.get("ltp") or 0)
    sym = state.symbol

    # ---- intent: system self-improvement / evolution (works without live data) ----
    if any(w in q for w in ("improve itself", "system improve", "evolve", "evolution",
                            "self-tun", "self tun", "nightly audit")):
        from . import evolution
        nl = evolution.last_nightly()
        recs = nl.get("recommendations") or []
        if not recs and not nl.get("nightly"):
            return {"answer": "No nightly audit has run yet — it runs automatically at 23:59 IST "
                              "(or trigger it from the Evolution Center). It then recommends weight, "
                              "calibration and guard changes for human approval.",
                    "points": [], "confidence": 30}
        return {"answer": f"System grade {nl.get('system_grade','—')}. Top improvements "
                          "(advisory, never auto-applied):",
                "points": [f"{r['priority']}. {r['title']} — gain {r['expected_gain']}, impact {r['impact']}"
                           for r in recs[:5]],
                "confidence": 65}

    if not L:
        sb = _status_brief()
        st = sb["ai_status"]
        _icon = {"done": "✓", "loading": "⟳", "pending": "○"}
        return {"answer": f"No live analysis yet — {sb['reason']}",
                "points": [
                    f"Broker: {st['broker']} · Market: {st['market']} ({st['ist_time']} IST) · Data: {st['data_quality']}",
                    f"Next: {sb['next_action']}",
                    "Pipeline: " + " · ".join(f"{_icon[p['state']]} {p['step']}" for p in sb["pipeline"]),
                    f"Waiting for: {', '.join(sb['waiting_for'])}" if sb["waiting_for"] else "All inputs present",
                    f"ETA: {sb['estimated']}",
                    sb["discipline"],
                ], "confidence": 0}

    points: list[str] = []
    level = _num(q)

    # ---- intent: break / cross / reach a level ----
    if level and any(w in q for w in ("break", "cross", "above", "below", "reach", "hit", "touch")):
        struct = L.get("structure", {})
        em = (intel.get("expansion") or {}).get("expected_move") or 0
        dist = abs(level - spot)
        adx = float(L.get("trend", {}).get("adx") or 0)
        # probability the level is reached ~ expected move vs distance, trend-adjusted
        base = 90 if (em and dist <= em * 0.6) else 60 if (em and dist <= em) else 35 if (em and dist <= em * 1.6) else 18
        base += min(max(adx - 18, 0) * 1.2, 12)
        if (level > spot and L.get("trend", {}).get("direction") == "BULL") or \
           (level < spot and L.get("trend", {}).get("direction") == "BEAR"):
            base += 8
        base = int(max(5, min(92, base)))
        side = "above" if level > spot else "below"
        points = [f"Spot {sym} ~{spot:,.0f}; {level:,.0f} is {dist:,.0f} pts {side}.",
                  f"Expected move ≈ {em:,.0f} pts · ADX {adx:.0f} · regime {L.get('regime',{}).get('regime','—').replace('_',' ').lower()}.",
                  f"Resistance {struct.get('resistance')} · support {struct.get('support')}."]
        return {"answer": f"~{base}% probability {level:,.0f} is reached in this session — "
                          "needs a volume-backed move; not a certainty.",
                "points": points, "confidence": base}

    # ---- intent: premium expansion / decay (checked before generic "expand") ----
    if "premium" in q:
        ex = intel.get("expansion") or {}
        cap = L.get("capital_protection") or {}
        return {"answer": f"Premium expansion potential: {ex.get('class','—')} "
                          f"(runner {ex.get('runner_probability','—')}%). Decay risk — theta "
                          f"{cap.get('theta_risk','—')}, IV-crush {cap.get('iv_crush_risk','—')}.",
                "points": [f"Expected move ≈ {ex.get('expected_move','—')} pts.",
                           f"Capital risk: {cap.get('category','—')} ({cap.get('capital_risk','—')})."],
                "confidence": int(ex.get("runner_probability") or 0)}

    # ---- intent: runner / how far / expansion ----
    if any(w in q for w in ("runner", "how far", "expand", "explosive", "big move")):
        ex = intel.get("expansion") or {}
        an = intel.get("market_animal") or {}
        return {"answer": f"Runner probability ~{ex.get('runner_probability','—')}% · classified "
                          f"{an.get('animal','—')} ({ex.get('class','—')}), expected move "
                          f"≈ {ex.get('expected_move','—')} pts. Probabilistic, not guaranteed.",
                "points": [f"Lifespan: {an.get('lifespan','—')}.",
                           f"Next evolution: {an.get('next_evolution','—')} ({an.get('next_evolution_prob','—')}%).",
                           f"Momentum strength {intel.get('summary',{}).get('move_type','—')}."],
                "confidence": int(ex.get("runner_probability") or 0)}

    # ---- intent: institutions ----
    if "institution" in q or "smart money" in q or "trapped" in q or "fii" in q or "dii" in q:
        it = intel.get("institutional_thoughts") or {}
        wr = fut.get("war_room") or {}
        likely = ", ".join(f"{t['behaviour']} ({t['confidence']}%)" for t in it.get("likely", [])[:3])
        return {"answer": f"Institutions likely: {likely or 'no clear footprint'}. "
                          f"Trapped: {wr.get('trapped','—')}.",
                "points": [f"Dominance: {wr.get('dominance','—')} (buyers {wr.get('buyer_strength','—')} / sellers {wr.get('seller_strength','—')}).",
                           f"Not yet: {', '.join(it.get('not_yet', [])) or '—'}.",
                           f"PCR {wr.get('pcr','—')} · delta imbalance {wr.get('delta_imbalance','—')}."],
                "confidence": 70}

    # ---- intent: where to enter ----
    if "enter" in q or "entry" in q or "buy" in q or "trade now" in q:
        strike = state.intelligence.get("strike") or {}
        if dec.get("is_trade"):
            return {"answer": f"{dec.get('action')} — entry {dec.get('entry')}, stop {dec.get('stop_loss')}, "
                              f"targets {dec.get('target1')}/{dec.get('target2')}/{dec.get('target3')}"
                              + (f"; strike {strike.get('strike')} {strike.get('type')} ~{strike.get('premium_entry')}." if strike else "."),
                    "points": [f"Confidence {sig.get('dynamic_confidence', sig.get('confidence','—'))}% · grade {sig.get('grade','—')}.",
                               f"Reward:risk {sig.get('reward_risk','—')}."],
                    "confidence": int(sig.get("dynamic_confidence") or sig.get("confidence") or 0)}
        return {"answer": f"No entry right now — {dec.get('reason','conditions not aligned')}. "
                          "Best action: WAIT.", "points": [], "confidence": 30}

    # ---- intent: exit ----
    if "exit" in q or "book" in q or "sell" in q or "hold" in q:
        ex = state.exit_intel or {}
        if ex.get("active"):
            return {"answer": f"{ex.get('recommended_action')} — {ex.get('reason')}. "
                              f"Exit score {ex.get('exit_score')}%.",
                    "points": [f"Next step: {(ex.get('partial_plan') or {}).get('action','—')}.",
                               f"Reversal now/@T1/@T2: {(ex.get('reversal_probability') or {}).get('current','—')}/"
                               f"{(ex.get('reversal_probability') or {}).get('near_t1','—')}/"
                               f"{(ex.get('reversal_probability') or {}).get('near_t2','—')}%."],
                    "confidence": int(ex.get("exit_confidence") or 0)}
        return {"answer": "No active trade to manage right now.", "points": [], "confidence": 0}

    # ---- intent: direction / what's next ----
    if any(w in q for w in ("direction", "bull", "bear", "next", "scenario", "what now", "outlook")):
        sc = fut.get("scenarios") or {}
        nm = (fut.get("next_move") or {}).get("30m") or {}
        return {"answer": f"Scenarios — Bullish {sc.get('bullish',{}).get('probability','—')}% · "
                          f"Range {sc.get('range',{}).get('probability','—')}% · "
                          f"Bearish {sc.get('bearish',{}).get('probability','—')}%. "
                          f"Primary: {str(sc.get('primary','—')).upper()}.",
                "points": [f"Next 30m: bull {nm.get('bullish','—')}% / range {nm.get('range','—')}% / bear {nm.get('bearish','—')}%.",
                           f"Final action: {dec.get('primary_action','—')} — {dec.get('reason','')}."],
                "confidence": int(sc.get("bullish", {}).get("confidence") or 50)}

    # ---- intent: strike to buy / avoid ----
    if "strike" in q:
        strike = state.intelligence.get("strike") or {}
        strikes = state.intelligence.get("strikes") or []
        if "avoid" in q:
            avoid = [s for s in strikes if (s.get("score") or 0) < 40]
            names = ", ".join(f"{s.get('strike')} {s.get('type')}" for s in avoid[:3]) or "deep OTM / illiquid strikes"
            return {"answer": f"Avoid {names} — low score / poor liquidity or far from spot.",
                    "points": [f"Prefer the recommended {strike.get('strike','—')} {strike.get('type','—')}."],
                    "confidence": 60}
        if strike:
            return {"answer": f"Best strike: {strike.get('strike')} {strike.get('type')} "
                              f"@ ~{strike.get('premium_entry','—')} (score {strike.get('score','—')}).",
                    "points": [f"SL ~{strike.get('premium_sl','—')} · targets {strike.get('premium_targets','—')}.",
                               f"Liquidity/OI rationale: {strike.get('reason','—')}."],
                    "confidence": int(strike.get("score") or 0)}
        return {"answer": "No strike recommended right now — WAIT for a valid setup.", "points": [], "confidence": 25}

    # ---- intent: highest-probability / safest / most-aggressive trade ----
    if any(w in q for w in ("highest probability", "best trade", "safest", "aggressive", "explosive trade", "most explosive")):
        an = intel.get("market_animal") or {}
        ex = intel.get("expansion") or {}
        if "safest" in q:
            return {"answer": f"Safest stance: {dec.get('primary_action','WAIT')} — {dec.get('reason','wait for confluence')}. "
                              f"Risk view: {cap.get('category','—')}.",
                    "points": ["Take trades only at grade A/B with confirmed structure.",
                               f"Capital risk: {cap.get('capital_risk','—')}."],
                    "confidence": int(sig.get("dynamic_confidence") or sig.get("confidence") or 0)}
        if any(w in q for w in ("aggressive", "explosive")):
            return {"answer": f"Most aggressive read: {an.get('animal','—')} with runner prob "
                              f"{ex.get('runner_probability','—')}% (expected ≈ {ex.get('expected_move','—')} pts). "
                              "Higher reward, higher risk — size down.",
                    "points": ["Only if structure + institutions align; respect the kill switch."],
                    "confidence": int(ex.get("runner_probability") or 0)}
        # highest-probability / best trade
        if dec.get("is_trade"):
            return {"answer": f"Highest-probability trade now: {dec.get('action')} "
                              f"@ {dec.get('entry')}, stop {dec.get('stop_loss')}, "
                              f"targets {dec.get('target1')}/{dec.get('target2')}/{dec.get('target3')}.",
                    "points": [f"Confidence {sig.get('dynamic_confidence', sig.get('confidence','—'))}% · grade {sig.get('grade','—')}.",
                               f"Reward:risk {sig.get('reward_risk','—')}."],
                    "confidence": int(sig.get("dynamic_confidence") or sig.get("confidence") or 0)}
        return {"answer": f"No high-probability trade right now — {dec.get('reason','conditions not aligned')}. Best action: WAIT.",
                "points": [], "confidence": 25}

    # ---- intent: why this confidence / why not higher ----
    if "why" in q and any(w in q for w in ("confidence", "90", "not", "%", "conf")):
        cal = (intel.get("calibration") or {})
        confirms = sig.get("confirmations") or []
        vetoes = sig.get("vetoes") or sig.get("warnings") or []
        return {"answer": f"Confidence {conf}% reflects measured confluence, not certainty. "
                          f"It isn't 90% because some layers are unconfirmed or calibration caps it.",
                "points": [f"Confirmed: {', '.join(confirms[:4]) or '—'}.",
                           f"Holding back: {', '.join(vetoes[:4]) or 'no hard vetoes, but not all layers aligned'}.",
                           f"Calibration: {cal.get('summary','measured vs realised win rate')}."],
                "confidence": conf}

    # ---- intent: what could invalidate / go wrong ----
    if any(w in q for w in ("invalidate", "go wrong", "fail", "risk of", "wrong")):
        vetoes = sig.get("vetoes") or sig.get("warnings") or []
        nz = L.get("no_trade_zone") or {}
        traps = L.get("traps") or {}
        ks = state.kill_switch or {}
        pts = []
        if ks.get("active"): pts.append(f"Kill switch ACTIVE: {'; '.join(ks.get('reasons', []))}.")
        if nz.get("active"): pts.append(f"No-trade zone: {nz.get('reason','—')}.")
        if traps.get("detected"): pts.append(f"Trap risk: {traps.get('type','—')}.")
        pts.append(f"Capital risk: {cap.get('category','—')} ({cap.get('capital_risk','—')}).")
        return {"answer": f"This trade is invalidated if structure breaks or confluence drops. "
                          f"Watch: {', '.join(vetoes[:3]) or 'momentum loss, reversal at key level'}.",
                "points": pts, "confidence": 60}

    # ---- intent: re-entry ----
    if "re-enter" in q or "reenter" in q or "re enter" in q or "re-entry" in q:
        ex = state.exit_intel or {}
        re = ex.get("re_entry") or {}
        if re:
            return {"answer": f"Re-entry: {re.get('plan', re.get('action','wait for a fresh confirmed setup'))}.",
                    "points": [f"Conditions: {re.get('condition','structure reclaim + momentum')}."],
                    "confidence": int(re.get("confidence") or 40)}
        return {"answer": "Re-enter only on a fresh confirmed setup (structure reclaim + momentum + confluence). "
                          "Don't average a losing trade.", "points": [], "confidence": 40}

    # ---- intent: market DNA / similar setups ----
    if "dna" in q or "similar" in q or "historical" in q or "in the past" in q:
        dna = _market_dna()
        return {"answer": f"Market DNA (regime proxy): {dna['matches']} similar {dna['regime'] or 'regime'} "
                          f"samples, historical win rate {dna['historical_win_rate'] or '—'}% "
                          f"(match {dna['match_pct']}%).",
                "points": [dna["note"], "Full historical-similarity engine is Phase 20."],
                "confidence": dna["match_pct"]}

    # ---- intent: should I wait ----
    if "wait" in q or "should i" in q:
        return {"answer": f"{dec.get('primary_action','WAIT')} — {dec.get('reason','conditions not fully aligned')}.",
                "points": [f"Confidence {conf}% · risk {cap.get('category','—')}.",
                           f"FORCE WAIT active: {bool((state.kill_switch or {}).get('active'))}."],
                "confidence": conf}

    # ---- intent: where will price go / market path / next level ----
    if any(w in q for w in ("where will price", "next level", "market path", "what next",
                            "next move", "where is it going", "next target", "touch")):
        mp = dec.get("market_path") or {}
        if mp.get("ready"):
            pts = []
            if mp.get("next_touch"):
                nt = mp["next_touch"]
                pts.append(f"Next touch: {nt['name']} {nt['level']} (~{nt['touch_prob']}%, ETA {nt['eta_min']}m)")
            pts += [f"Target: {t['name']} {t['level']} ({t['prob']}%)" for t in (mp.get("targets") or [])[:3]]
            if mp.get("failure_level"):
                pts.append(f"Cancels if {mp['failure_level']['level']} breaks")
            return {"answer": mp.get("summary", "—"), "points": pts,
                    "confidence": int((mp.get("scenarios") or {}).get("bullish", {}).get("probability") or 0)
                                  if mp.get("bias") == "BULLISH" else
                                  int((mp.get("scenarios") or {}).get("bearish", {}).get("probability") or 0)}

    # ---- intent: candle / path projection ----
    if any(w in q for w in ("projection", "ghost candle", "next candle", "projected", "path",
                            "where will price", "expected candle")):
        cp = dec.get("candle_projection") or {}
        if not cp.get("ready"):
            return {"answer": "No directional projection yet — needs a trending setup.", "points": [], "confidence": 20}
        paths = cp.get("paths", {})
        last = (cp.get("candles") or [{}])[-1].get("expected", {})
        return {"answer": f"Projected {cp['direction']} path → ~{last.get('close')} "
                          f"(expected move {cp['expected_move']} pts, forward-only, no repaint).",
                "points": [f"Primary {paths.get('primary',{}).get('probability')}% → {paths.get('primary',{}).get('target')}",
                           f"Failure {paths.get('failure',{}).get('probability')}% → {paths.get('failure',{}).get('target')}",
                           f"Range {paths.get('alternative',{}).get('probability')}%"],
                "confidence": int(paths.get("primary", {}).get("probability") or 0)}

    # ---- intent: confidence evolution / why confidence changed ----
    if any(w in q for w in ("confidence evolution", "confidence change", "why confidence",
                            "confidence going", "confidence timeline", "confidence up", "confidence down")):
        ce = dec.get("confidence_evolution") or {}
        if not ce.get("ready"):
            return {"answer": "No confidence history yet — needs a few live cycles.", "points": [], "confidence": 20}
        dtxt = "" if ce["delta"] == 0 else f", {ce['delta']:+d}"
        return {"answer": f"Confidence {ce['current']}% ({ce['direction']}{dtxt}). {ce['reason']}.",
                "points": [f"Range this session: {ce['low']}–{ce['high']}%",
                           f"Responsible layer: {ce.get('responsible_layer') or '—'}",
                           f"Samples: {ce['samples']}"],
                "confidence": ce["current"]}

    # ---- intent: execution gate / can I take this trade / mandatory conditions ----
    if any(w in q for w in ("execution gate", "can i trade", "can i take", "gate", "mandatory",
                            "cleared to", "allowed to trade", "final gate")):
        eg = dec.get("execution_gate") or {}
        if not eg.get("ready"):
            return {"answer": "No execution gate reading yet — needs a live AI cycle.", "points": [], "confidence": 20}
        if eg.get("gate_passed"):
            return {"answer": f"Gate PASSED → {eg['final_decision']} ({eg['passed_count']}/{eg['total']} conditions).",
                    "points": [f"Waiting on: {', '.join(eg.get('waiting_on', [])) or 'none'}"],
                    "confidence": 70}
        return {"answer": f"Gate verdict: {eg['final_decision']} — mandatory conditions not met.",
                "points": (eg.get("blocking_reasons") or ["Confluence not aligned"])[:5],
                "confidence": 40}

    # ---- intent: what's missing / why no trade / entry checklist ----
    if any(w in q for w in ("what is missing", "what's missing", "why no trade", "why not",
                            "checklist", "what is needed", "what needs", "waiting for what",
                            "fire score")):
        ec = dec.get("entry_checklist") or {}
        if not ec.get("ready"):
            return {"answer": "No checklist yet — needs a live AI cycle.", "points": [], "confidence": 20}
        if ec.get("is_trade"):
            pts = [f"{c['item']}: {c['status']}" for c in ec.get("checklist", []) if c["status"] == "PASS"][:6]
            return {"answer": f"Trade confirmed — fire score {ec['fire_score']}/100 ({ec['fire_band']}), "
                              f"{ec['passed']}/{ec['total']} confirmations.", "points": pts,
                    "confidence": ec["fire_score"]}
        return {"answer": f"No trade — fire score {ec['fire_score']}/100 ({ec['fire_band']}). Why:",
                "points": ec.get("why_not", [])[:6], "confidence": ec["fire_score"]}

    # ---- intent: signal maturity / entry trigger / when to enter ----
    if any(w in q for w in ("maturity", "entry trigger", "when to enter", "when should i enter",
                            "is it ready", "fire now", "armed", "entry window", "signal age",
                            "late entry")):
        sm = dec.get("signal_maturity") or {}
        if not sm.get("ready"):
            return {"answer": "No maturity reading yet — needs a live AI cycle.", "points": [], "confidence": 20}
        et = sm.get("entry_trigger", {})
        return {"answer": f"{et.get('status')} — maturity {sm.get('maturity_score')}/100 "
                          f"({sm.get('stage')}), decay {sm.get('decay')}.",
                "points": [f"Signal age {sm.get('signal_age_sec')}s · stability {sm.get('stability')} · "
                           f"confirmations {sm.get('confirmation_count')}/{sm.get('confirmation_total')}",
                           f"Entry window left: {et.get('window_remaining_sec')}s · late-entry risk {et.get('late_entry_risk')}",
                           f"BUY allowed: {sm.get('buy_allowed')} (threshold {sm.get('threshold')})"
                           + (" · Expiry precision mode" if sm.get('monthly_expiry_mode') else "")],
                "confidence": int(sm.get("maturity_score") or 0)}

    # ---- intent: trade quality / should I trade / institutional decision ----
    if any(w in q for w in ("trade quality", "should i trade", "trade score", "conviction",
                            "institutional decision", "final decision", "devil", "quality score",
                            "is this a good trade", "elite")):
        di = dec.get("intelligence_synthesis") or {}
        if not di.get("ready"):
            return {"answer": "No synthesised decision yet — needs a live AI cycle.", "points": [], "confidence": 20}
        tq = di.get("trade_quality", {}); gov = di.get("governance", {})
        return {"answer": f"{di.get('final_decision')} — {tq.get('grade')} "
                          f"(quality {tq.get('score')}/1000, conviction {di.get('conviction')}%).",
                "points": [f"Strongest for: {gov.get('strongest_bull')}",
                           f"Strongest against: {gov.get('strongest_bear')}",
                           f"Largest risk: {gov.get('largest_risk')}",
                           f"Devil's advocate: {gov.get('devils_advocate')}"],
                "confidence": int(di.get("conviction") or 0)}

    # ---- intent: target / stop probability ladder ----
    if any(w in q for w in ("probability ladder", "target probability", "chance of target",
                            "reach target", "odds of", "probability of t", "hit target", "hit stop")):
        lad = dec.get("probability_ladder") or {}
        if not lad.get("ready"):
            return {"answer": "No probability ladder yet — needs an active setup with entry, "
                              "targets and an expected move.", "points": [], "confidence": 20}
        pts = [f"{r['level']} @ {r['price']}: {r['probability']:.0f}% ({r['band']})" for r in lad.get("rungs", [])]
        sl = lad.get("stop_loss")
        if sl:
            pts.append(f"Stop @ {sl['price']}: {sl['probability']:.0f}% ({sl['band']}) — hit first")
        return {"answer": "Probability ladder (touch odds, not certainty):",
                "points": pts, "confidence": int(lad.get("edge") or 0)}

    # ---- intent: options professor — why CE/PE/strike/premium (plain language) ----
    if any(w in q for w in ("why ce", "why pe", "why call", "why put", "why this strike",
                            "why this premium", "explain the trade", "options professor",
                            "why strike", "teach me")):
        prof = dec.get("options_professor") or {}
        ex = prof.get("explanations") or {}
        if not ex:
            return {"answer": "No trade to explain yet — wait for a setup.", "points": [], "confidence": 20}
        order = ["why_ce", "why_pe", "why_strike", "why_premium", "why_stop", "why_target"]
        pts = [ex[k] for k in order if ex.get(k)]
        return {"answer": f"Options Professor ({prof.get('side','—')}):", "points": pts[:5], "confidence": 60}

    # ---- intent: today / tomorrow scenario simulation ----
    if any(w in q for w in ("tomorrow", "today scenario", "gap up", "gap down", "simulate",
                            "what if", "scenarios today", "most likely")):
        sim = state.simulator or {}
        if not sim.get("ready"):
            return {"answer": "Simulator has no live data yet.", "points": [], "confidence": 20}
        ml = sim.get("most_likely") or {}
        pts = [f"{s['scenario']}: {s['probability']:.0f}% · move ≈{s['expected_move']} · {s['risk']} risk"
               for s in sim.get("today", [])]
        pts.append(f"Tomorrow bias: {sim.get('tomorrow_bias')}")
        return {"answer": f"Most likely today: {ml.get('scenario','—')} ({ml.get('probability','—')}%). "
                          "Scenarios (probabilities, not certainty):",
                "points": pts, "confidence": int(ml.get("probability") or 40)}

    # ---- intent: project status / roadmap / what's completed / what next ----
    if any(w in q for w in ("roadmap", "what is completed", "what's completed", "what is pending",
                            "project status", "progress", "build next", "what next",
                            "what should we build", "completed phases", "என்ன வேலை")):
        from . import evolution
        rm = evolution.roadmap()
        done = [i for i in rm["items"] if i["status"] == "COMPLETED"]
        pend = [i for i in rm["items"] if i["status"] == "PENDING"]
        blk = [i for i in rm["items"] if i["status"] == "BLOCKED"]
        return {"answer": f"System {rm['completion_pct']:.0f}% complete — {rm['completed']} phases done, "
                          f"{rm['pending']} pending, {rm['blocked']} blocked. "
                          f"Next recommended: {rm['next_recommended']}.",
                "points": [f"Completed: {', '.join(i['phase'] for i in done)}",
                           f"Pending: {', '.join(i['name'] for i in pend) or '—'}",
                           f"Blocked: {', '.join(i['name'] for i in blk) or '—'}",
                           rm["note"]],
                "confidence": 80}

    # ---- intent: explain the confidence number (per-engine contribution) ----
    if any(w in q for w in ("explain confidence", "confidence breakdown", "why this confidence",
                            "what makes confidence", "confidence contribution")):
        cb = dec.get("confidence_breakdown") or {}
        if not cb.get("ready"):
            return {"answer": "No directional signal to break down yet.", "points": [], "confidence": 20}
        pts = [f"{c['engine']}: {'+' if c['contribution'] >= 0 else ''}{c['contribution']} (score {c['score']:.0f})"
               for c in cb.get("components", [])]
        return {"answer": f"Confidence {cb.get('confidence')}% for {cb.get('direction')} — engine contributions:",
                "points": pts, "confidence": int(cb.get("confidence") or 0)}

    # ---- intent: research lab / self-diagnosis / system weaknesses ----
    if any(w in q for w in ("research lab", "self-diagnos", "self diagnos", "weakness",
                            "system health check", "bottleneck", "diagnose", "what is wrong")):
        from . import research_lab
        rl = research_lab.report()
        c = rl["counts"]
        top = [f"[{f['severity']}] {f['finding']}" for f in rl["findings"]
               if f["severity"] in ("CRITICAL", "HIGH", "MEDIUM")][:5]
        return {"answer": f"Research Lab self-scan — {c['HIGH']} high, {c['MEDIUM']} medium findings:",
                "points": top or ["No significant issues detected."], "confidence": 70}

    # ---- intent: how should the system improve / evolution / self-tuning ----
    if any(w in q for w in ("improve itself", "system improve", "evolve", "evolution",
                            "self-tun", "self tun", "upgrade", "get better", "nightly audit")):
        from . import evolution
        nl = evolution.last_nightly()
        recs = nl.get("recommendations") or []
        if not recs and not nl.get("nightly"):
            return {"answer": "No nightly audit has run yet — it runs automatically at 23:59 IST "
                              "(or trigger it from the Evolution Center). It will then recommend "
                              "weight, calibration and guard changes for human approval.",
                    "points": [], "confidence": 30}
        return {"answer": f"System grade {nl.get('system_grade','—')}. Top improvements (advisory, "
                          "never auto-applied):",
                "points": [f"{r['priority']}. {r['title']} — gain {r['expected_gain']}, impact {r['impact']}"
                           for r in recs[:5]],
                "confidence": 65}

    # ---- fallback: summarize what the brain currently sees ----
    s = intel.get("summary") or {}
    return {"answer": f"{s.get('whats_happening','—')}. Action: {dec.get('primary_action','WAIT')} "
                      f"({dec.get('reason','')}).",
            "points": [f"Move: {s.get('move_type','—')} · clarity {s.get('clarity','—')}.",
                       f"How far: {s.get('how_far','—')} · risks: {s.get('what_fails','—')}."],
            "confidence": 50}
