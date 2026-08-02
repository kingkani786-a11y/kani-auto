# RVE-002 — Day State Descriptor Research

**Date:** 2026-08-02 · **Branch:** `v8-dev` · **Status:** Research Finding —
NOT a rule, NOT production, NOT merged
**Reproduce:** `python3 research/RVE_002_analysis.py`
**Follows:** RVE-001 (see its V2 revision note — this experiment is the reason
it needed one)

---

## The question RVE-001 left open

RVE-001 ended at: *what actually defines a trading day, in a way that
repeats?* The 5-label regime taxonomy demonstrably does not — within-regime
across-day spread was 52–66pp against only 25pp between regimes.

This experiment tests whether **continuous, recorded day-state features**
do better — after first fixing the measurement flaw RVE-001 uncovered.

## The metric fix (precondition)

RVE-001 measured `potential >= N` — **absolute premium points**. That is not
comparable across symbols:

| Symbol | median premium | 20 abs points means |
|---|---|---|
| NIFTY | ₹59 | a **34%** move |
| SENSEX | ₹106 | a 19% move |
| GOLD | ₹441 | a **4.5%** move |

RVE-002 uses **`peak_rise >= 30%`** — the premium's own percentage move,
which is symbol-independent.

**The owner's ATR-multiple proposal (move ÷ ATR) was NOT used — it is not
computable from recorded data.** `engine.atr` is the *underlying's* ATR
(index points, ≈0.1% of underlying: NIFTY 25.05 on 24181, GOLD 172 on
143182), while `potential`/`peak_rise` describe the *premium*. Dividing one
by the other mixes units. A true ATR-multiple needs the premium's own ATR
recorded — logged below as a future recording requirement.

## Controls applied (each one RVE-001 lacked)

**symbol** · **days-to-expiry (dte)** · **day**

---

## Finding 1 — DTE is the strongest descriptor found in either experiment

| | dte=0 | dte=1 | dte=4 |
|---|---|---|---|
| NIFTY `rose ≥30%` | **26.4%** (n=299) | 12.1% (n=223) | 6.2% (n=292) |
| SENSEX `rose ≥30%` | **32.1%** (n=769) | 11.6% (n=353) | — |

**Monotonic, ~4–5×, and consistent in direction across both symbols.** This
is the cleanest effect found anywhere in RVE-001 or RVE-002.

It also holds on the *failure* side, which is the fairer test — a metric that
only measures upside can flatter a high-variance condition:

| | rose ≥30% | FALSE alerts | median points lost |
|---|---|---|---|
| NIFTY dte=0 | 26.4% | **25.1%** | 0.60 |
| NIFTY dte=1 | 12.1% | 43.5% | 2.15 |
| NIFTY dte=4 | 6.2% | **56.8%** | 3.20 |
| SENSEX dte=0 | 32.1% | **29.8%** | 2.55 |
| SENSEX dte=1 | 11.6% | 43.9% | 8.40 |

Expiry-day ignitions are **both** more likely to become real moves **and**
less likely to be false alerts. (`FALSE` = alerted but never reached +10%,
a percentage-based classification, so it is not a premium-scale artifact —
unlike "median points lost", which partly is.)

## Finding 2 — every continuous feature tested was SPURIOUS, mediated by DTE

Day-level correlations looked striking at first:

| Feature | NIFTY r | SENSEX r |
|---|---|---|
| ADX | −0.21 | **−0.95** |
| Trend score | −0.81 | −0.91 |
| MTF score | −0.83 | −0.89 |
| Liquidity | −0.86 | −0.82 |
| ATR% | −0.35 | +0.42 |

An `r = −0.95` on ADX is the kind of number that gets a feature shipped.
**It does not survive controlling for expiry distance:**

```
Within dte=0 only, split at the median ADX:
  NIFTY   ADX low 26.2%  |  ADX high 26.2%   ->  0.0pp
  SENSEX  ADX low 32.9%  |  ADX high 31.8%   ->  1.1pp
```

The entire apparent ADX/Trend/MTF/Liquidity signal was DTE wearing a
disguise: high-`peak_rise` days simply *were* the dte=0 days (NIFTY 07-21
dte=0 → 25.7%; NIFTY 07-31 dte=4 → 6.6%; SENSEX 07-23 & 07-30 both dte=0 →
29.3% / 32.1%; SENSEX 07-22 & 07-29 both dte=1 → 18.7% / 7.8%).

**Four candidate day-state features, all eliminated by one control.**

## Finding 3 — residual day variation persists, still unexplained

After fixing the metric and controlling for symbol, day-to-day spread is
**NIFTY 20.7pp / SENSEX 24.3pp** (down from a naive 49pp). DTE accounts for
much of that, but not obviously all of it. Whatever remains is not captured
by anything currently recorded.

Time-of-day block: NIFTY 5.9pp (weak), SENSEX 14.1pp — but SENSEX's blocks
were **not** DTE-controlled, so that 14.1pp may be the same artifact again.
Untested; do not treat as a finding.

---

## What this means

```
RESEARCH FINDING 002

  Metric fixed (absolute pts -> % rise) — symbol confound removed
        ↓
  DTE is a real, monotonic, two-sided descriptor (4-5x, both symbols)
        ↓
  ADX / Trend / MTF / Liquidity: ALL spurious, mediated by DTE
        ↓
  Residual within-symbol day variation (~21-24pp) still unexplained
        ↓
  Day State Descriptor is NOT yet buildable from recorded features
```

**For V9:** the Day State Descriptor remains the correct prerequisite for a
Similarity Engine, and it remains **unbuildable today** — not because the
idea is wrong, but because the only descriptor that survives scrutiny (DTE)
is a single dimension, and every other recorded candidate collapsed under
one control.

**For the owner's original question** (*"where do I enter to catch 10 / 20 /
50 points?"*): on this evidence, **expiry distance is far more predictive of
whether a large percentage move is available than any confluence condition
tested so far.** That is a genuine, evidence-backed observation — and it is
one input, not a strategy.

## Recording requirements this exposes (for when the freeze lifts)

Not recommendations to build — data that must exist before the question can
even be asked properly:

1. **Premium ATR** (or the underlying move per episode) — makes a true
   ATR-multiple metric possible, which is the professionally standard
   symbol-independent normalisation.
2. **dte on every record** — currently `None` on 1,633 of 3,619 alerted rows
   (added 2026-07-21; earlier rows lack it).
3. **VIX, IV Rank, CPR width, gamma exposure, opening gap** — the descriptors
   most likely to define "what kind of day this is", and *none of them has
   ever been written to a single record*. Untested, not disproven.

## Caveats

1. **5–7 usable days per symbol.** Two symbols with enough data (NIFTY,
   SENSEX). Nothing here is stable.
2. **dte available on only 55% of alerted rows.**
3. **Radar-conditional.** Every record is an episode the radar already
   flagged as igniting — so this describes *"given an ignition was
   detected"*, not the market at large.
4. **No realised P&L anywhere.** The system places no orders. `peak_rise` is
   the best price that existed, not a fill.
5. **Intraday episodes only** — expiry-day premiums decaying to zero at
   settlement is outside the episode window, so the dte=0 picture is
   incomplete on the far downside.
6. **In-sample.** No walk-forward.

## Boundaries respected

No production code, dashboard, PQI, Walk-Forward, Promotion Gate, or
Similarity Engine touched. `research/` imports only stdlib and is referenced
by nothing in `backend/`.
