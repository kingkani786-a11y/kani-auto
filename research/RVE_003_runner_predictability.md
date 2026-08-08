# RVE-003 — Opening-Range Runner Predictability

**Date:** 2026-08-08 · **Branch:** `main` · **Status:** Research Finding —
**NEGATIVE**. NOT a rule, NOT production, NOT wired to any live path.
**Reproduce:** `cd backend && python3 ../research/RVE_003_analysis.py`
**Data:** 5 index symbols × ~122 trading days of real Dhan 1-min candles
(2026-02-09 → 2026-08-08), cached under `data/orfe_research/`
**Follows:** RVE-001, RVE-002 (on `v8-dev`). Same discipline, different
subject — those studied premium-radar patterns; this studies the ORFE
Opening-Range setup on `main`.

---

## Why this exists

**So nobody re-runs this feature sweep in six months and rediscovers
nothing.** A negative result that isn't written down gets re-tested. This
documents both what was tested and — equally important — what was not, so a
future reader does not mistake *"not found in this feature set"* for
*"provably unpredictable"*.

## The question

The ORFE Opening-Range breakout-and-retrace setup showed mild positive
expectancy that is **overwhelmingly concentrated in rare large winners**.
If those winners could be identified in advance — at 09:30, before entry —
the setup would become far more tradeable.

**Can they?**

---

## Finding 1 — The fat tail is real, and extreme

Fixed 0.618 entry, one consistent rule, 279 resolved trades across 5 symbols:

| | R |
|---|---|
| min | −1.00 |
| p25 | **−1.00** |
| median | +0.68 |
| p75 | +1.12 |
| max | +2.97 |

**28 of 279 trades (10%) produce 89% of all profit** — +72.0 R of +81.2 R total.

A quarter of all trades are full stop-outs. The median trade is modestly
positive. Essentially the entire return comes from one trade in ten.

## Finding 2 — Nothing measurable at 09:30 predicts them

Six features, **pre-declared before looking at outcomes** and all reported
regardless of result:

| Feature | Runners (28) | Rest (251) | Ratio |
|---|---|---|---|
| OR width % | 0.407 | 0.465 | 0.88× |
| Gap % | −0.140 | 0.066 | — |
| OR volume share | 8.886 | 9.572 | 0.93× |
| ADX | 31.35 | 32.70 | 0.96× |
| RSI | 46.20 | 52.00 | 0.89× |
| ATR | 27.10 | 25.40 | 1.07× |

**Every ratio sits within ~12% of 1.0.** No separation.

Categorical splits mirror their base rates almost exactly:

- **Regime** — runners 71% TRENDING vs rest 63% TRENDING
- **Symbol** — 4–8 runners each, proportional to each symbol's share
- **Bias** — runners 17 PUT / 11 CALL vs rest 120 PUT / 131 CALL

### Two tempting numbers that must be resisted

1. **|gap%| 0.476 (runners) vs 0.315 (rest)** — looks like 1.5×. On 28
   events with medians this small, a handful of trades moves it. Six
   features were tested; one looking elevated is the *expected* outcome of
   six draws, not evidence.
2. **RSI lower + PUT-skewed runners** — 17 vs 11 is a coin-flip result at
   n=28.

Reporting either as a finding would repeat exactly the RVE-001 failure mode,
where a naive 48.9pp spread survived four confound layers before collapsing
to nothing.

---

## Operational conclusion (this is the part that changes behaviour)

**If runners cannot be filtered for at entry, then entry precision is not
the lever — survival is.**

Concretely, for this setup as it stands:

1. **Size every qualifying entry the same.** There is no measured basis for
   sizing up on a "better-looking" setup, because no measured feature makes
   one setup look better. Discretionary conviction-sizing here would be
   acting on noise, and worse, it would most likely *underweight* the very
   trades that carry the return — the runners look statistically ordinary
   at 09:30.
2. **Stop discipline on the 90% that don't run is the only remaining lever.**
   With p25 = −1.00 R, a quarter of trades reach a full stop. Letting any of
   those exceed 1 R directly consumes the tail's contribution. The 89%/10%
   concentration means the arithmetic is unforgiving: loosening stops to
   "give it room" degrades the whole edge, because the extra room does not
   convert ordinary trades into runners — nothing about them was different.
3. **Holding through is mandatory, not optional.** Since runners are only
   identifiable *after* they run, any rule that exits early on the average
   trade will preferentially truncate the trades that were about to become
   the 10%.

This shifts the problem from *signal selection* to *risk management and hold
discipline*. That is a genuinely different engineering target than "build a
better entry filter", and it is where effort should go next for this setup.

---

## What was NOT tested (do not read this doc as "permanently unpredictable")

This experiment tested **only features knowable at 09:30 from opening-range
candle data on the instrument itself**. The following were out of scope and
remain open questions — their absence here is a scope limit, not a negative
result:

| Not tested | Why it might matter | Blocker |
|---|---|---|
| **Broader market context on runner days** — NIFTY/BANKNIFTY correlation, cross-index divergence at 09:30 | Runner days may be market-wide events rather than instrument events; 69% day-overlap between symbols hints the day matters more than the symbol | Needs a cross-symbol same-timestamp join, not built |
| **FII/DII flow** | Institutional flow is the standard candidate for what makes a day trend all session | No data source connected |
| **India VIX level and term structure** | Volatility regime plausibly gates whether a breakout extends or fades | VIX is fetched live but **no historical VIX pull exists** in this codebase |
| **Option-chain state at 09:30** — OI build, PCR, gamma positioning | Dealer positioning is a real mechanism for sustained directional moves | Dhan serves **no historical option chain**; only forward-collected live data could answer this |
| **Prior-day structure** — close location, prior-day range, consecutive-day patterns | Multi-day context is absent from a single-session feature set | Computable from cached candles; simply not in scope today |
| **Time-of-day of the breakout** | An early breakout may behave differently from a 14:00 one | Computable; not in scope today |

The cheapest of these to attempt next are **prior-day structure** and
**breakout time-of-day** — both derivable from candles already cached, with
no new data source.

---

## Sample-size honesty

- 279 resolved trades over ~122 trading days across 5 symbols.
- **These are NOT 279 independent observations.** Mean pairwise day-overlap
  between symbols is **69%**; on 83 of 120 days, four or five symbols all
  produced a setup. NIFTY↔SENSEX overlap is 92%. Five correlated Indian
  equity indices on the same sessions carry far less information than the
  raw count suggests.
- The runner subgroup is **n=28**. Six features on 28 events is at the edge
  of what this sample can honestly support, which is precisely why the two
  elevated-looking features above are reported as noise rather than signal.
- No brokerage, slippage or spread is modelled anywhere. Index points only —
  **not option premium P&L**, which is what is actually traded.

## Relationship to the same day's other findings

RVE-003 sits alongside two other results from 2026-08-08, all on the same
dataset:

1. **Fibonacci level selection shows no edge** — win rate tracks R:R almost
   perfectly inversely (0.236 → R:R 4.10, 15.9% wins; 1.0 → R:R 0.21, 80.2%
   wins). Four of six levels performed *worse* than a zero-edge null at their
   own R:R.
2. **A data-fitted dynamic entry zone lost to a plain fixed level
   out-of-sample** (0.788 vs 1.178 mean R) — fitting to "where pullbacks
   usually turn" pushes entry shallow, widening the stop and shrinking R.
3. **RVE-003 (this doc)** — and the runners that carry the whole distribution
   are not predictable from the opening range either.

Taken together: **entry-side optimisation for this setup is exhausted at the
current evidence level.** What survived is that the structure itself is
mildly positive and fat-tailed. Do not re-litigate the entry question without
genuinely new data — new feature *families* (the table above), or a test
sample past the owner's 100-day / 500-**independent**-signal bar.

---

*Read-only research. No threshold, gate, weight or live decision path was
modified to produce this document. The backtest it draws on is gated
`BACKTEST_ONLY` with `unlocked_for_decisions = false`.*
