"""Premium Radar — live option-premium tracking for the BUYER.

Owner insight: the platform watches the INDEX too much; an option buyer lives
on PREMIUM movement. MODE (move_detector) already alerts on big tiered moves,
but (a) it only watches the ATM strike_queue and (b) the dashboard hides it
until an alert fires — so the BIRTH of a move (₹85 → 99 → 112) is invisible.

Premium Radar fixes both: it tracks ATM ± N strikes (CE + PE) from the FULL
chain every option tick and always exposes, per strike:
  premium · %from-low · velocity (pts/min) · acceleration · volume · OI-change
  · a transparent Runner SCORE (0–100) · a lifecycle STAGE
    (Birth → Expansion → Acceleration → Runner → Exhaustion) · ★stars.

Doctrine kept: read-only over published chain; NOT the decision path; the
Runner score is a DECLARED transparent score (weighted signals), honestly
labelled — never a calibrated win-probability. No trade instruction is emitted.
"""
from __future__ import annotations

import collections
import time
from typing import Any

_LOOKBACK = 300.0          # 5-min rolling window per strike
_N_STRIKES = 4             # ATM ± 4 on each side, both CE and PE
# A "big mover" needs a real ABSOLUTE move, not just a big % off a penny base:
# ₹0.6→₹0.8 is +33% but only +0.2 pts of noise, while ₹0.9→₹22.7 is +21.8 real
# pts. Filtering on points (declared, tunable) keeps real runners, drops lottery
# wiggle that was inflating the runner count and printing absurd % (2422%).
_MIN_MOVE_PTS = 5.0
_tracks: dict[str, dict[str, Any]] = {}


def _series_metrics(series) -> dict[str, Any]:
    now = series[-1][0]
    prem = series[-1][1]
    low = min(p for _, p, _v, _o in series)
    high = max(p for _, p, _v, _o in series)
    rise = prem - low
    rise_pct = (rise / low * 100) if low else 0.0
    # velocity: pts/min over the last 60s
    t0 = now - 60
    older = [p for ts, p, _v, _o in series if ts <= t0]
    base_p = older[-1] if older else series[0][1]
    vel = (prem - base_p)  # pts in last ~60s ≈ pts/min
    # acceleration: last-60s rise vs the PRIOR 60s rise. Honest only when the
    # prior window actually has data — at session start it doesn't, and
    # subtracting a phantom 0 made accel == velocity, so `accel > 0` was
    # trivially true and every rising strike "ignited" (opening false-alert
    # storm: 5 simultaneous IGNITEs, 3/3 alerts false). No prior window ⇒
    # acceleration is UNKNOWN ⇒ 0.0, never a free pass.
    def _rise_between(a, b):
        pts = [p for ts, p, _v, _o in series if a <= ts <= b]
        return (pts[-1] - pts[0]) if len(pts) >= 2 else 0.0
    _prior_pts = [1 for ts, _p, _v, _o in series if now - 120 <= ts <= now - 60]
    accel = (_rise_between(now - 60, now) - _rise_between(now - 120, now - 60)
             if len(_prior_pts) >= 2 else 0.0)
    vol_now = series[-1][2]
    vol_start = series[0][2]
    oi_now = series[-1][3]
    oi_start = next((o for _ts, _p, _v, o in series if o > 0), 0)
    oi_pct = ((oi_now - oi_start) / oi_start * 100) if oi_start else 0.0
    return {"premium": round(prem, 2), "low": round(low, 2), "high": round(high, 2),
            "rise_pct": round(rise_pct, 1), "velocity": round(vel, 2),
            "accel": round(accel, 2), "vol_now": vol_now,
            "vol_delta": vol_now - vol_start, "oi_pct": round(oi_pct, 1)}


def _runner_score(m: dict[str, Any]) -> int:
    """Transparent 0–100 runner SCORE (declared, not win-calibrated). Weighted:
    rise% (30) + velocity (25) + acceleration (20) + volume (15) + OI build (10)."""
    s = 0.0
    s += min(30, m["rise_pct"] * 1.5)                       # rise
    s += min(25, max(0, m["velocity"]) * 2.5)               # velocity
    s += 20 if m["accel"] > 0 else (5 if m["accel"] == 0 else 0)  # acceleration
    s += 15 if m["vol_delta"] > 0 else 0                    # fresh volume
    s += min(10, max(0, m["oi_pct"]))                       # OI build-up
    return int(max(0, min(100, round(s))))


def _stage(m: dict[str, Any]) -> str:
    if m["velocity"] < 0 and m["rise_pct"] >= 20:
        return "EXHAUSTION"
    if m["rise_pct"] < 5:
        return "BIRTH"
    if m["accel"] > 0 and m["velocity"] >= 4:
        return "RUNNER"
    if m["accel"] > 0:
        return "ACCELERATION"
    return "EXPANSION"


def _coil(m: dict[str, Any], was_coiled: bool = False) -> dict[str, Any]:
    """Pre-breakout 'loaded spring' — the EARLIEST honest catch.

    Every other signal (runner-score, stage, phase) needs the premium to have
    already moved. This one fires BEFORE the move: energy building underneath
    (fresh volume and/or OI accumulating) while the premium is still
    compressed (little rise, near-flat velocity). Catching a strike here means
    being ready at ₹86 instead of chasing at ₹120.

    Declared heuristic from data already captured — NOT a win probability.
    States: COILED (loaded, no move yet) → IGNITING (spring releasing now)."""
    compressed = m["rise_pct"] < 8 and abs(m["velocity"]) < 2
    vol_energy = m["vol_delta"] > 0
    oi_energy = m["oi_pct"] >= 1
    energy = (1 if vol_energy else 0) + (1 if oi_energy else 0)
    # strength 0–100: energy sources + how much OI is piling in (capped)
    strength = int(min(100, energy * 35 + min(30, max(0, m["oi_pct"]) * 3)))
    # ignition path 1: a velocity SPIKE on stored energy, still early (catchable)
    if m["rise_pct"] < 18 and m["velocity"] >= 2 and m["accel"] > 0 and energy >= 1:
        return {"state": "IGNITING", "dot": "⚡", "strength": max(strength, 60),
                "note": "Coil breaking — energy releasing, move starting NOW. Earliest entry window."}
    # ignition path 2 — the slow-runner breakout (evidence 2026-07-14: of 21
    # MISSED runners, 19 were COILED but NEVER ignited because they climbed
    # WITHOUT a velocity≥2 spike). A loaded coil that has now crossed the stir
    # (+5%) and is still rising on its stored energy IS the breakout — alert it
    # while still catchable (<20%), even without the spike.
    # REQUIRES was_coiled: the evidence was about strikes that ACTUALLY coiled
    # first. Without this gate it fired on any 5-20% riser and caused an
    # opening false-alert storm. Declared/tunable; measured by the Black Box.
    if was_coiled and 5 <= m["rise_pct"] < 20 and m["velocity"] > 0 and energy >= 1:
        return {"state": "IGNITING", "dot": "⚡", "strength": max(strength, 55),
                "note": "Coil breakout — loaded spring released, premium climbing on volume/OI. Early entry window."}
    if compressed and energy >= 1:
        bits = []
        if vol_energy:
            bits.append("volume rising")
        if oi_energy:
            bits.append(f"OI +{m['oi_pct']}%")
        return {"state": "COILED", "dot": "🌀", "strength": strength,
                "note": f"Loaded spring — premium flat but {', '.join(bits)}. Watch for ignition."}
    return {"state": "NONE", "dot": "", "strength": 0, "note": ""}


def _stars(score: int) -> int:
    return max(1, min(5, 1 + score // 20))


# Owner's 3 macro-phases by %-rise from the session low.
def _phase(rise_pct: float) -> dict[str, str]:
    if rise_pct >= 70:
        return {"code": "RUNNER_CONFIRMED", "label": "RUNNER CONFIRMED", "dot": "🔴"}
    if rise_pct >= 30:
        return {"code": "RUNNER_BUILDING", "label": "RUNNER BUILDING", "dot": "🟠"}
    return {"code": "BUILDING", "label": "PREMIUM BUILDING", "dot": "🟢"}


def _ladder(series) -> list[dict[str, Any]]:
    """Down-sample the premium series to ≤6 points for the visible ladder
    (09:36 ₹85 → 09:57 ₹158). Times are IST HH:MM."""
    from ..core.clock import IST
    import datetime
    pts = list(series)
    if len(pts) <= 6:
        chosen = pts
    else:
        step = (len(pts) - 1) / 5
        chosen = [pts[round(i * step)] for i in range(6)]
    out = []
    for ts, p, _v, _o in chosen:
        t = datetime.datetime.fromtimestamp(ts, IST).strftime("%H:%M")
        out.append({"t": t, "p": round(p, 2)})
    return out


def scan(symbol: str, spot: float, chain: list[dict] | None) -> None:
    """Track ATM ± N strikes (CE+PE) each option tick. Read-only, additive."""
    if not chain or not spot:
        return
    now = time.time()
    # ATM = chain strike nearest spot
    strikes = sorted({float(r.get("strike", 0)) for r in chain if r.get("strike")})
    if not strikes:
        return
    atm = min(strikes, key=lambda k: abs(k - spot))
    idx = strikes.index(atm)
    window = strikes[max(0, idx - _N_STRIKES): idx + _N_STRIKES + 1]

    live_keys = set()
    for strike in window:
        row = next((r for r in chain if float(r.get("strike", 0)) == strike), None)
        if not row:
            continue
        for typ, side in (("CE", "ce"), ("PE", "pe")):
            prem = float(row.get(f"{side}_ltp") or 0)
            if prem <= 0:
                continue
            key = f"{symbol}:{int(strike)}:{typ}"
            live_keys.add(key)
            t = _tracks.setdefault(key, {"series": collections.deque(maxlen=200),
                                         "symbol": symbol, "strike": int(strike),
                                         "type": typ, "peak_rise": 0.0, "peak_prem": 0.0,
                                         "vol_confirm": None, "oi_confirm": None})
            vol = float(row.get(f"{side}_volume") or 0)
            oi = float(row.get(f"{side}_oi") or 0)
            t["series"].append((now, prem, vol, oi))
            while t["series"] and now - t["series"][0][0] > _LOOKBACK:
                t["series"].popleft()
            # day-peak + first confirmation timestamps (for Missed Opportunity)
            m = _series_metrics(t["series"])
            # runner-score history for the confidence-evolution sparkline
            t.setdefault("score_hist", collections.deque(maxlen=40))
            sc = _runner_score(m)
            hist = t["score_hist"]
            if not hist or now - hist[-1][0] >= 10:   # ~1 sample / 10s
                hist.append((now, sc))
            # absolute session low/high — the TRUE intraday range for Missed
            # (the rolling-window low moves up, so peak must use the session low)
            t["sess_low"] = min(t.get("sess_low", prem), prem)
            t["sess_high"] = max(t.get("sess_high", prem), prem)
            t["peak_prem"] = t["sess_high"]
            t["peak_rise"] = ((t["sess_high"] - t["sess_low"]) / t["sess_low"] * 100
                              if t["sess_low"] else 0.0)
            if t["vol_confirm"] is None and m["vol_delta"] > 0 and m["rise_pct"] >= 5:
                t["vol_confirm"] = now
            if t["oi_confirm"] is None and m["oi_pct"] >= 1 and m["rise_pct"] >= 5:
                t["oi_confirm"] = now
            # coil clock: when did this strike first start loading? (evidence:
            # "coiling 45s") — reset once it stops coiling so it's always fresh.
            cs = _coil(m, bool(t.get("ever_coiled")))["state"]
            if cs == "COILED":
                t.setdefault("coil_since", now)
                t["ever_coiled"] = True      # remember: this spring WAS loaded
            elif cs != "IGNITING":
                t.pop("coil_since", None)
                # forget the coil ONLY on true resolution — the move ran away
                # (≥20%) or genuinely faded back to base (<2% and falling).
                # The old condition (any single velocity≤0 tick) erased the
                # memory during normal pullbacks, so path-2 could never fire in
                # the 5-20% window — Friday 2026-07-17 evidence: all 12 missed
                # runners were coiled-but-never-ignited (~500 pts missed).
                # Owner-approved detection change (the ONLY one this weekend).
                if m["rise_pct"] >= 20 or (m["rise_pct"] < 2 and m["velocity"] < 0):
                    t.pop("ever_coiled", None)
            # feed the measurement layer (read-only KPI + black-box instrumentation)
            try:
                from . import opportunity_metrics as _om
                # wave_n only matters at ignite: how many same-type strikes are
                # loaded right now (chain-wave corroboration evidence)
                wave_n = 0
                if cs == "IGNITING":
                    wave_n = sum(1 for k2, t2 in _tracks.items()
                                 if t2.get("symbol") == symbol and t2.get("type") == typ
                                 and t2.get("ever_coiled"))
                _om.record(key, int(strike), typ, prem, m["rise_pct"], cs,
                           score=sc, velocity=m["velocity"], vol_delta=m["vol_delta"],
                           oi_pct=m["oi_pct"], accel=m["accel"], now=now,
                           symbol=symbol, wave_n=wave_n)
            except Exception:
                pass  # measurement must never affect the radar
    # drop stale tracks (strike left the ATM window long ago)
    for k in [k for k, t in _tracks.items() if t["series"] and now - t["series"][-1][0] > 120]:
        _tracks.pop(k, None)


def _checklist(m: dict[str, Any]) -> dict[str, bool]:
    """The conditions a strike needs to become a runner (owner's watchlist)."""
    return {
        "premium_rising": m["rise_pct"] > 0,
        "velocity": m["velocity"] > 0,
        "volume": m["vol_delta"] > 0,
        "oi": m["oi_pct"] >= 1,
    }


_CHECK_LABEL = {"premium_rising": "Premium velocity", "velocity": "Velocity rising",
                "volume": "Volume expansion", "oi": "OI build-up"}


def _thinking(rows: list[dict]) -> dict[str, Any] | None:
    """Deterministic reasoning cycle (OBSERVE→REASON→EXPECT→RISK) on the single
    best current opportunity. Evidence-based narration of the radar's own
    numbers — NOT a prediction, NOT an entry call. The engine gate decides."""
    if not rows:
        return None
    r = rows[0]
    chk = r["checklist"]
    have = [_CHECK_LABEL[k] for k, v in chk.items() if v]
    missing = [_CHECK_LABEL[k] for k, v in chk.items() if not v]
    # expectation is a conditional statement, never a certainty
    if r["rise_pct"] >= 70:
        expect = "Runner confirmed — continuation while volume/OI hold; watch for exhaustion."
    elif r["checks_met"] >= 3 and r["accel"] > 0:
        expect = ("Runner continuation likely WHILE the remaining checks confirm and OI stays positive."
                  if missing else
                  "All checks confirmed — runner continuation likely while volume/OI stay positive.")
    elif r["checks_met"] >= 2:
        expect = "Building — needs the remaining checks to become a runner."
    else:
        expect = "Early / weak — not enough confirmation yet."
    risk = ("Volume exhaustion or OI failing to confirm can invalidate this move."
            if missing else "Give-back if velocity fades.")

    # #2 — inferred CAUSE (honest heuristic from OI/premium/volume/acceleration)
    if r["oi_pct"] <= -1 and r["rise_pct"] > 0:
        cause = "Short covering (premium up while OI falls)"
    elif r["oi_pct"] >= 1 and r["rise_pct"] > 0:
        cause = "Fresh buying (OI and premium both rising)"
    elif r["accel"] > 0 and r["vol_delta"] > 0:
        cause = "Momentum / gamma expansion (accelerating on volume)"
    else:
        cause = "Directional buying"

    # #5 — pre-stated INVALIDATION (falsifiable: the thesis is cancelled IF…)
    inval = ["Velocity turns negative (premium stops rising)",
             f"Premium falls back under ₹{r['from_low']}"]
    if r["oi_pct"] >= 0:
        inval.insert(1, "OI turns negative")

    # Evidence Meter — where the confidence comes from (declared strengths 0–100)
    def _clip(x): return int(max(0, min(100, round(x))))
    evidence = {
        "Premium": _clip(r["rise_pct"] * 3),
        "Velocity": _clip(max(0, r["velocity"]) * 10),
        "Acceleration": 100 if r["accel"] > 0 else 50 if r["accel"] == 0 else 20,
        "Volume": 90 if r["vol_delta"] > 0 else 25,
        "OI": _clip(max(0, r["oi_pct"]) * 10),
    }

    # #4 — Miss probability / entry-window honesty (from the lifecycle phase)
    rp = r["rise_pct"]
    if rp >= 70:
        miss = {"label": "LATE — don't chase", "tone": "late",
                "detail": f"Already ran {rp:.0f}% — runner mostly played out."}
    elif rp >= 30:
        miss = {"label": "ENTERING — window closing", "tone": "mid",
                "detail": f"Up {rp:.0f}% — momentum underway, later entries riskier."}
    else:
        miss = {"label": "EARLY — window open", "tone": "early",
                "detail": f"Only {rp:.0f}% from low — birth/build stage."}

    return {
        "watching": f"{r['strike']} {r['type']}",
        "premium": r["premium"], "rise_pct": r["rise_pct"],
        "runner_score": r["runner_score"], "stars": r["stars"], "stage": r["stage"],
        "miss": miss,
        "cause": cause,
        "invalidation": {"conditions": inval, "then": "Runner thesis cancelled — stand aside."},
        "evidence": evidence,
        "observed": f"Premium ₹{r['from_low']} → ₹{r['premium']} ({r['rise_pct']:+}% ), "
                    f"velocity {r['velocity']} pts/min, OI {r['oi_pct']:+}%",
        "confirmed": have,
        "missing": missing,
        "confirmations_line": f"{r['checks_met']} / 4 confirmations",
        "expectation": expect,
        "risk": risk,
        "confidence": r["runner_score"],
        "phase": r["phase"],
        "score_hist": r.get("score_hist", []),
        "cycle": "OBSERVE → DETECT → REASON → EXPECT → VERIFY → LEARN",
        "next_review": "~5s (next option tick)",
        "note": "Evidence-based reasoning over live premium data — not a "
                "prediction and not an entry signal. The engine gate decides trades.",
    }


def _attention(rows: list[dict], topn: int = 4) -> dict[str, Any]:
    """👀 AI Attention — where the radar's focus is, as a % across strikes
    (like an LLM attention distribution). Weight = runner_score; normalised.
    Honest: this is WHERE it is looking, not a probability of profit."""
    scored = [r for r in rows if r["runner_score"] > 0]
    total = sum(r["runner_score"] for r in scored)
    if not total:
        return {"items": [], "note": "No active premium movement to focus on."}
    ranked = sorted(scored, key=lambda r: r["runner_score"], reverse=True)
    items = [{"strike": r["strike"], "type": r["type"],
              "pct": round(100 * r["runner_score"] / total, 1)}
             for r in ranked[:topn]]
    rest = round(100 - sum(i["pct"] for i in items), 1)
    if rest > 0.5:
        items.append({"strike": None, "type": "Rest", "pct": rest})
    return {"items": items,
            "note": "Attention = share of the radar's focus (runner-score "
                    "weighted), not a win probability."}


def _chain_wave(rows: list[dict]) -> list[dict[str, Any]]:
    """3+ same-type strikes heating TOGETHER = a real directional WAVE, not a
    single-strike blip or fakeout. CE wave → underlying pushing up; PE wave →
    down. This is the confirmation layer for the coil: a COIL/IGNITE that sits
    inside a wave is far more trustworthy than a lone strike twitching.
    Declared heuristic on data already tracked — never a trade instruction."""
    out = []
    for typ, dirn, label in (("CE", "up", "BULLISH WAVE"), ("PE", "down", "BEARISH WAVE")):
        hot = [r for r in rows if r["type"] == typ and (
            r.get("coil", {}).get("state") in ("COILED", "IGNITING")
            or (r["velocity"] > 0 and r["rise_pct"] >= 3))]
        if len(hot) >= 3:
            hot.sort(key=lambda r: r["strike"])
            igniting = sum(1 for r in hot if r.get("coil", {}).get("state") == "IGNITING")
            out.append({
                "type": typ, "direction": dirn, "label": label,
                "count": len(hot), "igniting": igniting,
                "strikes": [r["strike"] for r in hot],
                "note": (f"{len(hot)} {typ} strikes heating together — real "
                         "directional pressure, not a single-strike blip."),
            })
    out.sort(key=lambda w: (w["count"], w["igniting"]), reverse=True)
    return out


def radar(top: int = 8) -> dict[str, Any]:
    """Leaders (running now) · Watchlist (building) · Missed (peaked today)."""
    rows = []
    missed = []
    for key, t in _tracks.items():
        if len(t["series"]) < 2:
            continue
        m = _series_metrics(t["series"])
        score = _runner_score(m)
        chk = _checklist(m)
        coil = _coil(m, bool(t.get("ever_coiled")))
        coil_secs = int(time.time() - t["coil_since"]) if t.get("coil_since") else 0
        rows.append({
            "symbol": t["symbol"], "strike": t["strike"], "type": t["type"],
            "premium": m["premium"], "from_low": m["low"], "rise_pct": m["rise_pct"],
            "velocity": m["velocity"], "accel": m["accel"], "oi_pct": m["oi_pct"],
            "vol_delta": m["vol_delta"], "runner_score": score, "stars": _stars(score),
            "stage": _stage(m), "phase": _phase(m["rise_pct"]),
            "ladder": _ladder(t["series"]), "checklist": chk,
            "checks_met": sum(chk.values()),
            "score_hist": [s for _ts, s in t.get("score_hist", [])],
            "coil": {**coil, "secs": coil_secs},
        })
        # Missed Opportunity: strike ran a big move today (peak ≥ 30%)
        _sess_low0 = t.get("sess_low", m["low"])
        if t.get("peak_rise", 0) >= 30 and (t["peak_prem"] - _sess_low0) >= _MIN_MOVE_PTS:
            reasons = []
            if t.get("vol_confirm"):
                reasons.append("Volume confirmation")
            if t.get("oi_confirm"):
                reasons.append("OI breakout")
            sess_low = t.get("sess_low", m["low"])
            # reconcile with the black box: a strike shown here ran ≥30%, but that
            # does NOT mean we missed it — the radar may have caught it EARLY. Tag
            # each row with its real capture so "big mover" ≠ "missed opportunity".
            try:
                from . import opportunity_metrics as _om
                caught = _om.capture_status(t["strike"], t["type"])
            except Exception:
                caught = None
            missed.append({
                "symbol": t["symbol"], "strike": t["strike"], "type": t["type"],
                "from_low": round(sess_low, 2), "peak_premium": round(t["peak_prem"], 2),
                "peak_rise_pct": round(t["peak_rise"], 1),
                "missed_points": round(t["peak_prem"] - sess_low, 2),
                "reasons": reasons or ["Premium velocity"],
                "caught": caught,   # EARLY = radar caught it · LATE/MISSED = truly missed
            })

    rows.sort(key=lambda r: r["runner_score"], reverse=True)
    # Leaders = clear movers; Watchlist = still-building with momentum but not yet runners
    leaders = [r for r in rows if r["rise_pct"] >= 30][:top]
    thinking = _thinking(rows)
    attention = _attention(rows)
    watchlist = [r for r in rows
                 if r["rise_pct"] < 30 and r["checks_met"] >= 2 and r["runner_score"] > 0]
    watchlist.sort(key=lambda r: r["runner_score"], reverse=True)
    missed.sort(key=lambda r: r["peak_rise_pct"], reverse=True)
    # ⚡ EARLY WARNING — the earliest catch: strikes loading (COILED) or just
    # breaking out (IGNITING), BEFORE the runner-score can see them. IGNITING
    # first (act now), then strongest coils. This is the anti-miss layer.
    early = [r for r in rows if r.get("coil", {}).get("state") in ("COILED", "IGNITING")]
    early.sort(key=lambda r: (r["coil"]["state"] != "IGNITING", -r["coil"]["strength"]))
    # Chain-wave confirmation — and mark each early row that sits inside a wave
    # (its coil is corroborated by neighbours moving the same way).
    waves = _chain_wave(rows)
    wave_types = {w["type"] for w in waves}
    for r in early:
        r["in_wave"] = r["type"] in wave_types
    return {
        "movers": rows[:top],            # full radar table (kept)
        "leaders": leaders,              # 🔴/🟠 running now
        "watchlist": watchlist[:6],      # 🟢 building — watch before it runs
        "missed": missed[:6],            # peaked ≥30% today
        "early_warning": early[:5],      # ⚡ loading/igniting — catch it at birth
        "chain_wave": waves,             # 🌊 3+ same-type strikes = real direction
        "thinking": thinking,            # 🧠 AI reasoning cycle on the top opportunity
        "attention": attention,          # 👀 where the radar's focus is (%)
        "tracked": len(_tracks),
        "note": "Runner score is a declared transparent signal blend "
                "(rise/velocity/acceleration/volume/OI), NOT a win-calibrated "
                "probability. Radar observes premium; it never places or "
                "recommends a trade — the engine gate decides.",
    }
