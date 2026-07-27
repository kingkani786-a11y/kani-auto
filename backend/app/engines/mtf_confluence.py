"""MTF Confluence Engine — owner Step 10 (V7.0 Roadmap, 2026-07-27).

A NEW, ADDITIVE engine: real per-timeframe analysis across 7 timeframes
(1m/3m/5m/15m/1H/4H/Daily), each scored on Trend/Structure/Momentum/VWAP/
EMA/BOS-CHOCH/Volume/CPR using the SAME already-existing, timeframe-
agnostic compute functions (technicals.py, structure.py,
support_resistance.py) — no new algorithms, only new orchestration.

Feeds ONLY new display surfaces (Hero MTF table, Evidence Panel row, Risk
Panel conflict flag, AI Dealer voice narration). Does NOT touch the
EXISTING mtf.py engine or anything it already feeds (the calibration
gate, dynamic confidence, trade-quality grade) — that stays exactly as it
is today; swapping what feeds a real gate would be a Trading Doctrine
change, out of scope for this additive display step. Similarly,
`higher_tf_conflict` here is informational only — it never changes
position sizing (that would also be a Trading Doctrine change, needing
the evidence-approval pipeline first).

Rate-limit-safe by design: 1m uses the already-fetched state.candles feed;
3m/5m/15m are resampled from that SAME feed (zero new broker calls, same
technique mtf.py already uses); Daily reuses the already-cached daily
series from period_pivot_cache.py (zero new calls); 1H and 4H each have
their own low-frequency, cache-gated fetch (mtf_1h_cache.py / 10 min TTL,
mtf_4h_cache.py / 20 min TTL), not per-cycle.

Bug fix (2026-07-27, V7.0 observation phase): 1H was originally resampled
from state.candles too, but that buffer is hard-capped at 600 one-minute
bars (market_service.py) — only 10 complete 1H bars can ever exist in that
window, 3x short of the 30-bar _MIN_BARS floor. 1H was therefore
structurally unable to ever become "ready", confirmed live. Switched to a
direct broker fetch (same pattern as 4H) instead of resampling.
"""
from __future__ import annotations

from typing import Any

from . import structure, support_resistance, technicals
from .mtf import resample

TF_LABELS = ["1m", "3m", "5m", "15m", "1H", "4H", "Daily"]
_RESAMPLE_MIN = {"1m": 1, "3m": 3, "5m": 5, "15m": 15}
# Higher timeframes carry more weight — same declared-weighting concept
# mtf.py's own TF_WEIGHT already uses, extended to the 3 new timeframes.
TF_WEIGHT = {"1m": 0.6, "3m": 0.7, "5m": 0.8, "15m": 1.0, "1H": 1.2, "4H": 1.4, "Daily": 1.6}
_MIN_BARS = 30


def _tf_signals(candles: list[dict]) -> dict[str, Any] | None:
    """The 8 signal types for ONE timeframe's candle series. Every one of
    these reuses an already-existing, timeframe-agnostic function — Trend/
    VWAP/EMA/Momentum(via ADX) all come from technicals.trend_engine();
    Structure + BOS/CHOCH from structure.analyze(); CPR from
    support_resistance.pivot_formula() applied to this timeframe's own
    prior completed bar (the same prior-period generalization
    support_resistance.period_pivots() already uses for Weekly/Monthly,
    just applied per-timeframe here instead of per-calendar-period)."""
    if not candles or len(candles) < _MIN_BARS:
        return None
    closes = [c["close"] for c in candles]
    last = closes[-1]
    vwap_v = technicals.vwap(candles)
    trend = technicals.trend_engine(candles, vwap_v)
    atr_v = technicals.atr(candles)
    struct = structure.analyze(candles, atr_v)
    mom = technicals.momentum(closes)
    prev_bar = candles[-2] if len(candles) >= 2 else candles[-1]
    cpr = support_resistance.pivot_formula(prev_bar["high"], prev_bar["low"], prev_bar["close"])
    vols = [c.get("volume", 0) for c in candles[-20:]]
    avg_vol = sum(vols) / len(vols) if vols else 0

    signals = {
        "trend": trend.get("direction", "NEUTRAL"),
        "structure": struct.get("direction", "NEUTRAL"),
        "momentum": "BULL" if mom > 0.1 else "BEAR" if mom < -0.1 else "NEUTRAL",
        "vwap": "BULL" if last > vwap_v else "BEAR",
        "ema": trend.get("direction", "NEUTRAL"),  # trend_engine already folds the EMA20/50/200 stack in
        "bos_choch": struct.get("bos_choch"),       # BOS/CHOCH itself has no inherent bull/bear polarity —
                                                     # shown as evidence, not counted in the verdict vote below
        "volume": "CONFIRMS" if (avg_vol and candles[-1].get("volume", 0) > avg_vol * 1.2) else "NEUTRAL",
        "cpr": "BULL" if last > cpr.get("pivot", last) else "BEAR",
    }
    voting = ("trend", "structure", "momentum", "vwap", "ema", "cpr")
    bull = sum(1 for k in voting if signals[k] == "BULL")
    bear = sum(1 for k in voting if signals[k] == "BEAR")
    verdict = "BUY" if bull - bear >= 2 else "SELL" if bear - bull >= 2 else "NEUTRAL"
    return {"signals": signals, "verdict": verdict, "bull": bull, "bear": bear}


def analyze(candles_1m: list[dict], candles_1h: list[dict] | None, candles_4h: list[dict] | None,
            candles_daily: list[dict] | None, hero_direction: str | None) -> dict[str, Any]:
    """`hero_direction` is the Hero's OWN already-decided bias (BULL/BEAR/
    None, from confluence.py's signal) — this function only checks
    agreement against it, it never computes or overrides the Hero's
    decision (Rule 11: One Hero -> One Decision)."""
    per_tf: dict[str, dict[str, Any] | None] = {}
    for label in TF_LABELS:
        if label in _RESAMPLE_MIN:
            series = resample(candles_1m, _RESAMPLE_MIN[label]) if candles_1m else []
        elif label == "1H":
            series = candles_1h or []
        elif label == "4H":
            series = candles_4h or []
        else:  # Daily
            series = candles_daily or []
        per_tf[label] = _tf_signals(series)

    ready = {k: v for k, v in per_tf.items() if v is not None}
    if not ready:
        return {"ready": False, "reason": "insufficient candle history across timeframes",
                "timeframes": {}, "note": "Waiting for enough bars at each timeframe."}

    hero_bias = "BUY" if hero_direction == "BULL" else "SELL" if hero_direction == "BEAR" else None
    agree_w = tot_w = 0.0
    for label, sig in ready.items():
        w = TF_WEIGHT[label]
        tot_w += w
        if hero_bias and sig["verdict"] == hero_bias:
            agree_w += w

    alignment_pct = round(agree_w / tot_w * 100, 0) if (tot_w and hero_bias) else None
    stars = max(1, min(5, round(alignment_pct / 20))) if alignment_pct is not None else None
    # Conflict = a HIGHER timeframe (1H/4H/Daily) disagrees with the Hero's
    # own bias. A lower-TF disagreement alone is NOT flagged as conflict —
    # lower timeframes are naturally noisier and disagreeing there is
    # normal, not a red flag.
    conflict = bool(hero_bias) and any(
        ready[label]["verdict"] not in ("NEUTRAL", hero_bias)
        for label in ("1H", "4H", "Daily") if label in ready
    )

    return {
        "ready": True,
        "timeframes": {label: {"verdict": sig["verdict"], "signals": sig["signals"]}
                       for label, sig in ready.items()},
        "missing_timeframes": [t for t in TF_LABELS if t not in ready],
        "alignment_pct": alignment_pct,
        "alignment_stars": stars,
        "higher_tf_conflict": conflict,
        "note": ("Real per-timeframe technicals, purely informational — never a decision, "
                 "never changes position sizing. Higher Timeframe Conflict is a display flag only."),
    }
