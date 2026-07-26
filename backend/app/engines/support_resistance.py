"""Dynamic Support/Resistance Engine — Phase 2 kickoff (owner, 2026-07-23,
item #5) + Phase 2 full build (owner, 2026-07-23, "Entry Decision Platform"
priority list). Swing-point detection, clustering into levels, and
touch/bounce/break % from actual candle history — no fabricated strength,
every number traces back to a counted event.

Phase 2 additions (this pass):
  - CPR/floor-pivot formula (daily/weekly/monthly) — a fixed textbook
    calculation, not a fitted heuristic, so it needs no "tune from evidence"
    caveat the way the swing/cluster thresholds do.
  - Evidence join (VWAP / Gamma Wall / Volume Profile POC-VAH-VAL / CPR) —
    confluence check against levels this module ALREADY computed; reuses
    each source engine's own output, never re-derives them.
  - Premium S/R via premium_series.py's persisted tick log, reusing
    compute_levels() unchanged (bars in, bars out) — no second algorithm.
  - hero_card() / entry_workflow() — pure derivations over compute_levels()'
    own output. entry_workflow's terminal state is BUY_READY (evidence
    complete), never BUY — the Decision Engine remains the sole BUY/WAIT/EXIT
    authority (Prime Directive); this only feeds it a readiness signal, same
    as the existing buy_checklist / entry_score_timeline.

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
    """True once the persistence layer exists (premium_series.py, 2026-07-23) —
    infra-level readiness. Per-strike DATA readiness (enough bars today) is a
    separate, honest check inside premium_levels() itself, exactly like
    compute_levels()'s own 'ready'/'reason' fields — a global True here never
    claims any specific strike has enough history."""
    return True


def spot_levels(candles: list[dict[str, Any]], cmp: float | None = None) -> dict[str, Any]:
    """Public entry point — same as compute_levels, named for the API layer."""
    return compute_levels(candles, cmp)


# ── Premium S/R (owner, 2026-07-23) — reuses compute_levels() unchanged ─────
PREMIUM_BUCKET_S = 60   # 1-min synthetic bars from persisted ticks


def premium_levels(symbol: str, strike: int, typ: str, cmp: float | None = None) -> dict[str, Any]:
    """Same swing/cluster/touch/bounce/break math as spot, fed the strike's
    persisted premium ticks (premium_series.py) bucketed into synthetic bars.
    No second algorithm — compute_levels() doesn't know or care whether its
    input came from an index candle or an option premium tick."""
    from ..services import premium_series

    ticks = premium_series.read_today(symbol, strike, typ)
    bars = premium_series.to_bars(ticks, PREMIUM_BUCKET_S)
    result = compute_levels(bars, cmp)
    result["strike"], result["type"], result["symbol"] = strike, typ, symbol
    result["bars_available"] = len(bars)
    if not result["ready"]:
        result["reason"] = (f"insufficient premium history today ({len(bars)} of "
                             f"{2 * SWING_WINDOW + 5} 1-min bars needed) — builds "
                             "through the session, never fabricated from a thin sample")
    return result


# ── Pivot / CPR (owner, 2026-07-23) — fixed textbook formula, not a fitted
# heuristic, so it carries no "tune from evidence" caveat like the thresholds
# above. Standard floor-trader pivot: Pivot=(H+L+C)/3, BC=(H+L)/2, TC mirrors
# BC around Pivot. R1/S1..R3/S3 the usual derivations. ───────────────────────
def pivot_formula(high: float, low: float, close: float) -> dict[str, float]:
    if not (high and low and close):
        return {}
    pivot = (high + low + close) / 3.0
    bc = (high + low) / 2.0
    tc = 2 * pivot - bc
    rng = high - low
    return {
        "pivot": round(pivot, 2), "bc": round(min(bc, tc), 2), "tc": round(max(bc, tc), 2),
        "r1": round(2 * pivot - low, 2), "r2": round(pivot + rng, 2), "r3": round(high + 2 * (pivot - low), 2),
        "s1": round(2 * pivot - high, 2), "s2": round(pivot - rng, 2), "s3": round(low - 2 * (high - pivot), 2),
    }


def daily_cpr(prev_day_high: float, prev_day_low: float, prev_day_close: float) -> dict[str, Any]:
    return {"period": "DAILY", **pivot_formula(prev_day_high, prev_day_low, prev_day_close)}


def period_pivots(daily_candles: list[dict[str, Any]], period: str) -> dict[str, Any]:
    """Weekly/Monthly pivots from daily OHLC (broker.get_daily_candles()) —
    pure function, unit-testable against synthetic daily bars. period='W' or
    'M'. Uses the PREVIOUS complete period's H/L/C, same convention as daily CPR
    using yesterday's H/L/C, not today's in-progress one."""
    import datetime as _dt

    if not daily_candles:
        return {}
    buckets: dict[tuple, list[dict]] = {}
    for c in daily_candles:
        d = _dt.datetime.fromtimestamp(c["time"]).date()
        key = d.isocalendar()[:2] if period == "W" else (d.year, d.month)
        buckets.setdefault(key, []).append(c)
    keys = sorted(buckets)
    if len(keys) < 2:
        return {}
    prev = buckets[keys[-2]]     # previous COMPLETE period, not the in-progress one
    h, l, c = max(x["high"] for x in prev), min(x["low"] for x in prev), prev[-1]["close"]
    label = "WEEKLY" if period == "W" else "MONTHLY"
    return {"period": label, **pivot_formula(h, l, c)}


# ── Evidence join (owner, 2026-07-23) — confluence check against sources this
# module does NOT compute itself; each is read from its own owning engine's
# output, never re-derived. A level with more independently-agreeing sources
# is not "more confident" (no such score is invented) — it just lists what
# agrees, same discipline as the AI Decision Matrix's own PASS/FAIL rows. ───
def _recent_volume_spike(candles: list[dict[str, Any]], level: float, tol: float) -> bool:
    """Distinct from volume_node (POC/VAH/VAL confluence) — a raw volume
    surge on a candle that actually touched the level, recently."""
    if len(candles) < 6:
        return False
    recent = candles[-10:]
    vols = [c.get("volume", 0) for c in recent[:-1]]
    avg = sum(vols) / len(vols) if vols else 0
    if avg <= 0:
        return False
    for c in recent:
        near = (c["low"] - tol) <= level <= (c["high"] + tol)
        if near and c.get("volume", 0) >= VOL_CONFIRM_MULT * avg:
            return True
    return False


def _recent_price_action(candles: list[dict[str, Any]], level: float, tol: float) -> bool:
    """A rejection wick at the level in one of the last few candles — same
    'near' test as _touch_stats, just checked on recent candles only."""
    for c in (candles or [])[-5:]:
        near = (c["low"] - tol) <= level <= (c["high"] + tol)
        if not near:
            continue
        rng = max(c["high"] - c["low"], 1e-9)
        if (c["high"] - c["close"]) / rng > 0.5 or (c["close"] - c["low"]) / rng > 0.5:
            return True
    return False


def attach_evidence(levels_result: dict[str, Any], cmp: float,
                     vwap: float | None = None, gamma_wall: float | None = None,
                     volume_profile: dict[str, Any] | None = None,
                     cpr_lines: dict[str, Any] | None = None,
                     candles: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    if not levels_result.get("ready"):
        return levels_result
    tol = cmp * TOUCH_TOL_PCT / 100 if cmp else 0
    vp = volume_profile or {}
    cpr_vals = [v for k, v in (cpr_lines or {}).items() if isinstance(v, (int, float))]

    def _near(level: float, target: float | None) -> bool:
        return target is not None and abs(level - target) <= tol

    def _evidence(level: float) -> dict[str, Any]:
        # Owner Step 6 (Evidence Panel Final, 2026-07-26): dropped "swing"
        # (was hard-coded True for every row — "these ARE swing-clustered
        # levels" — not a real check, carried no evidentiary information).
        # Renamed "oi_wall" -> "gamma_wall": this field tests proximity to
        # the Gamma Wall (expiry.py), not open-interest buildup — the old
        # name implied a different signal than what it actually measured.
        ev = {
            "vwap": _near(level, vwap),
            "volume_node": _near(level, vp.get("poc")) or _near(level, vp.get("vah")) or _near(level, vp.get("val")),
            "cpr": any(_near(level, v) for v in cpr_vals),
            "gamma_wall": _near(level, gamma_wall),
            "volume": _recent_volume_spike(candles or [], level, tol),
            "price_action": _recent_price_action(candles or [], level, tol),
        }
        count = sum(1 for v in ev.values() if v)
        total = len(ev)
        # owner, 2026-07-24: an OBSERVED source-agreement ratio (how many of
        # the sources above independently agree), never a fabricated
        # "AI confidence" score — same discipline as bounce_pct/break_pct.
        return {**ev, "count": count, "total": total,
                "confidence_pct": round(count / total * 100, 1) if total else None}

    for row in levels_result.get("resistance", []) + levels_result.get("support", []):
        row["evidence"] = _evidence(row["level"])
    return levels_result


# ── Entry Workflow + Hero Card (owner, 2026-07-23) — pure derivations over
# compute_levels()' own output. Terminal state is BUY_READY (evidence
# complete), never BUY — the Decision Engine stays the sole BUY/WAIT/EXIT
# authority; this only feeds it a readiness signal, same role as the
# existing buy_checklist / entry_score_timeline. ────────────────────────────
WATCH_ZONE_PCT = 0.5     # within 0.5% of CMP = "watching" a level
VOL_CONFIRM_MULT = 1.5   # latest bar's volume >= 1.5x its own recent average

STAGES = ["WAIT", "WATCHING", "VOLUME_CONFIRM", "CANDLE_CONFIRM", "BUY_READY"]


def _volume_confirms(candles: list[dict[str, Any]]) -> bool:
    if len(candles) < 6:
        return False
    recent = [c.get("volume", 0) for c in candles[-21:-1]]
    avg = sum(recent) / len(recent) if recent else 0
    return avg > 0 and candles[-1].get("volume", 0) >= VOL_CONFIRM_MULT * avg


def _candle_confirms(candles: list[dict[str, Any]], level: float, tol: float, is_support: bool) -> bool:
    """Rejection: wick touches the level, close holds the expected side —
    the same 'near' + close-side test compute_levels() already uses for a
    touch's outcome, applied to just the latest candle."""
    if not candles:
        return False
    c = candles[-1]
    near = (c["low"] - tol) <= level <= (c["high"] + tol)
    if not near:
        return False
    return c["close"] > level + tol if is_support else c["close"] < level - tol


def entry_workflow(level_row: dict[str, Any], cmp: float, candles: list[dict[str, Any]],
                    is_support: bool) -> dict[str, Any]:
    """Stage machine for ONE level (call once for the hero level). Progressive
    gating — a later stage requires every earlier condition to still hold,
    not an independent path that could skip ahead."""
    level = level_row["level"]
    tol = cmp * TOUCH_TOL_PCT / 100 if cmp else 0
    dist_pct = abs(level - cmp) / cmp * 100 if cmp else 999
    touching = dist_pct <= TOUCH_TOL_PCT
    watching = dist_pct <= WATCH_ZONE_PCT
    vol_ok = touching and _volume_confirms(candles)
    candle_ok = vol_ok and _candle_confirms(candles, level, tol, is_support)

    stage = ("BUY_READY" if candle_ok else "VOLUME_CONFIRM" if vol_ok else
             "WATCHING" if watching else "WAIT")
    return {
        "stage": stage, "distance": round(abs(level - cmp), 2),
        "distance_pct": round(dist_pct, 3),
        "volume_confirmed": vol_ok, "candle_confirmed": candle_ok,
        "note": "Readiness signal only — the Decision Engine still decides BUY/WAIT/EXIT.",
    }


def hero_card(levels_result: dict[str, Any], candles: list[dict[str, Any]] | None = None) -> dict[str, Any] | None:
    """The single nearest actionable level — established (>=3 touches)
    preferred over a still-forming one at the same rough distance."""
    if not levels_result.get("ready"):
        return None
    rows = [(r, False) for r in levels_result.get("resistance", [])] + \
           [(r, True) for r in levels_result.get("support", [])]
    if not rows:
        return None
    cmp = levels_result["cmp"]
    rows.sort(key=lambda t: (not t[0]["established"], abs(t[0]["level"] - cmp)))
    row, is_support = rows[0]
    card = {
        "label": row["label"], "level": row["level"],
        "distance": round(abs(row["level"] - cmp), 2),
        "strength_score": row["strength_score"], "strength_stars": row["strength_stars"],
        "evidence": row.get("evidence"), "established": row["established"],
        "side": "SUPPORT" if is_support else "RESISTANCE",
    }
    if candles:
        card["workflow"] = entry_workflow(row, cmp, candles, is_support)
        card["action"] = card["workflow"]["stage"]
    return card
