"""Market Event Engine — OBS-16, Step 1 (owner, 2026-08-05).

Per docs/V7_1_MARKET_EVENT_ENGINE_SPEC.md. STEP 1 ONLY: pure ring-buffer +
threshold logic, unit-testable against synthetic tick sequences. NOT WIRED —
no caller in this codebase invokes on_tick() yet. Wiring into _spot_tick()
is a separate step in the spec's own build order, needing its own approval.

WHY THIS EXISTS. V7 is state-oriented: every cycle computes
price -> indicators -> decision fresh from the current snapshot. Nothing
watches consecutive prices and says "a fast move just happened" — a 20-point
move over 8 seconds and the same 20 points drifting over 10 minutes look
identical to every existing engine. This module answers a narrow, different
question: did a SUDDEN move just happen, and how sudden.

WHAT IT IS NOT:
  * Not a signal, not a trade suggestion, not a probability the move
    continues. It reports what already happened, past tense, nothing more.
  * Not a replacement for candles.py/evidence_rank.py/structural_targets —
    those read completed 5-min bars; this reads the raw 2s tick stream
    (_spot_tick's cadence, per the spec's own audit of the fast vs slow
    loop) so it can measure something they structurally cannot: how FAST a
    move happened, not just that it happened.
  * Never claims volume or ATR context is fresher than it is — every event
    carries the timestamp of whatever atr_hint/volume was actually supplied,
    since both are known (per the spec) to lag the 2s price tick.

DECLARED thresholds — starting values, not fitted, not backtested. Same
discipline as candles.py's THRESHOLD_REGISTRY.
"""
from __future__ import annotations

from collections import deque
from typing import Any

THRESHOLD_REGISTRY = {
    "MIN_ATR_MULTIPLE": (1.5, "move must be >= this multiple of the last-known ATR"),
    "MIN_ABS_MOVE_PCT": (0.10, "AND >= this % of price — stops a huge-ATR "
                               "instrument's routine wiggle firing on the multiple alone"),
    "MAX_WINDOW_S": (30.0, "a move only counts as 'sudden' if it completes within this many seconds"),
    "MIN_VOLUME_MULT": (2.0, "if volume is fresh enough to check, require >= this "
                             "multiple of baseline to call it VOLUME_SHOCK specifically"),
    "DEDUPE_WINDOW_S": (60.0, "don't re-emit for the same still-unfolding move every tick"),
    "RING_SECONDS": (120.0, "how much tick history each symbol keeps"),
}
MIN_ATR_MULTIPLE = 1.5
MIN_ABS_MOVE_PCT = 0.10
MAX_WINDOW_S = 30.0
MIN_VOLUME_MULT = 2.0
DEDUPE_WINDOW_S = 60.0
RING_SECONDS = 120.0

# per-symbol tick ring: deque[(ts, price)]. Module-level state, same shape as
# confluence.py's _prev_ctx / memory.py's _tracked — a per-symbol dict the
# rest of the app reads through this module's functions, never directly.
_ticks: dict[str, deque[tuple[float, float]]] = {}
_last_emit: dict[str, float] = {}   # symbol -> ts of last emitted event (dedupe)


def _ring(symbol: str) -> deque[tuple[float, float]]:
    r = _ticks.get(symbol)
    if r is None:
        r = _ticks[symbol] = deque()
    return r


def _prune(ring: deque[tuple[float, float]], now: float) -> None:
    while ring and now - ring[0][0] > RING_SECONDS:
        ring.popleft()


def on_tick(symbol: str, price: float, ts: float,
           atr_hint: float | None = None,
           atr_as_of: float | None = None,
           volume_hint: float | None = None,
           volume_baseline: float | None = None,
           volume_as_of: float | None = None) -> dict[str, Any] | None:
    """Feed one price tick. Returns an event dict the instant a move clears
    the declared thresholds within MAX_WINDOW_S, else None.

    Pure bookkeeping over its own module-level ring buffers — reads no other
    live state. Never raises: a caller (once wired) must still wrap this in
    try/except per this session's standing contract for every additive
    observational engine (candles.py, evidence_rank.py, structural_targets),
    but this function itself is defensive against bad inputs (price<=0,
    NaN, non-monotonic ts) rather than relying solely on that wrapper.
    """
    if price is None or price <= 0 or ts is None:
        return None

    ring = _ring(symbol)
    _prune(ring, ts)

    if not ring:
        ring.append((ts, price))
        return None

    # Find the OLDEST tick still inside the window — the largest possible
    # move-so-far is measured from there, not just from the previous tick.
    # A slow grind that only recently accelerated is exactly what this must
    # NOT flag (that's drift, not a shock); anchoring at the window edge
    # keeps a genuinely gradual multi-minute move from ever looking sudden.
    window_start = ts - MAX_WINDOW_S
    anchor_ts, anchor_price = ring[0]
    for t, p in ring:
        if t >= window_start:
            anchor_ts, anchor_price = t, p
            break

    ring.append((ts, price))

    if anchor_price <= 0:
        return None

    duration_s = ts - anchor_ts
    if duration_s <= 0 or duration_s > MAX_WINDOW_S:
        return None

    absolute_move = price - anchor_price
    percentage_move = abs(absolute_move) / anchor_price * 100

    atr_multiple = None
    if atr_hint and atr_hint > 0:
        atr_multiple = abs(absolute_move) / atr_hint

    # Gate: BOTH an ATR-relative shock (when ATR is known) AND a minimum
    # absolute-percentage move — never either alone (spec's explicit
    # caution: a bare abs(delta) or a bare ATR-multiple each fail on some
    # instrument's routine scale).
    clears_atr = atr_multiple is not None and atr_multiple >= MIN_ATR_MULTIPLE
    clears_pct = percentage_move >= MIN_ABS_MOVE_PCT
    if atr_multiple is None:
        # No ATR context yet (e.g. before the first AI cycle completes) —
        # fall back to the percentage floor alone rather than refusing to
        # ever detect anything. Declared, not silent: reflected in the
        # returned event via atr_multiple: None.
        qualifies = clears_pct
    else:
        qualifies = clears_atr and clears_pct

    if not qualifies:
        return None

    last = _last_emit.get(symbol, 0.0)
    if ts - last < DEDUPE_WINDOW_S:
        return None

    volume_change = None
    if volume_hint is not None and volume_baseline and volume_baseline > 0:
        volume_change = volume_hint / volume_baseline

    event_type = "SPIKE"
    if volume_change is not None and volume_change >= MIN_VOLUME_MULT:
        event_type = "VOLUME_SHOCK"
    elif atr_multiple is not None and atr_multiple >= MIN_ATR_MULTIPLE * 1.5:
        event_type = "VELOCITY_SHOCK"

    _last_emit[symbol] = ts

    return {
        "event_type": event_type,
        "direction": "UP" if absolute_move > 0 else "DOWN",
        "price_before": round(anchor_price, 2),
        "price_after": round(price, 2),
        "absolute_move": round(absolute_move, 2),
        "percentage_move": round(percentage_move, 3),
        "duration_s": round(duration_s, 1),
        "atr_multiple": round(atr_multiple, 2) if atr_multiple is not None else None,
        "atr_as_of": atr_as_of,
        "volume_change": round(volume_change, 2) if volume_change is not None else None,
        "volume_as_of": volume_as_of,
        "timestamp": ts,
        "symbol": symbol,
        "note": ("Reports a move that already happened — no probability it "
                 "continues, no trade suggestion. atr_multiple/volume_change "
                 "are None when that context wasn't available yet, never "
                 "guessed; each carries its own _as_of timestamp because "
                 "both can lag the fresh price tick that triggered this."),
    }


def reset(symbol: str | None = None) -> None:
    """Test/ops utility — clears ring state for one symbol or all of them.
    Never called from the trading path."""
    if symbol is None:
        _ticks.clear(); _last_emit.clear()
    else:
        _ticks.pop(symbol, None); _last_emit.pop(symbol, None)
