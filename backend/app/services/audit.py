"""Validation & Audit Layer (Phase 3) — measurement only.

Records every decision the EXISTING engines produce and forward-tracks the
real outcome against the spot ticks already flowing (no new market data, no
new engines, no logic/threshold changes). It then scores how well WAIT,
ENTER, runner calls, no-trade, animal classification, decision clarity and
data confidence actually performed.

Forward-tracking is a heuristic measurement, not a trade:
  * ENTER: track real entry/SL/T1-3 → which target reached vs SL first.
  * WAIT / NO TRADE: track a hypothetical ATR trade in the prevailing bias —
    if it would have hit SL, the WAIT "saved a loss"; if it would have hit
    T1, the WAIT was a "false WAIT" (missed). Else the WAIT was correct.
Samples settle on first of target/SL or a 45-minute window.
"""
from __future__ import annotations

import time
from collections import Counter, deque
from typing import Any

WINDOW_SEC = 45 * 60
_open: list[dict] = []                 # forward-tracked samples (capped)
_history: deque = deque(maxlen=400)    # settled audit records
_action_counts: Counter = Counter()    # lifetime decision distribution


def record_decision(decision: dict[str, Any], intel: dict[str, Any],
                    signal: dict[str, Any], spot: float, atr: float,
                    bias: str, regime: str, session: str) -> None:
    """Called once per AI cycle. Logs the action and arms a forward sample."""
    action = decision.get("primary_action", "WAIT")
    _action_counts[action] += 1

    if spot <= 0 or atr <= 0:
        return
    # avoid duplicate open samples for the same standing decision
    if _open and _open[-1]["action"] == action and abs(_open[-1]["spot0"] - spot) < atr * 0.2:
        return
    if len(_open) > 60:
        _open.pop(0)

    is_enter = action == "ENTER" and signal.get("signal") not in (None, "NO TRADE")
    direction = (signal.get("direction")
                 or ("BULL" if bias in ("BULLISH", "FAVORABLE") else "BEAR" if bias == "BEARISH" else "BULL"))
    d = 1 if direction == "BULL" else -1

    if is_enter and signal.get("entry") and signal.get("stop_loss"):
        entry = signal["entry"]; sl = signal["stop_loss"]
        t1, t2, t3 = signal["target1"], signal["target2"], signal["target3"]
    else:
        entry = spot
        sl = spot - d * 1.2 * atr
        t1, t2, t3 = spot + d * 1.5 * atr, spot + d * 2.5 * atr, spot + d * 4.0 * atr

    ex = intel.get("expansion", {})
    _open.append({
        "action": action, "hypothetical": not is_enter, "dir": d,
        "spot0": spot, "entry": entry, "sl": sl, "t1": t1, "t2": t2, "t3": t3,
        "atr": atr, "opened": time.time(),
        "max_fav": 0.0, "max_adv": 0.0, "reached": 0, "sl_hit": False,
        # predictions to validate
        "runner_prob": float(ex.get("runner_probability") or 0),
        "expected_move": float(ex.get("expected_move") or atr * 2),
        "animal": (intel.get("market_animal") or {}).get("animal", ""),
        "clarity": (intel.get("decision_clarity") or {}).get("label", ""),
        "data_confidence": intel.get("data_confidence", ""),
        "regime": regime, "session": session,
        # Shadow Calibration (owner, 2026-08-07) — the ONE field this module
        # was missing. It already forward-tracks a HYPOTHETICAL sample on
        # every blocked cycle (hypothetical=True above) all the way to a real
        # win/loss, but never recorded WHAT CONFIDENCE the engine predicted at
        # that moment — so blocked cycles could never be calibration-scored.
        # Same expression memory.track_signal() uses for the real calibration
        # (dynamic_confidence or confidence), so the two are comparable.
        # Recorded only; changes no audit metric, no gate, no threshold.
        "signal_confidence": float(signal.get("dynamic_confidence")
                                   or signal.get("confidence") or 0),
        "direction": direction,
    })


def on_tick(spot: float) -> None:
    """Advance open samples against the live price (uses existing tick stream)."""
    if spot <= 0:
        return
    now = time.time()
    for s in list(_open):
        d = s["dir"]
        fav = (spot - s["entry"]) * d
        adv = (s["entry"] - spot) * d
        s["max_fav"] = max(s["max_fav"], fav)
        s["max_adv"] = max(s["max_adv"], adv)
        # target / stop progression (target before stop within a tick = optimistic
        # only for the favorable side; stop checked first = conservative)
        if not s["sl_hit"] and (spot - s["sl"]) * d <= 0 and s["reached"] == 0:
            s["sl_hit"] = True
            _settle(s)
            continue
        if (spot - s["t3"]) * d >= 0:
            s["reached"] = 3; _settle(s); continue
        if (spot - s["t2"]) * d >= 0:
            s["reached"] = max(s["reached"], 2)
        elif (spot - s["t1"]) * d >= 0:
            s["reached"] = max(s["reached"], 1)
        if now - s["opened"] > WINDOW_SEC:
            _settle(s)


def _settle(s: dict) -> None:
    if s in _open:
        _open.remove(s)
    actual_exp = s["max_fav"]                      # max favorable excursion (points)
    win = s["reached"] >= 1 and not (s["sl_hit"] and s["reached"] == 0)
    _history.append({
        "action": s["action"], "hypothetical": s["hypothetical"],
        "reached": s["reached"], "sl_hit": s["sl_hit"], "win": 1 if win else 0,
        "runner_prob": s["runner_prob"], "expected_move": s["expected_move"],
        "actual_expansion": round(actual_exp, 1), "atr": s["atr"],
        "animal": s["animal"], "clarity": s["clarity"],
        "data_confidence": s["data_confidence"], "regime": s["regime"],
        "session": s["session"], "ts": time.time(),
        # Shadow Calibration (owner, 2026-08-07) — carried through to the
        # settled record so shadow_calibration.py can pair predicted
        # confidence with the realised win/loss. Additive: every existing
        # key above is untouched, so every existing report() consumer is
        # byte-identical.
        "signal_confidence": s.get("signal_confidence", 0.0),
        "direction": s.get("direction", ""),
    })


# ---------- reporting ----------
def _pct(num: int, den: int) -> float | None:
    return round(num / den * 100, 1) if den else None


def report() -> dict[str, Any]:
    h = list(_history)
    enters = [r for r in h if not r["hypothetical"]]
    waits = [r for r in h if r["hypothetical"]]

    # entry accuracy
    e_n = len(enters)
    e_t1 = sum(1 for r in enters if r["reached"] >= 1)
    e_t2 = sum(1 for r in enters if r["reached"] >= 2)
    e_t3 = sum(1 for r in enters if r["reached"] >= 3)
    e_sl = sum(1 for r in enters if r["sl_hit"] and r["reached"] == 0)

    # wait / no-trade audit (hypothetical would-have trades)
    w_n = len(waits)
    w_saved = sum(1 for r in waits if r["sl_hit"] and r["reached"] == 0)   # avoided a loss
    w_false = sum(1 for r in waits if r["reached"] >= 1)                   # missed a winner
    w_correct = w_n - w_false

    # runner audit (predicted runner_prob >= 60 → expect Large+ expansion)
    pred_runner = [r for r in enters if r["runner_prob"] >= 60]
    big = lambda r: r["actual_expansion"] >= max(r["expected_move"] * 0.8, r["atr"] * 2.5)
    runner_hit = sum(1 for r in pred_runner if big(r))
    false_runner = sum(1 for r in pred_runner if not big(r))
    missed_runner = sum(1 for r in enters if r["runner_prob"] < 60 and big(r))

    # animal audit — did realized expansion match the animal's expected band?
    bands = {"Rabbit": (0, 1.5), "Horse": (1.0, 3.0), "Elephant": (2.0, 6.0), "Cheetah": (2.5, 99)}
    a_grp: dict[str, list[int]] = {}
    for r in enters:
        b = bands.get(r["animal"])
        if not b or r["atr"] <= 0:
            continue
        mult = r["actual_expansion"] / r["atr"]
        a_grp.setdefault(r["animal"], []).append(1 if b[0] <= mult <= b[1] else 0)
    animal_acc = {k: {"n": len(v), "accuracy": _pct(sum(v), len(v))} for k, v in a_grp.items()}

    def winrate_by(key: str, items: list[dict]) -> dict:
        g: dict[str, list[int]] = {}
        for r in items:
            g.setdefault(r.get(key) or "—", []).append(r["win"])
        return {k: {"n": len(v), "win_rate": _pct(sum(v), len(v))} for k, v in g.items()}

    clarity_audit = winrate_by("clarity", enters)
    dataconf_audit = winrate_by("data_confidence", enters)
    overall_acc = _pct(sum(r["win"] for r in enters), e_n)

    # scorecard
    runner_acc = _pct(runner_hit, len(pred_runner))
    animal_overall = _pct(sum(sum(v) for v in a_grp.values()), sum(len(v) for v in a_grp.values()))
    clear_rows = [r for r in enters if r["clarity"] in ("VERY CLEAR", "CLEAR")]
    decision_acc = _pct(sum(r["win"] for r in clear_rows), len(clear_rows))

    return {
        "distribution": {a: _action_counts.get(a, 0) for a in ("WAIT", "ENTER", "HOLD", "TRAIL", "EXIT")},
        "total_decisions": sum(_action_counts.values()),
        "entry": {"n": e_n, "entry_accuracy": _pct(e_t1, e_n),
                  "t1": _pct(e_t1, e_n), "t2": _pct(e_t2, e_n), "t3": _pct(e_t3, e_n),
                  "stop_loss_rate": _pct(e_sl, e_n)},
        "wait": {"n": w_n, "wait_accuracy": _pct(w_correct, w_n),
                 "saved_loss": _pct(w_saved, w_n), "false_wait": _pct(w_false, w_n)},
        "no_trade": {"avoided": w_n, "no_trade_accuracy": _pct(w_correct, w_n),
                     "capital_saved": _pct(w_saved, w_n)},
        "runner": {"n": len(pred_runner), "runner_accuracy": runner_acc,
                   "false_runner": _pct(false_runner, len(pred_runner)),
                   "missed_runner": missed_runner},
        "animal": {"by_animal": animal_acc, "classification_accuracy": animal_overall},
        "clarity": {"by_label": clarity_audit, "decision_clarity_accuracy": decision_acc},
        "data_confidence": {"by_level": dataconf_audit,
                            "reliability": (dataconf_audit.get("High") or {}).get("win_rate")},
        # profit-booking accuracy: of entries, % that reached ≥ T1 (a booking
        # opportunity actually existed to act on)
        "profit_booking_accuracy": _pct(e_t1, e_n),
        "scorecard": {
            "overall_accuracy": overall_acc, "entry_accuracy": _pct(e_t1, e_n),
            "runner_accuracy": runner_acc, "no_trade_accuracy": _pct(w_correct, w_n),
            "animal_accuracy": animal_overall, "decision_accuracy": decision_acc,
            "profit_booking_accuracy": _pct(e_t1, e_n),
        },
        "monthly_report": _monthly(enters, clarity_audit),
        "samples_open": len(_open), "samples_settled": len(h),
        "ts": time.time(),
    }


def _monthly(enters: list[dict], clarity_audit: dict) -> dict:
    def best_worst(key: str):
        g: dict[str, list[int]] = {}
        for r in enters:
            g.setdefault(r.get(key) or "—", []).append(r["win"])
        rated = {k: sum(v) / len(v) for k, v in g.items() if len(v) >= 3}
        if not rated:
            return None, None
        return max(rated, key=rated.get), min(rated, key=rated.get)

    best_sig, worst_sig = best_worst("animal")
    best_reg, worst_reg = best_worst("regime")
    recs: list[str] = []
    # data-proven tuning suggestions only (never auto-applied)
    unclear = [r for r in enters if r["clarity"] in ("UNCLEAR", "MODERATE")]
    if unclear and sum(r["win"] for r in unclear) / len(unclear) < 0.45:
        recs.append("Low-clarity entries underperform — consider raising the clarity gate.")
    if worst_reg:
        recs.append(f"{worst_reg} regime is the weakest — consider tightening entries there.")
    if not recs:
        recs.append("No threshold change indicated yet — keep measuring.")
    return {
        "best_signal_type": best_sig, "worst_signal_type": worst_sig,
        "most_reliable_regime": best_reg, "least_reliable_regime": worst_reg,
        "biggest_strength": best_reg, "biggest_weakness": worst_reg,
        "recommended_threshold_adjustments": recs,
    }
