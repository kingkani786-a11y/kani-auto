"""Historical Market Memory.

Records rolling snapshots (price, PCR, OI, Greeks, max pain) to Supabase
when configured (building toward the 2-year database) with an in-memory
ring fallback. Also tracks every fired signal to outcome (target1 vs stop)
to compute the historical accuracy fed back into signal grading.
"""
from __future__ import annotations

import logging
import time
from collections import deque
from typing import Any

from .journal import _sb  # reuse the configured Supabase client (or None)

log = logging.getLogger("memory")

_ring: deque[dict] = deque(maxlen=20000)
_tracked: list[dict] = []          # open signal outcomes
# Self-learning store: each outcome carries its context so future signals in
# the same regime are ranked by how that regime actually performed.
_outcomes: deque[dict] = deque(maxlen=200)  # {win, regime, signal, layers}
# Module 5 — per-engine reliability: which engines were PASS at signal time and
# whether the trade then won. {engine: {"n": int, "correct": int}}
_engine_stats: dict[str, dict[str, int]] = {}


def record_snapshot(symbol: str, spot: float, analytics: dict[str, Any]) -> None:
    g = (analytics or {}).get("greeks", {})
    row = {
        "ts": time.strftime("%Y-%m-%d %H:%M:%S"),
        "symbol": symbol,
        "spot": spot,
        "pcr": analytics.get("pcr"),
        "max_pain": analytics.get("max_pain"),
        "call_oi": analytics.get("call_oi"),
        "put_oi": analytics.get("put_oi"),
        "atm_iv": (g.get("ce") or {}).get("iv"),
        "atm_delta_ce": (g.get("ce") or {}).get("delta"),
        "expiry": analytics.get("expiry"),
    }
    _ring.append(row)
    if _sb:
        try:
            _sb.table("market_memory").insert(row).execute()
        except Exception as e:
            log.debug("memory persist failed: %s", e)


def history(symbol: str, limit: int = 500) -> list[dict]:
    if _sb:
        try:
            res = (_sb.table("market_memory").select("*").eq("symbol", symbol)
                   .order("ts", desc=True).limit(limit).execute())
            if res.data:
                return res.data
        except Exception:
            pass
    return [r for r in _ring if r["symbol"] == symbol][-limit:]


# Generated-signal log (for analytics "signals generated" counts & journal).
_generated: deque = deque(maxlen=2000)


def _dedupe_recent(symbol: str, signal: dict) -> bool:
    """True if this exact signal was already logged in the last 10 min — the
    same call repeats every 30s, so log it once per setup, not per cycle."""
    now = time.time()
    for g in reversed(_generated):
        if now - g["ts"] > 600:
            break
        if (g["symbol"] == symbol and g["signal"] == signal.get("signal")
                and abs((g.get("entry") or 0) - (signal.get("entry") or 0)) < 1e-6):
            return True
    return False


# ---- signal outcome tracking -> regime-aware historical accuracy ----
def track_signal(symbol: str, signal: dict[str, Any], regime: str = "",
                 layers: list[str] | None = None, session: str = "",
                 engines_pass: list[str] | None = None,
                 dna: dict | None = None, strike: Any = None,
                 premium_entry: float | None = None,
                 premium_target: float | None = None) -> None:
    if signal.get("signal") in (None, "NO TRADE"):
        return
    conf = float(signal.get("dynamic_confidence") or signal.get("confidence") or 0)
    grade = signal.get("grade", "")
    # Phase 20 — planned premium expansion (from the recommended strike) for DNA
    pexp = None
    if premium_entry and premium_target and premium_entry > 0:
        pexp = round((premium_target - premium_entry) / premium_entry * 100, 1)
    rec = {
        "symbol": symbol,
        "direction": signal["direction"],
        "signal": signal["signal"],
        "regime": regime,
        "session": session,
        "layers": layers or signal.get("confirmations", []),
        "confidence": conf,
        "grade": grade,
        "engines_pass": engines_pass or [],
        "entry": signal["entry"],
        "stop": signal["stop_loss"],
        "target": signal["target1"],
        "dna": dna or {},                 # Phase 20 feature snapshot
        "strike": strike,
        "premium_expansion_pct": pexp,
        "mfe": 0.0, "mae": 0.0,           # V25 §5 — max favorable/adverse excursion (pts)
        "opened": time.time(),
    }
    # log every distinct generated signal once (analytics + journal feed)
    if not _dedupe_recent(symbol, signal):
        _generated.append({"ts": time.time(), "symbol": symbol, "signal": signal["signal"],
                           "direction": signal["direction"], "confidence": conf,
                           "grade": grade, "entry": signal["entry"], "regime": regime})
        _tracked.append(rec)
    del _tracked[:-30]  # cap open positions


def _settle(t: dict, win: bool) -> None:
    # PnL in points: target hit vs stop hit (drift settles count at the level)
    pnl = (t["target"] - t["entry"]) if win else (t["stop"] - t["entry"])
    if t["direction"] == "BEAR":
        pnl = -pnl
    risk = abs(t["entry"] - t["stop"]) or 1.0
    _outcomes.append({"win": 1 if win else 0, "regime": t.get("regime", ""),
                      "session": t.get("session", ""),
                      "signal": t.get("signal", ""), "layers": t.get("layers", []),
                      "entry": t["entry"], "stop": t["stop"], "target": t["target"],
                      "exit": t["target"] if win else t["stop"],
                      "pnl": round(pnl, 2), "r_multiple": round(pnl / risk, 2),
                      "confidence": t.get("confidence", 0), "grade": t.get("grade", ""),
                      "direction": t.get("direction", ""),
                      "dna": t.get("dna", {}), "strike": t.get("strike"),
                      "premium_expansion_pct": t.get("premium_expansion_pct"),
                      "mfe": t.get("mfe", 0.0), "mae": t.get("mae", 0.0),
                      "missed_pts": round(max(0.0, t.get("mfe", 0.0) - (pnl if win else 0)), 1),
                      "opened": t.get("opened", time.time()), "closed": time.time()})
    # Module 5 — attribute the outcome to each engine that was PASS at entry
    for eng in t.get("engines_pass", []):
        s = _engine_stats.setdefault(eng, {"n": 0, "correct": 0})
        s["n"] += 1
        if win:
            s["correct"] += 1
    _tracked.remove(t)
    if _sb:
        # Phase 19 — persist the FULL outcome so learning (accuracy, calibration,
        # Brier, engine reliability) survives restart. Best-effort; never blocks.
        o = _outcomes[-1]
        try:
            _sb.table("signal_outcomes").insert({
                "symbol": t["symbol"], "signal": t["signal"], "regime": t["regime"],
                "session": o["session"], "layers": t["layers"],
                "engines_pass": t.get("engines_pass", []),
                "win": 1 if win else 0, "pnl": o["pnl"], "r_multiple": o["r_multiple"],
                "confidence": o["confidence"], "grade": o["grade"],
                "direction": o["direction"], "entry": o["entry"], "stop": o["stop"],
                "target": o["target"], "exit": o["exit"],
                "dna": o.get("dna", {}), "strike": o.get("strike"),
                "premium_expansion_pct": o.get("premium_expansion_pct"),
                "opened": o["opened"], "closed": o["closed"],
            }).execute()
        except Exception as e:
            log.debug("outcome persist failed: %s", e)


def rehydrate(limit: int = 200) -> dict[str, Any]:
    """Phase 19 — restore self-learning memory from Supabase on startup so the
    system keeps its measured accuracy / calibration / reliability across
    restarts. No-op (returns zeros) when Supabase isn't configured."""
    if not _sb:
        return {"loaded": 0, "source": "memory-only"}
    try:
        res = (_sb.table("signal_outcomes").select("*")
               .order("closed", desc=True).limit(limit).execute())
        rows = list(reversed(res.data or []))  # oldest→newest into the ring
    except Exception as e:
        log.warning("rehydrate failed: %s", e)
        return {"loaded": 0, "source": "error"}

    _outcomes.clear()
    _engine_stats.clear()
    for r in rows:
        win = 1 if r.get("win") else 0
        _outcomes.append({
            "win": win, "regime": r.get("regime", ""), "session": r.get("session", ""),
            "signal": r.get("signal", ""), "layers": r.get("layers", []),
            "entry": r.get("entry"), "stop": r.get("stop"), "target": r.get("target"),
            "exit": r.get("exit"), "pnl": r.get("pnl", 0), "r_multiple": r.get("r_multiple", 0),
            "confidence": r.get("confidence", 0), "grade": r.get("grade", ""),
            "direction": r.get("direction", ""),
            "dna": r.get("dna") or {}, "strike": r.get("strike"),
            "premium_expansion_pct": r.get("premium_expansion_pct"),
            "opened": r.get("opened", 0), "closed": r.get("closed", 0),
        })
        for eng in (r.get("engines_pass") or []):
            s = _engine_stats.setdefault(eng, {"n": 0, "correct": 0})
            s["n"] += 1
            if win:
                s["correct"] += 1
    log.info("rehydrated %d outcomes, %d engines from Supabase", len(_outcomes), len(_engine_stats))
    return {"loaded": len(_outcomes), "engines": len(_engine_stats), "source": "supabase"}


def update_outcomes(symbol: str, spot: float) -> None:
    for t in list(_tracked):
        if t["symbol"] != symbol:
            continue
        d = 1 if t["direction"] == "BULL" else -1
        # V25 §5 — track excursion in points while the position is open
        excursion = (spot - t["entry"]) * d
        if excursion > t.get("mfe", 0.0):
            t["mfe"] = round(excursion, 1)
        if excursion < t.get("mae", 0.0):
            t["mae"] = round(excursion, 1)
        if (spot - t["target"]) * d >= 0:
            _settle(t, True)
        elif (spot - t["stop"]) * d <= 0:
            _settle(t, False)
        elif time.time() - t["opened"] > 6 * 3600:   # stale — score by drift direction
            _settle(t, (spot - t["entry"]) * d > 0)


def historical_accuracy(regime: str | None = None) -> float | None:
    """Overall accuracy, or regime-specific when that regime has enough samples.
    This is the learning loop: regimes that historically failed demand more."""
    if regime:
        sub = [o for o in _outcomes if o["regime"] == regime]
        if len(sub) >= 5:
            return round(sum(o["win"] for o in sub) / len(sub) * 100, 1)
    if len(_outcomes) < 5:
        return None
    return round(sum(o["win"] for o in _outcomes) / len(_outcomes) * 100, 1)


def engine_reliability() -> dict:
    """Module 5 — per-engine reliability / trust / suggested weight.
    Trust 'BUILDING' until ≥10 samples. Weight = reliability normalised to the
    average reliable engine (display/advisory; not auto-applied to the gate)."""
    rated = {e: {"n": s["n"], "reliability": round(s["correct"] / s["n"] * 100, 0)}
             for e, s in _engine_stats.items() if s["n"] >= 1}
    mature = {e: v["reliability"] for e, v in rated.items() if v["n"] >= 10}
    avg = (sum(mature.values()) / len(mature)) if mature else 0
    out = {}
    for e, v in rated.items():
        trust = "BUILDING" if v["n"] < 10 else (
            "HIGH" if v["reliability"] >= 60 else "MEDIUM" if v["reliability"] >= 50 else "LOW")
        weight = round(v["reliability"] / avg, 2) if avg else 1.0
        out[e] = {**v, "trust": trust, "weight": weight if v["n"] >= 10 else 1.0}
    return out


def learning_stats() -> dict:
    by_regime: dict[str, list[int]] = {}
    for o in _outcomes:
        by_regime.setdefault(o["regime"] or "UNKNOWN", []).append(o["win"])
    return {
        "samples": len(_outcomes),
        "overall_accuracy": historical_accuracy(),
        "by_regime": {r: {"n": len(v), "accuracy": round(sum(v) / len(v) * 100, 1)}
                      for r, v in by_regime.items()},
    }
