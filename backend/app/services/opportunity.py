"""V26 — AI Market Opportunity Engine (staged, rate-limit-safe).

Level 1 (cheap)  : the existing scanner pass — batch quotes across indices +
                   watchlist, momentum/breakout ranked. Zero extra calls here.
Level 2 (deep)   : option chains fetched ONLY for the few strongest directional
                   candidates, spaced ≥3s apart (broker option-chain limit).
                   The connected instrument reuses its live chain — no refetch.
Level 3          : the existing Universal Strike Engine on the selected
                   instrument (click a card → switch instrument).

Nothing fabricated: candidates whose chain is unavailable are published as
momentum-only with premium fields None ("Unavailable" in the UI).
"""
from __future__ import annotations

import asyncio
import logging
import math
import time
from typing import Any

from ..broker.instruments import get_instrument
from ..core.state import state
from ..engines import index_analytics, strike_selector
from . import alerts

log = logging.getLogger(__name__)

DEEP_TOP = 2          # chains fetched per cycle, max (rate budget: ~2 extra calls/min)
CHAIN_SPACING = 3.0   # seconds BEFORE each broker call (expiry list AND chain)
ALERT_SCORE = 85.0
_last_alert: dict[str, float] = {}

board: dict[str, Any] = {"ready": False, "note": "First scan pending."}

# V40.3 — board feedback loop: each published candidate is re-checked ~30 min
# later against the SAME scanner quotes (zero extra calls). Outcome = was the
# direction right? Aggregated by AI-score bucket so the score itself gets graded.
_OUTCOME_SEC = 1800
_pending: list[dict[str, Any]] = []
score_quality: dict[str, dict[str, int]] = {}


def _bucket(score: float) -> str:
    return "80+" if score >= 80 else "60-79" if score >= 60 else "<60"


def _feedback(scanner_results: list[dict]) -> dict[str, Any]:
    now = time.time()
    ltps = {r["symbol"]: float(r.get("ltp") or 0) for r in (scanner_results or [])}
    for p in list(_pending):
        if now - p["ts"] < _OUTCOME_SEC:
            continue
        cur = ltps.get(p["symbol"])
        _pending.remove(p)
        if not cur or not p.get("ltp"):
            continue
        correct = (cur > p["ltp"]) == (p["bias"] == "BULL")
        q = score_quality.setdefault(_bucket(p["ai_score"]), {"n": 0, "correct": 0})
        q["n"] += 1
        q["correct"] += 1 if correct else 0
    return {b: {"n": q["n"], "direction_hit_pct": round(q["correct"] / q["n"] * 100, 0) if q["n"] else None}
            for b, q in sorted(score_quality.items())}


async def _deep(client, cand: dict) -> None:
    """Level 2 — attach best-strike detail to one candidate (in place)."""
    sym = cand["symbol"]
    inst = get_instrument(sym)
    if inst.security_id == 0:
        cand["detail"] = "id-unresolved"
        return
    # reuse the live chain for the connected instrument — zero extra calls
    if sym == state.symbol and (state.analytics or {}).get("chain"):
        analytics = state.analytics
    else:
        # NEVER compete with the live feed: defer politely when the broker
        # budget is tight, and space out BEFORE every extra call we make
        from ..broker.dhan import DhanClient
        if DhanClient.stats().get("cooldown_active"):
            cand["detail"] = "rate-budget (deferred to next cycle)"
            return
        await asyncio.sleep(CHAIN_SPACING)
        expiries = await client.get_expiries(inst)
        if not expiries:
            cand["detail"] = "no-options"
            return
        if DhanClient.stats().get("cooldown_active"):
            cand["detail"] = "rate-budget (deferred to next cycle)"
            return
        await asyncio.sleep(CHAIN_SPACING)
        chain = await client.get_option_chain(inst, expiries[0])
        analytics = index_analytics.analyze_chain(
            chain, cand["ltp"], expiries[0], inst.strike_step)
    rows = analytics.get("chain") or []
    if not rows:
        cand["detail"] = "no-chain"
        return
    cand["options_rows"] = len(rows)
    direction = "BULL" if cand["bias"] == "BULL" else "BEAR"
    iv = float(((analytics.get("greeks") or {}).get("ce") or {}).get("iv") or 0)
    spot = float(cand["ltp"])
    em = spot * iv * math.sqrt(1 / 365.0) if iv > 0 else spot * 0.004
    s = 1 if direction == "BULL" else -1
    levels = {"stop_loss": round(spot - s * 0.5 * em, 2),
              "target1": round(spot + s * 0.5 * em, 2),
              "target2": round(spot + s * 1.0 * em, 2),
              "target3": round(spot + s * 1.5 * em, 2)}
    picks = strike_selector.select_top(rows, direction, spot,
                                       analytics.get("expiry", ""), levels, n=1)
    if not picks:
        cand["detail"] = "no-strike"
        return
    p = picks[0]
    # V40 SANITY GATE — the published premium must be consistent with the
    # chain's own put-call parity and the strike must sit near spot. A chain
    # that fails this belongs to the wrong expiry/underlying (TATA STEEL
    # 190 CE shown ₹22.35 vs real ₹4.75) — publish momentum-only instead.
    try:
        _stk = float(p["strike"])
        if abs(_stk - spot) > spot * 0.15:
            raise ValueError(f"strike {_stk} too far from spot {spot}")
        _row = next((r for r in rows if float(r.get("strike", 0)) == _stk), None)
        _ce = float((_row or {}).get("ce_ltp") or 0)
        _pe_l = float((_row or {}).get("pe_ltp") or 0)
        if _ce > 0 and _pe_l > 0:
            _parity = (_ce - _pe_l) - (spot - _stk)
            if abs(_parity) > max(spot * 0.02, 2.0):
                raise ValueError(f"parity off by {_parity:.2f} (CE {_ce} PE {_pe_l})")
    except ValueError as ve:
        log.warning("opportunity sanity FAILED for %s %s %s: %s — momentum-only",
                    sym, p.get("strike"), p.get("type"), ve)
        cand["detail"] = "sanity-failed (chain/underlying mismatch)"
        return
    cand.update({
        "strike": p["strike"], "type": p["type"],
        "premium": p["premium_entry"], "premium_sl": p["premium_stop_loss"],
        "premium_t1": p["premium_target1"],
        "prob_itm": p["prob_itm_pct"], "spread_pct": p["spread_pct"],
        "sel_score": p["selection_score"],
        # blended board score: half momentum (L1), half strike quality (L2)
        "ai_score": round(0.5 * cand["score"] + 0.5 * p["selection_score"], 0),
        "detail": "ok",
    })


async def build_board(client, scanner_results: list[dict]) -> dict[str, Any]:
    """One board pass over the latest Level-1 results."""
    global board
    cands = [dict(r) for r in (scanner_results or []) if r.get("bias") in ("BULL", "BEAR")]
    cands.sort(key=lambda r: r.get("score", 0), reverse=True)
    # balanced deep set: strongest bulls + strongest bears
    bulls = [c for c in cands if c["bias"] == "BULL"][:max(2, DEEP_TOP // 2)]
    bears = [c for c in cands if c["bias"] == "BEAR"][:max(2, DEEP_TOP // 2)]
    deep = (bulls + bears)[:DEEP_TOP]
    options_analysed = 0
    for c in deep:
        try:
            await _deep(client, c)
            options_analysed += int(c.get("options_rows") or 0)
        except Exception as e:                      # one bad candidate never kills the board
            c["detail"] = "chain-error"
            log.info("opportunity deep scan failed for %s: %s", c.get("symbol"), e)
    for c in deep:
        c.setdefault("ai_score", c["score"])        # momentum-only fallback
        c["status"] = "READY" if c["ai_score"] >= ALERT_SCORE else "WATCH"
    ce = sorted([c for c in deep if c["bias"] == "BULL"], key=lambda c: c["ai_score"], reverse=True)[:3]
    pe = sorted([c for c in deep if c["bias"] == "BEAR"], key=lambda c: c["ai_score"], reverse=True)[:3]

    # threshold-only alert (transition + 30-min cooldown per symbol)
    now = time.time()
    for c in ce + pe:
        if c["ai_score"] >= ALERT_SCORE and c.get("detail") == "ok" \
                and now - _last_alert.get(c["symbol"], 0) > 1800:
            _last_alert[c["symbol"]] = now
            await alerts.send("SCANNER",
                              f"NEW OPPORTUNITY — {c['symbol']} {c['strike']:.0f} {c['type']}",
                              f"AI score {c['ai_score']:.0f} · premium ₹{c['premium']} · ITM {c['prob_itm']}%",
                              c["symbol"])

    # V40.3 — settle old candidates, then enrol the new board for future grading
    quality = _feedback(scanner_results)
    _enrolled = {p["symbol"] for p in _pending}
    for c in ce + pe:
        if c["symbol"] not in _enrolled and c.get("ltp"):
            _pending.append({"symbol": c["symbol"], "bias": c["bias"],
                             "ltp": float(c["ltp"]), "ai_score": float(c["ai_score"]),
                             "ts": now})

    board = {
        "ready": True, "ce": ce, "pe": pe,
        "board_quality": {"by_score_bucket": quality,
                          "note": "Direction-hit after ~30 min per published candidate "
                                  "(scanner quotes only). Grades the AI score itself; "
                                  "builds over cycles."},
        "meter": {"scanned": len(scanner_results or []),
                  "directional": len(cands),
                  "deep_scanned": len(deep),
                  "options_analysed": options_analysed},
        "note": "Staged scan: momentum L1 (existing batch quotes) → chains only for "
                f"top {DEEP_TOP} candidates (≥{CHAIN_SPACING:.0f}s apart) → click opens the "
                "full Strike Engine. Premium fields absent ⇒ chain unavailable, never estimated.",
        "ts": now,
    }
    state.opportunities = board
    return board
