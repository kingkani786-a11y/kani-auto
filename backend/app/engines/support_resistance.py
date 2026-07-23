"""Dynamic Support/Resistance Engine — Phase 2 kickoff (owner, 2026-07-23,
item #5). Spot-levels calculation core: swing-point detection, clustering into
levels, and touch/bounce/break % from actual candle history — no fabricated
strength, every number traces back to a counted event.

Kickoff scope (owner: "calculation logic scaffolded and testable, UI can be
partial"): SPOT levels only. Premium S/R is explicitly deferred — see
`premium_levels_available()` below for why (no persisted full-session premium
series exists yet; premium_radar._tracks is a 200-tick rolling window, not
enough history for genuine touch-count stats, and fabricating one from thin
history would be exactly the invented-confidence the charter forbids).

Declared thresholds below (mirrors opportunity_metrics.py's own style):
tune from evidence once live data accumulates, never silently.
"""
from __future__ import annotations

from typing import Any

# ── declared thresholds ──────────────────────────────────────────────────────
SWING_WINDOW = 3       # bars each side that must NOT exceed a swing point
CLUSTER_TOL_PCT = 0.15 # swing prices within 0.15% of each other = one level
TOUCH_TOL_PCT = 0.10   # a candle within 0.10% of a level = a "touch"
REACT_BARS = 3         # bars after a touch examined to classify bounce/break
MIN_TOUCHES_STRENGTH = 3  # touches needed before a level is "established"


def _swing_points(candles: list[dict[str, Any]], window: int = SWING_WINDOW) -> tuple[list[float], list[float]]:
    """Fractal swing highs/lows: bar i is a swing high if its high is the max
    of the window [i-window, i+window] (and symmetric for lows)."""
    highs: list[float] = []
    lows: list[float] = []
    n = len(candles)
    for i in range(window, n - window):
        seg = candles[i - window: i + window + 1]
        h = candles[i]["high"]
        l = candles[i]["low"]
        if h == max(c["high"] for c in seg):
            highs.append(h)
        if l == min(c["low"] for c in seg):
            lows.append(l)
    return highs, lows


def _cluster(prices: list[float], tol: float) -> list[float]:
    """Merge nearby swing prices into one level (mean of the cluster)."""
    if not prices:
        return []
    prices = sorted(prices)
    clusters: list[list[float]] = [[prices[0]]]
    for p in prices[1:]:
        if p - clusters[-1][-1] <= tol:
            clusters[-1].append(p)
        else:
            clusters.append([p])
    return [sum(c) / len(c) for c in clusters]


def _touch_stats(candles: list[dict[str, Any]], level: float, tol: float,
                  react_bars: int = REACT_BARS) -> dict[str, int]:
    """Walk every candle; each time price comes within `tol` of `level`,
    classify the approach side (from the prior candle's close) and the
    outcome `react_bars` later: same side held = bounce/reject, opposite side
    closed = break. Ambiguous (no clear resolution within the window) is
    counted as neither — an honest "still forming", not forced into a bucket."""
    touches = bounces = breaks = 0
    n = len(candles)
    for i in range(1, n):
        c = candles[i]
        near = (c["low"] - tol) <= level <= (c["high"] + tol)
        if not near:
            continue
        prev_close = candles[i - 1]["close"]
        approached_from_below = prev_close < level
        touches += 1
        fut = candles[i + 1: i + 1 + react_bars]
        if not fut:
            continue
        last_close = fut[-1]["close"]
        if approached_from_below:
            if last_close > level + tol:
                breaks += 1        # broke UP through resistance
            elif last_close < level - tol:
                bounces += 1       # rejected back down
        else:
            if last_close < level - tol:
                breaks += 1        # broke DOWN through support
            elif last_close > level + tol:
                bounces += 1       # held, bounced back up
    return {"touches": touches, "bounces": bounces, "breaks": breaks}


def _strength(touches: int, bounce_pct: float | None) -> int:
    """Declared, tunable strength score (0-100) — touches carry more weight
    than bounce_pct early on (a level with 1 touch that always bounced is
    still unproven; consistency needs a sample)."""
    base = min(60.0, touches * 12.0)
    conviction = (bounce_pct or 0) * 0.4
    return int(round(min(100.0, base + conviction)))


def _stars(score: int) -> int:
    return max(1, min(5, 1 + score // 22))


def compute_levels(candles: list[dict[str, Any]], cmp: float | None = None) -> dict[str, Any]:
    """Core, pure function of `candles` — no live state read, fully unit-
    testable against synthetic OHLC. Returns spot R1-3/S1-3 ranked around cmp
    (defaults to the last candle's close)."""
    if not candles or len(candles) < (2 * SWING_WINDOW + 5):
        return {"ready": False, "reason": "insufficient candle history", "resistance": [], "support": []}

    cmp = cmp if cmp is not None else candles[-1]["close"]
    tol = cmp * TOUCH_TOL_PCT / 100
    cluster_tol = cmp * CLUSTER_TOL_PCT / 100

    highs, lows = _swing_points(candles)
    levels = _cluster(highs + lows, cluster_tol)

    scored = []
    for lvl in levels:
        st = _touch_stats(candles, lvl, tol)
        touches = st["touches"]
        resolved = st["bounces"] + st["breaks"]
        bounce_pct = round(st["bounces"] / resolved * 100, 1) if resolved else None
        break_pct = round(st["breaks"] / resolved * 100, 1) if resolved else None
        score = _strength(touches, bounce_pct)
        scored.append({
            "level": round(lvl, 2), "touches": touches,
            "bounce_pct": bounce_pct, "break_pct": break_pct,
            "strength_score": score, "strength_stars": _stars(score),
            "established": touches >= MIN_TOUCHES_STRENGTH,
        })

    resistance = sorted([s for s in scored if s["level"] > cmp], key=lambda s: s["level"])[:3]
    support = sorted([s for s in scored if s["level"] < cmp], key=lambda s: -s["level"])[:3]
    for i, r in enumerate(resistance):
        r["label"] = f"R{i + 1}"
    for i, s in enumerate(support):
        s["label"] = f"S{i + 1}"

    return {
        "ready": True, "cmp": round(cmp, 2),
        "resistance": resistance, "support": support,
        "note": (f"Swing-fractal levels (window={SWING_WINDOW}), clustered within "
                 f"{CLUSTER_TOL_PCT}% of CMP, touch tolerance {TOUCH_TOL_PCT}%. "
                 "Declared thresholds — tune from evidence as live data accumulates."),
    }


def premium_levels_available() -> bool:
    """Premium S/R needs a persisted full-session (ts, premium) series per
    strike to compute genuine touch/bounce/break stats. premium_radar._tracks
    only keeps a rolling window (deque maxlen=200, ~_LOOKBACK seconds) — not
    enough history for an honest 'N touches, X% bounce' claim. Returns False
    until a persisted premium series exists (Phase 2 dependency, tracked on
    the roadmap) — never fabricated from insufficient history."""
    return False


def spot_levels(candles: list[dict[str, Any]], cmp: float | None = None) -> dict[str, Any]:
    """Public entry point — same as compute_levels, named for the API layer."""
    return compute_levels(candles, cmp)
