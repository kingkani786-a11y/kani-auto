# Cloud AI Trade Explorer — Evidence-Driven Adaptive Entry Engine

**SPECIFICATION ONLY. Nothing in this document is built.** Authored by the
owner, 2026-08-04, during `V7.0 FROZEN · V7.1 BACKLOG OPEN`. Recorded here
so the design survives the session; **no code was written from it.**

---

## The objective, in the owner's own words

> AI should continuously search for the best-supported directional
> opportunity, identify what evidence is driving it, show the
> target/invalidation map, expose contradictions, and learn from actual
> outcomes — **without fabricating certainty**.

**The core architectural shift:** stop producing one opaque blended score.
Start producing *competing entry hypotheses*, each with its own evidence,
then rank them and **name the dominant driver**.

```
MARKET DATA → AI RESEARCH LAYERS → many ENTRY HYPOTHESES
   → each with Evidence + Historical Validation → AI RANKING
   → BEST-SUPPORTED ENTRY → ENTRY/TARGET/SL → EXECUTION GATE
```

Signal and Execution stay separate throughout (already begun — see V7.1
item #1, commit `b975034`).

### The intended surface

```
┌─────────────────────────────────────┐
│          AI TRADE EXPLORER          │
├─────────────────────────────────────┤
│ SIGNAL          BUY PE · 24450      │
│                                     │
│ PRIMARY BASIS   🟢 PRICE ACTION     │
│                                     │
│ SUPPORTING      ✓ Candle Pattern    │
│                 ✓ Historical Match  │
│                 ✓ Database Pattern  │
│                 ✓ Order Flow        │
│                                     │
│ CONTRADICTIONS  ⚠ Greeks            │
│                                     │
│ TARGET MAP      T1 / T2 / T3        │
│                                     │
│ EXECUTION       🔴 BLOCKED          │
│                 Reason: Calibration │
└─────────────────────────────────────┘
```

Classification vocabulary for every layer, per cycle:
`PRIMARY · SECONDARY · CONFIRMATION · CONTRADICTORY · INSUFFICIENT`.

---

## AUDIT BEFORE BUILD — what already exists

Run 2026-08-04 against `backend/app/engines/` (55 engines) and `v8-dev`.
This is the standing norm that has repeatedly cut scope (OBS-5 was ~80%
already built; 5 of the owner's 7 "decision clarity" items already
existed). **Result: roughly half of Phases 1–4 already exists in some form.**

| Spec layer | Status | Where |
|---|---|---|
| **Price Action** | ✅ substantial | `structure.py` — BOS/CHOCH, pivots, liquidity zones, `_stop_hunt()` sweep-and-reject, fibonacci, trendline |
| **Order Flow** | ✅ exists | `orderflow.py` — signed volume delta, aggression, absorption, liquidity vacuum (note OBS-11: its low-data default shares its real baseline) |
| **Greeks** | ✅ exists | `greeks.py`, delta-skew logic in `signal_engine.py` |
| **Volatility** | ✅ exists | `technicals.py` (ATR), India VIX layer, `gamma_shield.py` |
| **Market Structure** | ✅ exists | `structure.py`, `market_profile.py`, `volume_profile.py`, `support_resistance.py` |
| **Database Similarity** | ⚠️ **first version EXISTS** | `market_dna.py` — `_similarity()` (weighted categorical + numeric with tolerance decay), `_verdict()` (5 bands), `analyze()` over stored `dna` snapshots. **See the blocker below — this is the load-bearing issue.** |
| **Historical Match** | ⚠️ partial | `memory.historical_accuracy()` (regime-scoped), `opportunity_metrics` black box (`data/opportunity_log/`), `probability_ladder.py` |
| **Entry DNA / outcome persistence** | ⚠️ partial | `market_dna.snapshot()` is already stored per tracked signal; V8's `pattern_extractor.py` on `v8-dev` computes content-hashed `pattern_id`/`core_pattern_id` |
| **Setup performance by regime** | ⚠️ partial, isolated | V8 `pattern_stats.py` + `evidence_validator.py` + `pattern_ranking.py` (PQI) + `walk_forward_patterns.py` — **all on `v8-dev`, frozen, never merged** |
| **Candle Pattern engine** | ❌ **does not exist** | no engulfing / pin / inside-bar / exhaustion / multi-candle sequence detection anywhere |
| **Evidence ranking (primary vs confirming)** | ❌ does not exist | today everything blends into one composite |
| **Contradiction Engine** | ❌ does not exist | related: OBS-15 (per-trade vetoes unexplained), OBS-16 (no market-event capture) |
| **Evidence-based Target Engine** | ❌ does not exist | targets today are `ATR × fixed multiples (2.0/3.0/4.5)` in `confluence.py` — exactly the "fixed multiple" the spec says to replace |

**Practical consequence: the genuinely new build is smaller than it looks —
Candle engine, Evidence ranking, Contradiction engine, Target engine. The
rest is wiring existing engines into the hypothesis/evidence shape, plus
merging what `v8-dev` already proved out.**

---

## ⛔ THE BLOCKER — read before building Phase 5

**Phase 5 ("similar-event retrieval", "Database Similarity", the Live
Similarity Engine) is blocked by the owner's own research.** This is not a
new caution; it is a finding already committed under `research/` on
`v8-dev`:

- **RVE-001** — conditional patterns looked like they separated strongly
  (48.9pp at 20pt). After stripping four confound layers — day
  concentration, regime, symbol, and the unit of measurement itself — the
  separation did not survive.
- **RVE-002** — re-run with the metric fixed plus symbol and DTE controls:
  **DTE was the only descriptor that survived.** ADX, Trend, MTF and
  Liquidity showed correlations up to r = −0.95 and collapsed to 0.0–1.1pp
  once DTE was held fixed. **They were spurious.**

`market_dna._similarity()` weights exactly the kind of features RVE-002
found spurious. **A similarity engine built on them would retrieve
confident-looking matches with no demonstrated edge** — the precise failure
mode the "no fabricated confidence" doctrine exists to prevent.

**What unblocks it:** a real **Day State Descriptor**. One dimension (DTE)
is not a descriptor. The most promising untested candidates — VIX, IV Rank,
CPR width, gamma exposure, opening gap — **have never been written to a
single record**, so they are *untested, not disproven*. That is RVE-003,
and it needs fresh data that includes them.

**Therefore:** Phases 1–4 and 6 can proceed on their own merits. **Phase 5
must not ship a "% probability" or a match-based directional claim until
RVE-003 exists.** Until then the honest form is the one the owner already
specified:

> **Historical evidence: STRONG — 137/184 comparable cases moved in the
> same direction.**

Counts and denominators. Never a manufactured percentage presented as a
probability.

---

## Phases (owner's decomposition, unchanged)

| Phase | Contents |
|---|---|
| **1 — Entry Evidence Engine** | Price Action · Candle · Historical · Database · Order Flow · Greeks |
| **2 — Evidence Ranking** | primary driver · confirmations · contradictions · insufficient |
| **3 — Target Engine** | MFE · ATR · structure · liquidity · expected move · historical excursion |
| **4 — Adaptive Memory** | Entry DNA · outcome persistence · setup performance · regime performance |
| **5 — AI Research Layer** | similar-event retrieval · pattern discovery · setup ranking · explanation |
| **6 — Execution** | `SIGNAL` / `EXECUTION` / `REASON` |

**Phase 6 is already started** — V7.1 item #1 (`b975034`) added
`signal_candidate` + the `_blocked` ring + `SignalExecutionCard`, so a
blocked signal no longer collapses into a bare `NO TRADE`.

### Entry DNA record (owner's field list)

```
direction · primary · secondary · historical · database · order flow · greeks
market regime · time · DTE · entry · T1/T2/T3 · stop
outcome · MFE · MAE
```

Much of this already lands in `market_dna.snapshot()` and the
`opportunity_metrics` black box. The genuinely missing joins are the ones
V8 Phase 1/2 already added **on `v8-dev`** (CPR, gamma wall, Greeks,
planned SL/target, BOS/CHOCH, VIX, MFE/MAE, time-to-target, decay) — so
this is largely a **merge question, not a build question**.

### The self-update rule — non-negotiable

> AI **தன்னைத்தானே threshold மாற்றிக் கொள்ளக்கூடாது.**

Learning changes **ranking**, never thresholds. Any threshold change stays
on the existing path: Observation → Evidence → Proposal → **human
approval**. This is the same rule that governs OBS-10 today, and V8's
Promotion Gate (`promotion_gate.py`) already implements exactly this
discipline — 5 ANDed checks before a pattern is even allowed to cost
compute, and it honestly returned **0 of 10 promoted** on real data.

---

## Recommended build order

1. **Candle Pattern engine** — the only fully-absent Phase 1 layer; pure
   derivation over candles already in memory; no new data, no new API cost.
2. **Evidence Ranking + Contradiction engine** — turns the existing layer
   scores into `PRIMARY / CONFIRMING / CONTRADICTORY`. This is the change
   that actually answers *"எதுல entry கிடைச்சது"*, and it is presentation
   over data that already exists. Subsumes OBS-15.
3. **Target Engine** — replace the fixed `ATR × (2.0/3.0/4.5)` with
   structure/liquidity/historical-MFE-derived levels.
4. **Adaptive Memory** — mostly a `v8-dev` merge; needs its own approval
   since `v8-dev` is separately frozen.
5. **Phase 5 — hold for RVE-003.** Counts-only framing in the meantime.

**Governance for all of it:** every step is a V7.1 change-set against the
frozen V7.0 baseline, reviewed item by item, additive where possible, and
**touching no Kill Switch / Risk / Greeks / Premium threshold.** These are
live-tree, gate-adjacent files — an unattended auto-restart can activate
them before an explicit deploy approval (`feedback-no-live-tree-edits`),
so sequence deploys deliberately.

---

## One honest boundary on the whole design

This system can be made to **search harder, explain better, and learn from
outcomes**. It cannot be made to *guarantee* a correct entry, and the spec
is right to avoid claiming so. The owner's own closing formulation is the
standard to hold it to:

> *…without fabricating certainty.*

Everything above should be judged against that line.
