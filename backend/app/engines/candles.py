"""Candle Pattern Engine — V7.1 Trade Explorer, Phase 1 layer (owner, 2026-08-04).

The only fully-absent Phase 1 evidence layer at the 2026-08-04 audit: nothing
in the 55 existing engines detected engulfing / pin / inside-bar / exhaustion /
multi-candle sequences. This fills that gap.

WHAT THIS DOES: detects candle structure over candles already in memory and
reports each detection WITH ITS CONTEXT. Pure derivation — no new broker call,
no new data source, no extra API cost.

WHAT THIS DELIBERATELY DOES NOT DO, and why:

  1. **No win rate, no probability, no "this pattern works N% of the time."**
     A pattern name alone is not evidence. The owner's own research is
     explicit on this (RVE-001/RVE-002 under research/ on v8-dev): features
     that looked strongly predictive — ADX, Trend, MTF, Liquidity, r up to
     -0.95 — collapsed to 0.0-1.1pp once DTE was held fixed. They were
     spurious. Attaching an invented hit-rate to "bullish engulfing" would
     repeat exactly that mistake, and would violate the standing "no
     fabricated probabilities/confidence" rule. Outcome statistics must come
     later, measured from the black box, per pattern, per regime.

  2. **It changes no score, no threshold, and no gate.** This layer is
     observational. Nothing here can make a blocked trade tradable or a
     rejected setup pass. Wiring it into the decision composite is a separate
     change that needs its own evidence and its own approval.

  3. **Context is reported alongside the pattern, never folded into it.**
     The spec's rule: "pattern + context + historical outcome" — a pin bar in
     the middle of a range and a pin bar rejecting a 5-star level are not the
     same event, and this engine says which one it saw rather than averaging
     them into a number.

Vocabulary is deliberately plain and matches the spec's own list.
"""
from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# DECLARED thresholds — every one is a stated convention, NOT a fitted or
# validated value. Named here in one block so they are auditable and so a
# future evidence pass knows exactly what to test. Same discipline as
# pattern_extractor.py's THRESHOLD_REGISTRY on v8-dev.
# ---------------------------------------------------------------------------
THRESHOLD_REGISTRY = {
    "MIN_CANDLES": (20, "bars needed before any detection is attempted"),
    "BODY_DOMINANT": (0.65, "body/range ratio at or above which a bar is 'decisive'"),
    "BODY_SMALL": (0.30, "body/range ratio at or below which a bar is 'indecisive'"),
    "WICK_DOMINANT": (2.0, "wick must be >= this multiple of the body to be a rejection"),
    "MOMENTUM_ATR": (1.3, "range >= this multiple of average range = expansion bar"),
    "EXHAUSTION_ATR": (2.2, "range >= this multiple = climax-sized bar"),
    "VOL_CONFIRM": (1.5, "volume >= this multiple of recent average = volume-confirmed"),
    "SEQUENCE_MIN": (3, "consecutive same-direction closes to call it a sequence"),
    "LEVEL_PROXIMITY_ATR": (0.35, "within this multiple of ATR counts as 'at' a level"),
}
MIN_CANDLES = 20
BODY_DOMINANT = 0.65
BODY_SMALL = 0.30
WICK_DOMINANT = 2.0
MOMENTUM_ATR = 1.3
EXHAUSTION_ATR = 2.2
VOL_CONFIRM = 1.5
SEQUENCE_MIN = 3
LEVEL_PROXIMITY_ATR = 0.35


def _anatomy(c: dict) -> dict[str, float]:
    """Body/wick geometry of one candle, normalised by its own range so the
    numbers are comparable across instruments (NIFTY ~24k vs GOLD ~141k)."""
    hi, lo = float(c["high"]), float(c["low"])
    op, cl = float(c["open"]), float(c["close"])
    rng = max(hi - lo, 1e-9)
    body = abs(cl - op)
    upper = hi - max(op, cl)
    lower = min(op, cl) - lo
    return {
        "range": rng, "body": body,
        "body_pct": body / rng,
        "upper_pct": upper / rng, "lower_pct": lower / rng,
        "upper": upper, "lower": lower,
        "bull": 1.0 if cl > op else 0.0,
        "close_loc": (cl - lo) / rng,      # 0 = closed on the low, 1 = on the high
    }


def _avg_range(candles: list[dict]) -> float:
    rs = [float(c["high"]) - float(c["low"]) for c in candles]
    return sum(rs) / len(rs) if rs else 0.0


def _avg_vol(candles: list[dict]) -> float:
    vs = [max(float(c.get("volume", 0) or 0), 0.0) for c in candles]
    return sum(vs) / len(vs) if vs else 0.0


def _add(out: list[dict], name: str, direction: str, note: str,
         strength: str, tags: list[str] | None = None) -> None:
    """`strength` is a DECLARED descriptor of the pattern's own geometry
    (how clean the shape is) — it is explicitly NOT a probability, a win
    rate, or a confidence that the trade will work."""
    out.append({"pattern": name, "direction": direction, "note": note,
                "geometry_strength": strength, "tags": tags or []})


def analyze(candles: list[dict], atr: float = 0.0,
            levels: dict[str, Any] | None = None) -> dict[str, Any]:
    """Detect candle structure on the most recent bars.

    `levels` (optional) may carry `support`/`resistance`/`vwap` floats so a
    detection can be reported as happening AT a level rather than in open
    space — the "pattern + context" half of the spec's rule.
    """
    if not candles or len(candles) < MIN_CANDLES:
        return {"ready": False, "patterns": [], "summary": "Building — need "
                f"{MIN_CANDLES} candles", "bias": "NONE", "count": 0,
                "note": "Detection only. No win-rate is claimed for any pattern."}

    recent = candles[-40:]
    last, prev = recent[-1], recent[-2]
    a, p = _anatomy(last), _anatomy(prev)
    avg_rng = _avg_range(recent[:-1]) or 1e-9
    avg_vol = _avg_vol(recent[:-1])
    vol_now = max(float(last.get("volume", 0) or 0), 0.0)
    vol_confirmed = bool(avg_vol and vol_now >= VOL_CONFIRM * avg_vol)
    rng_mult = a["range"] / avg_rng

    out: list[dict] = []

    # ---- engulfing: this body fully covers the previous body ----
    body_hi_now, body_lo_now = max(last["open"], last["close"]), min(last["open"], last["close"])
    body_hi_prev, body_lo_prev = max(prev["open"], prev["close"]), min(prev["open"], prev["close"])
    engulfs = body_hi_now >= body_hi_prev and body_lo_now <= body_lo_prev
    if engulfs and a["body_pct"] >= BODY_DOMINANT and p["body"] > 0:
        if a["bull"] and not p["bull"]:
            _add(out, "Bullish Engulfing", "BULL",
                 "This bar's body fully covers the previous down-bar's body.",
                 "clean" if a["body_pct"] >= 0.8 else "fair",
                 ["volume-confirmed"] if vol_confirmed else [])
        elif not a["bull"] and p["bull"]:
            _add(out, "Bearish Engulfing", "BEAR",
                 "This bar's body fully covers the previous up-bar's body.",
                 "clean" if a["body_pct"] >= 0.8 else "fair",
                 ["volume-confirmed"] if vol_confirmed else [])

    # ---- pin / rejection: one long wick, small body ----
    if a["body"] > 0 and a["body_pct"] <= BODY_SMALL:
        if a["lower"] >= WICK_DOMINANT * a["body"] and a["lower_pct"] >= 0.5:
            _add(out, "Rejection (lower wick)", "BULL",
                 f"Long lower wick — price was pushed down and rejected; "
                 f"closed in the upper {round(a['close_loc'] * 100)}% of the bar.",
                 "clean" if a["lower_pct"] >= 0.66 else "fair",
                 ["volume-confirmed"] if vol_confirmed else [])
        if a["upper"] >= WICK_DOMINANT * a["body"] and a["upper_pct"] >= 0.5:
            _add(out, "Rejection (upper wick)", "BEAR",
                 f"Long upper wick — price was pushed up and rejected; "
                 f"closed in the lower {round((1 - a['close_loc']) * 100)}% of the bar.",
                 "clean" if a["upper_pct"] >= 0.66 else "fair",
                 ["volume-confirmed"] if vol_confirmed else [])

    # ---- inside bar: full range contained by the previous bar ----
    if last["high"] <= prev["high"] and last["low"] >= prev["low"]:
        _add(out, "Inside Bar", "NEUTRAL",
             "Range fully inside the previous bar — compression, direction "
             "undecided. Often precedes expansion, but which way is not "
             "determined by the pattern itself.",
             "clean" if a["range"] <= 0.6 * p["range"] else "fair")

    # ---- momentum / expansion bar ----
    if rng_mult >= MOMENTUM_ATR and a["body_pct"] >= BODY_DOMINANT:
        d = "BULL" if a["bull"] else "BEAR"
        _add(out, "Momentum Bar", d,
             f"Range {rng_mult:.1f}x the recent average with a decisive body "
             f"({round(a['body_pct'] * 100)}% of range) — range expansion.",
             "clean" if rng_mult >= 1.8 else "fair",
             ["volume-confirmed"] if vol_confirmed else [])

    # ---- exhaustion / climax: outsized range but the close gives it back ----
    if rng_mult >= EXHAUSTION_ATR and a["body_pct"] <= BODY_SMALL:
        d = "BEAR" if a["close_loc"] < 0.4 else "BULL" if a["close_loc"] > 0.6 else "NEUTRAL"
        _add(out, "Exhaustion Bar", d,
             f"Climax-sized range ({rng_mult:.1f}x average) but a small body — "
             "the move was given back inside the bar.",
             "clean", ["volume-confirmed"] if vol_confirmed else [])

    # ---- consecutive directional closes ----
    seq_dir, seq_n = None, 0
    for c in reversed(recent):
        up = float(c["close"]) > float(c["open"])
        d = "BULL" if up else "BEAR"
        if seq_dir is None:
            seq_dir, seq_n = d, 1
        elif d == seq_dir:
            seq_n += 1
        else:
            break
    if seq_n >= SEQUENCE_MIN and seq_dir:
        _add(out, f"{seq_n} Consecutive {'Up' if seq_dir == 'BULL' else 'Down'} Bars",
             seq_dir,
             f"{seq_n} closes in the same direction — persistent one-way pressure. "
             "Persistence is not the same as continuation.",
             "clean" if seq_n >= 5 else "fair")

    # ---- pattern + CONTEXT: is this happening at a level? ----
    context: list[str] = []
    lv = levels or {}
    prox = LEVEL_PROXIMITY_ATR * (atr or avg_rng)
    close_px = float(last["close"])
    for key, label in (("support", "support"), ("resistance", "resistance"), ("vwap", "VWAP")):
        val = lv.get(key)
        try:
            v = float(val) if val is not None else None
        except (TypeError, ValueError):
            v = None
        if v and prox and abs(close_px - v) <= prox:
            context.append(f"at {label} {round(v, 2)}")

    # ---- net directional lean of what was detected (a COUNT, not a score) ----
    bulls = sum(1 for o in out if o["direction"] == "BULL")
    bears = sum(1 for o in out if o["direction"] == "BEAR")
    bias = "BULL" if bulls > bears else "BEAR" if bears > bulls else "NEUTRAL"

    if not out:
        summary = "No defined candle pattern on the latest bar."
    else:
        lead = out[0]
        summary = lead["pattern"]
        if context:
            summary += " " + ", ".join(context)
        if len(out) > 1:
            summary += f" (+{len(out) - 1} more)"

    return {
        "ready": True,
        "patterns": out,
        "count": len(out),
        "bias": bias,
        "bull_count": bulls,
        "bear_count": bears,
        "context": context,
        "volume_confirmed": vol_confirmed,
        "range_multiple": round(rng_mult, 2),
        "body_pct": round(a["body_pct"] * 100),
        "close_location_pct": round(a["close_loc"] * 100),
        "summary": summary,
        "note": ("Detection and geometry only. No win rate or probability is "
                 "attached to any pattern — outcome statistics have to be "
                 "measured per pattern per regime from the black box first "
                 "(see RVE-001/002: named features that looked predictive "
                 "were spurious once confounds were controlled). This layer "
                 "changes no score, threshold or gate."),
        "thresholds_declared": {k: v[0] for k, v in THRESHOLD_REGISTRY.items()},
    }
