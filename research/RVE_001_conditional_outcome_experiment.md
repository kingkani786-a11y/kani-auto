# RVE-001 — Conditional Outcome Validation Experiment

**Date:** 2026-08-02 · **Branch:** `v8-dev` · **Status:** Research Finding —
NOT a rule, NOT production, NOT merged
**Reproduce:** `python3 research/RVE_001_analysis.py --csv`

> **This is a research artifact, deliberately preserved including its negative
> result.** It records something that looked true, then turned out not to be —
> which is the most useful kind of finding to keep, and the easiest kind to
> lose if it isn't written down.

---

## Why this experiment existed

The owner's core ask, in their own framing: *"இந்த இடத்துல entry எடுத்தா 10
point, இந்த இடத்துல 20, இந்த இடத்துல 50."* — a point ladder that is about
**the setup in front of you right now**.

The dashboard already shows a point ladder:

```
⚡ Quick  5–10 pts   72%      🔥 Fast   10–20 pts  53%
⭐ Trend  20–40 pts  29%      💎 Runner 40–80 pts  12%      🚀 Mega 80–150  5%
```

But `opportunity_metrics.outcome_stats()` pools the **entire** black box into
one global base rate. Those percentages are identical for NIFTY and GOLD, for
a trending day and a chop day, for a perfect confluence setup and a bare one.
Confirmed empirically: every dashboard dump across a full session of live
review showed `72/53/29/12/5`, essentially unchanged.

**So the question:** do conditional patterns actually reach points at
materially different rates than that base rate? If yes → a Live Similarity
Engine (V9 Stage 2B) has real content to show. If no → no UI creates edge
that isn't in the data.

## Method

Deliberately **identical metric** to `outcome_stats()`, so every number here
is apples-to-apples with the ladder's own:

- **population** — episodes with `t_ignite` (alerted only)
- **reach @ N** — `potential >= N`, where `potential = peak − base`

Four tests, increasing rigour: T1 naive → T2 controlled → T3 within-day →
T4 does regime explain it.

## Data available (a real constraint, not a footnote)

| | |
|---|---|
| Total black-box records | 4,411 |
| Alerted (the ladder's population) | 3,619 |
| **Alerted WITH condition data** | **1,863** |
| Usable days | 5–7 |

Everything before 2026-07-22 has empty `engine.layers` (the known pre-fix
join bug), so roughly half the alerted history cannot be conditioned on at
all.

**Only 3 condition dimensions were testable:** `OI_BUILD/WEAK`,
`TREND_STRONG/WEAK`, `VWAP_ABOVE/BELOW` (+ regime/session as context).
CPR width, gamma wall, BOS/CHOCH, VIX, and Greeks exist **only on `v8-dev`,
which has never run live** — they have never been written to a single real
record, so this experiment says *nothing* about whether they carry edge.

---

## T1 — Naive across-day separation: looked like a strong YES

20pt reach, patterns with n≥30:

| Pattern | n | 20pt |
|---|---|---|
| `OI_BUILD·HIGH_MOMENTUM·TREND_STRONG·VWAP_ABOVE` | 46 | **58.7%** |
| `OI_BUILD·TRENDING·TREND_STRONG·VWAP_BELOW` | 123 | 50.4% |
| `OI_BUILD·TRENDING·TREND_STRONG·VWAP_ABOVE` | 259 | 43.6% |
| *base rate* | 3,619 | *27.4%* |
| `OI_WEAK·RANGE_BOUND·TREND_STRONG·VWAP_ABOVE` | 50 | 18.0% |
| `OI_WEAK·TRENDING·TREND_STRONG·VWAP_ABOVE` | 224 | **9.8%** |

Spread at 20pt: **48.9pp** (9.8% → 58.7%), a 6× ratio between best and worst,
with large samples on both ends. At this point the honest-looking read is
"Case A — patterns genuinely separate, build the Similarity Engine."

**That read is wrong.**

## T2 — Controlled: the "OI edge" is day-concentrated

Isolating the apparent star discriminator — identical conditions, only OI
differs:

| | n | days | **biggest-day share** | 20pt |
|---|---|---|---|---|
| `OI_BUILD` | 259 | 3 | **70.7%** | 43.6% |
| `OI_WEAK` | 224 | 2 | **71.4%** | 9.8% |

~183 of the 259 `OI_BUILD` rows are from **one day** (07-29); ~160 of the 224
`OI_WEAK` rows are from **a different single day** (07-27). That comparison is
not measuring OI — it is measuring **07-29 versus 07-27**.

## T3 — Within-day: the effect largely evaporates, and its direction flips

Hold the day fixed, compare core conditions inside it:

| Test | 20pt spread |
|---|---|
| T1 across-day (naive) | **48.9pp** |
| **T3 within-day (honest)** | **15.2pp average** |

Direction consistency of `OI_BUILD` vs `OI_WEAK`, per day:

| Day | OI_BUILD | OI_WEAK | winner |
|---|---|---|---|
| 2026-07-23 | 32.4% (n=111) | 37.1% (n=275) | WEAK |
| 2026-07-27 | 36.7% (n=30) | 9.3% (n=237) | BUILD |
| 2026-07-29 | 55.2% (n=250) | 68.9% (n=45) | WEAK |
| 2026-07-30 | 36.8% (n=345) | 34.0% (n=97) | BUILD |
| 2026-07-31 | 7.9% (n=139) | 8.8% (n=102) | WEAK |

**2 wins, 3 losses — a coin flip.** The single most impressive-looking
discriminator in T1 has no reliable direction once the day is controlled for.

## The dominant variable is the DAY

| Day | 20pt reach (all alerted) |
|---|---|
| 2026-07-31 | **8.3%** — nothing ran |
| 2026-07-27 | 12.4% |
| 2026-07-23 | 35.8% |
| 2026-07-30 | 36.2% |
| 2026-07-29 | **57.3%** — almost everything ran |

A **49pp** day-to-day swing — which is essentially the entire "pattern
separation" seen in T1. On 07-31 no setup reached 20 points; on 07-29 most did.

## T4 — But "day" is NOT captured by the current regime classifier

The owner's sharp caveat: *day ≠ calendar date*. For this to generalise, "day"
must mean a repeatable **market state** (High Momentum Day, Range Compression
Day…), so a future day can be matched to a past one. That is testable — and it
**fails** with the current 5-label regime taxonomy:

Same regime label, different days:

| Regime | across-day spread (20pt) | values |
|---|---|---|
| HIGH_MOMENTUM | **65.7pp** | 10.9% … 76.6% |
| EXPIRY_PINNING | **54.6pp** | 10.4% … 65.0% |
| TRENDING | **52.2pp** | 7.8% … 60.0% |
| RANGE_BOUND | 31.2pp | 0.0% … 31.2% |

Pooled across all days the ordering *is* sensible and intuitive:

| Regime | n | days | 20pt | 50pt |
|---|---|---|---|---|
| HIGH_MOMENTUM | 229 | 5 | 39.3% | 11.4% |
| TRENDING | 726 | 7 | 32.9% | 11.8% |
| EXPIRY_PINNING | 1,096 | 4 | 28.6% | 10.6% |
| RANGE_BOUND | 146 | 3 | 20.5% | 4.1% |
| LOW_MOMENTUM | 28 | 1 | 14.3% | 0.0% |

…a **25pp** between-regime spread. But the **within-regime, across-day spread
(52–66pp) is more than twice that**. The noise inside a regime label swamps
the signal between labels. `TRENDING` means 60% on one day and 7.8% on another.

---

## Finding

```
RESEARCH FINDING 001

  Naive pattern separation looked strong (48.9pp @ 20pt)
        ↓
  Confounded by day effect (70%+ single-day concentration)
        ↓
  Within-day the effect shrinks to 15.2pp, direction inconsistent (2-3)
        ↓
  The DAY dominates (8.3% .. 57.3% base) — but the current 5-label
  regime classifier does NOT capture it (52-66pp within-regime spread)
        ↓
  NEEDS: a better day-state descriptor before any similarity work
```

**What this does NOT say:** it does not say conditions never matter, and it
does not say the Similarity Engine is a dead idea. It says the *conditions
currently recorded*, at the *thresholds currently declared*, over *5 usable
days*, do not separate reliably once day is controlled — and that the regime
labels available today are too coarse to stand in for "what kind of day is
this."

## Consequences for V9

- **Do NOT build the Live Similarity Engine on these conditions yet.** On this
  evidence it would be matching on features that don't reliably separate.
- The V9 design itself is not invalidated — its *inputs* are. The likely
  prerequisite is a **day/market-state descriptor good enough that the same
  state predicts similar outcomes on different days**, which the current
  regime engine demonstrably is not.
- **Untested hypotheses** for what such a descriptor might use (recorded as
  open questions, NOT recommendations, NOT evidence): realised intraday
  volatility, opening-range expansion, India VIX level/change, breadth,
  cumulative delta. None of these has been measured against reach-rate.

## Caveats (all load-bearing)

1. **5 usable days.** Nothing here is stable evidence; a single new day could
   move any of these numbers materially.
2. **3 condition dimensions only.** CPR width, gamma wall, BOS/CHOCH, VIX,
   Greeks have never run live — completely untested, not "found unhelpful".
3. **Declared, unvalidated thresholds** (`OI≥60`, `Trend≥60`). The real
   separation may sit at a different cut-point entirely.
4. **`potential = peak − base` is idealised** — the best price that existed,
   not an achievable fill. The system places no orders, so no realised P&L
   exists anywhere in this dataset.
5. **In-sample.** No walk-forward, no out-of-sample split. That is precisely
   what `walk_forward_patterns.py` exists for, and it was not run here.
6. Alerted-only population, matching the ladder — unalerted moves excluded.

## Boundaries respected

No production code, dashboard, PQI, Walk-Forward, or Promotion Gate was read
from or written to. This directory is standalone and imported by nothing.
