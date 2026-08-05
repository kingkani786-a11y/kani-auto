# Market Event Engine — OBS-16 Specification

**SPECIFICATION ONLY. Nothing in this document is built.** Written 2026-08-05
per the owner's explicit request to scope OBS-16 (recorded 2026-08-04,
`docs/V7_STATUS.md` line 882) before any code is written. No implementation
should start from this document without a separate, explicit approval on
the diff plan that follows it — same discipline as every other V7.1 item
this session (Candle Pattern, Evidence Ranking, Structural Targets).

---

## The gap, restated precisely

V7 is state-oriented, not event-oriented. Every cycle computes
`price → indicators → decision` fresh from the current snapshot. Nothing
watches consecutive snapshots and says *"a fast move just happened"* — a
20-point move over 8 seconds and the same 20 points drifting over 10
minutes look identical to every existing engine, because both just end at
"current price is X+20."

---

## Audit: what's actually available to build this on

This is the part a spec written without reading the code would get wrong.

### The fast hook already exists — `_spot_tick()`

`backend/app/services/market_service.py:297-360`. Runs every
**`spot_interval` = 2.0s** (`config.py:19`), cheap LTP-only call. Writes
`state.spot = {ltp, change, tick_dir, volume, ts, ...}` every tick. This is
the *only* place in the codebase with sub-30-second price resolution — the
full confluence cycle (`_ai_cycle`) only runs every **`ai_interval` = 30.0s**
(`config.py:22`). A detector built on `_ai_cycle` snapshots (30s apart)
cannot honestly report "8 second duration" the way the owner's own example
output does — it would be sampling artifact dressed as precision.
**The engine must hook `_spot_tick`, not `_ai_cycle`.**

There is already a precedent for exactly this kind of hook:
`self.lifecycle.on_tick(ltp)` at `market_service.py:358` — a per-tick
observer called from inside `_spot_tick`, whose return value gates a
`manager.broadcast("lifecycle", snap)`. A `market_event.on_tick(ltp, ts)`
call added the same way, at the same call site, is the natural — and
minimal — integration point.

### The honest constraint this creates: volume lags price

`_spot_tick`'s heavy quote (which carries `volume`) only refreshes every
30s (`market_service.py:299,318`); the cheap per-2s tick is LTP-only. So a
"Volume 3.1× baseline" figure in an event record is *necessarily* up to
~30s stale relative to the price move that triggered the event. The spec
must say this plainly on the event record itself — never let a fresh-
looking price event carry a silently-stale volume confirmation.

### The other honest constraint: ATR normalization is also stale

The owner's own design caution (already recorded) requires **absolute move
+ normalized move (move / ATR) + speed** — never a bare `abs(delta) > N`.
But ATR (`atr_v`) is only computed inside `_ai_cycle`'s slower loop
(`confluence.py`), not per-tick. Normalizing a fresh 2s price move against
an ATR that can be up to 30s old is a real tradeoff, not a flaw to hide —
document it as "ATR as of the last completed AI cycle," same honesty
`orderflow.py`'s `low_data` flag (OBS-11, just shipped) already practices
for a different staleness case.

### Existing precedent for the per-symbol "previous cycle" pattern

`confluence.py:244` — `_prev_ctx[symbol] = {"iv": iv_now, "atr": atr_v}`,
already used for regime phase-transition deltas. Confirms the codebase's
established shape for "compare this cycle to the last one, keyed by
symbol" state. The Market Event Engine needs its own state (a short ring
of recent ticks per symbol, not a single previous value) since detecting a
move needs a *window*, not just a t-1 comparison — but the per-symbol
dict-keyed pattern itself should be reused, not reinvented.

---

## Design

### Module: `backend/app/engines/market_event.py` (new, additive)

Pure-ish module holding one per-symbol ring buffer of recent
`(ts, price)` ticks (e.g. `deque(maxlen=60)` ≈ last 2 minutes at 2s
cadence) and the detection logic. No live-state reads beyond what's passed
in — same "pure function over its inputs" discipline as
`support_resistance.structural_targets()`.

```python
def on_tick(symbol: str, price: float, ts: float, atr_hint: float | None) -> dict | None:
    """Called from _spot_tick, once per tick. Returns an event dict the
    instant a move clears the declared thresholds, else None. Pure
    ring-buffer bookkeeping; never blocks, never raises past its own
    try/except (mirrors every other observational engine this session)."""
```

An emitted event is a `dict`, never mutates trading state:

```
{
  "event_type":        "SPIKE" | "VELOCITY_SHOCK" | "VOLUME_SHOCK",
  "direction":         "UP" | "DOWN",
  "price_before":       ...,
  "price_after":        ...,
  "absolute_move":      ...,
  "percentage_move":    ...,
  "duration_s":         ...,        # wall-clock span the buffer covers
  "atr_multiple":       ... | None, # None if no atr_hint available yet
  "atr_as_of":          <timestamp of the AI cycle that produced atr_hint>,
  "volume_change":      ... | None, # None if the 30s-cadence volume hasn't refreshed
  "volume_as_of":       <timestamp>,
  "confidence_before":  ... | None, # from state.decision at buffer-start, if available
  "confidence_after":   ... | None, # from state.decision at emit time
  "timestamp":          ts,
}
```

`confidence_before`/`confidence_after` are opportunistic — pulled from
whatever `state.decision` held at each end of the window. They are NOT
computed by this engine and it must never claim they are; if `state.decision`
is stale or absent at either end, the field is `None`, not guessed.

### DECLARED thresholds (not fitted, not tuned from any backtest yet)

Following the exact discipline `candles.py`'s `THRESHOLD_REGISTRY` and
`opportunity_metrics.py`'s established constants already use:

| Constant | Starting value | Meaning |
|---|---|---|
| `MIN_ATR_MULTIPLE` | 1.5 | move must be ≥1.5× the last-known ATR to count as a shock, not routine noise |
| `MIN_ABS_MOVE_PCT` | 0.10 | AND ≥0.10% of price — stops a huge-ATR instrument's routine wiggle from firing on the multiple alone |
| `MAX_WINDOW_S` | 30 | a move is only "sudden" if it completes within this many seconds |
| `MIN_VOLUME_MULT` | 2.0 | if volume data is fresh enough to check, require ≥2× baseline to call it VOLUME_SHOCK specifically (SPIKE/VELOCITY_SHOCK can fire without this — volume may simply not be fresh) |
| `DEDUPE_WINDOW_S` | 60 | don't re-emit for the same still-unfolding move every tick |

Every one of these must ship in a `THRESHOLD_REGISTRY`-style dict, marked
declared-not-fitted, exactly like every other threshold this session has
added (`candles.py`, `evidence_rank.py`, `support_resistance.py`).

### Wiring — additive only, one call site

```python
# market_service.py, inside _spot_tick(), alongside the existing
# self.lifecycle.on_tick(ltp) call:
try:
    from ..engines import market_event
    ev = market_event.on_tick(inst.symbol, ltp, now,
                              atr_hint=state.intelligence.get("layers", {})
                                                          .get("trend", {})
                                                          .get("atr"))
    if ev:
        state.market_events.append(ev)   # new small ring, e.g. deque(maxlen=50)
        await manager.broadcast("market_event", ev)
except Exception:
    pass   # observation must never break the spot loop — same contract as
           # every other additive hook this session (memory.track_signal,
           # candles.py, evidence_rank.py all wrap identically)
```

**This never touches**: Kill Switch, calibration, any veto, any score,
`_ai_cycle`, `confluence.run()`. It is a sibling observer on the fast tick
loop, not a participant in the decision pipeline. Confirming this with the
same present-vs-stubbed byte-identical-packet test used for Phase 3A is
part of the build's own acceptance gate, not optional.

### Dashboard (deferred to the build phase, sketched here only)

A compact strip, not a new large panel — placed above the existing
decision line per the owner's original sketch:

```
⚡ MARKET EVENT — NIFTY +20.4 pts in 8s — Volume 3.1× (as of 14s ago) —
   1.7× ATR (as of last cycle) — Confidence 68 → 76
```

Rule 11 intact: this narrates what the market did, never what to do about
it. `Decision: WAIT — Reason: Premium + Greeks veto` stays on its own line,
unconflated, exactly as the owner's original sketch specified.

### Persistence (owner's now-standard pattern for this session's items)

Mirrors Phase 3A's `structural_targets` persistence exactly: events append
to a small ring (`state.market_events`, separate from `_tracked`/
`_outcomes`) and, if useful, get attached to `memory.track_signal()`'s
per-signal record as `market_events_during_window: list`. **Never** feeds
`_settle()`'s PnL/calibration math — same non-negotiable boundary already
enforced for `dna` and `structural_targets`.

---

## What this explicitly does NOT do

- Does not compute a probability that the move continues.
- Does not suggest a trade, entry, or exit.
- Does not change ATR, targets, thresholds, or any existing engine's score.
- Does not backfill historical events retroactively — it only detects going
  forward from whenever it's deployed. (A separate, later question: whether
  to also mine `data/opportunity_log`'s existing tick history for past
  events — out of scope here.)
- Does not claim volume or ATR context is fresher than it actually is —
  every event record carries the honest `_as_of` timestamp for both.

## Build order, if/when approved

1. `market_event.py` — pure ring-buffer + threshold logic, unit-testable
   against synthetic tick sequences (fast spike, slow drift, no-fire cases).
2. Wire the single `_spot_tick()` call site + `state.market_events` ring.
3. Broadcast channel + minimal dashboard strip.
4. Persistence hook into `track_signal()`, same pattern as `structural_targets`.
5. Regression: present-vs-stubbed byte-identical packet proof (mandatory,
   same as every other item this session); confirm `_spot_tick`'s existing
   behavior (lifecycle alerts, paper mark-to-market, audit.on_tick) is
   unaffected when `market_event.on_tick` is added alongside them.

Each step gets its own diff plan and its own approval before code, per the
standing discipline — this document scopes the *what*, not a green light
to build it now.
