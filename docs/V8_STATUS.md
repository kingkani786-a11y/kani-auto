# V8 Research Pipeline — Status

**2026-07-30: CODE FREEZE declared by owner.** No new V8 pipeline code until
2-4 weeks of fresh live-market data has accumulated through the Phase 1-2
joins (see "Why the freeze" below). Critical bug fixes only. This is a
`v8-dev`-only freeze — it does not touch the separate, already-standing
V7.0 production observation freeze on `main`.

## Pipeline built (all on `v8-dev`, isolated from `main`/production)

```
Black Box (opportunity_metrics.py, existing)
      │
      ▼
Phase 1  Dataset Enrichment       — cpr/gamma_wall/greeks/planned_sl+target/
      │                             bos_choch/vix joined into engine snapshot
      ▼
Phase 2  Outcome Join             — MFE/MAE/time-to-target/time-to-failure/
      │                             premium_decay per episode
      ▼
Phase 3A Pattern Extractor        — per-episode condition tags (pattern_extractor.py)
      │                             + pattern_id (regime/session baked in)
      │                             + core_pattern_id (regime/session excluded)
      ▼
Phase 3B Pattern Statistics       — occurrence/win%/avg MFE-MAE/timing per
      │                             pattern_id (pattern_stats.py)
      ▼
Evidence Validator                — 6 mechanical checks: sample size, days
      │                             observed, win-rate stability, single-day
      │                             concentration, min-tick pollution
      │                             (OBS-6), time-of-day concentration
      │                             (evidence_validator.py)
      ▼
Core Signature Validator          — same file: does a CORE pattern's win
      │                             rate hold across the different regimes/
      │                             sessions it appeared under?
      ▼
Phase 3C PQI Ranking              — weighted Pattern Quality Index (sample
      │                             size 20% / days observed 15% / win
      │                             stability 20% / cross-regime 15% /
      │                             cross-session 10% / MFE:MAE ratio 10% /
      │                             drawdown consistency 10%) + 5-band star
      │                             classification (pattern_ranking.py)
      ▼
Research Candidate Queue          — top 10 by PQI, filtered to a minimum
      │                             sample size
      ▼
Walk-Forward (candidate-only)     — chronological (by-day) folds, per-fold
      │                             Win Rate/Profit Factor/Expectancy/Max
      │                             Drawdown, verdict PASS/FAIL/UNSTABLE/
      │                             INSUFFICIENT_DATA (walk_forward_patterns.py)
      ▼
Promotion Gate                    — ANDs 5 checks (min sample, min days,
      │                             min PQI ≥80, Evidence VALIDATED,
      │                             Walk-Forward PASS) before anything is
      │                             allowed to cost Monte Carlo compute
      │                             (promotion_gate.py)
      ▼
Monte Carlo                       — NOT BUILT. Owner: pointless to build
      │                             before a single real pattern clears the
      │                             Promotion Gate.
      ▼
Proposal Engine                   — NOT BUILT.
      ▼
Human Approval → Implementation → Shadow Test → Production
```

## Why the freeze

Real historical black-box data (`data/opportunity_log/`) spans ~12-16 days,
and everything before 2026-07-22 (the bulk of it — the 2026-07-30 audit
found only 1,414 of 3,829 total records usable) predates Phase 1's actual
condition-tag joins entirely. Running today's Candidate Queue against that
data honestly returns **0 of 10 candidates promoted** — every one blocked
by Walk-Forward FAIL/INSUFFICIENT_DATA and mostly `NOT_VALIDATED` evidence.

That is the CORRECT, non-fabricated result of a real evidence pipeline —
not a bug to code around. Writing Monte Carlo or a Proposal Engine now
would have nothing legitimate to operate on. The owner's own words: *"No
real pattern has reached Walk-Forward PASS yet... இது உண்மையில் மிகவும்
நல்ல செய்தி"* (that's genuinely good news) — a research engine that
refuses to fake a PASS is the point, not a shortfall.

## What happens next

1. `v8-dev` stays code-frozen (bug fixes only) for **2-4 weeks**.
2. The live backend (once the owner connects broker credentials to a
   `v8-dev` instance — never `main`'s live process, per the standing
   cwd/dev-server safety rule) accumulates real, Phase-1/2/3-tagged
   opportunity episodes day by day.
3. After that window, re-run `pattern_ranking.research_candidate_queue()` →
   `walk_forward_patterns.run_walk_forward_on_queue()` →
   `promotion_gate.run_promotion_gate()` against the fresh data.
4. Only once a real pattern reaches `PROMOTED_TO_MONTE_CARLO` does Monte
   Carlo get built — designed against an actual promoted candidate's real
   shape, not a hypothetical one.
5. Proposal Engine is built only after that, and even then it only ever
   produces a proposal document for human review — never applies a change
   itself (EDAES Mode B, unchanged: production changes always need a
   fresh, explicit, per-action approval).

## Research track (allowed during the freeze — read-only, `research/`)

Research experiments are permitted during the freeze because they change no
production code, dashboard, PQI, Walk-Forward, Promotion Gate or Similarity
Engine — they only read the existing black box. Committed as **Research
Artifacts**, explicitly not rules and not merged.

| ID | Question | Result |
|---|---|---|
| **RVE-001** | Do conditional patterns reach point-targets differently than the Ladder's global base rate? | **Negative, after 4 confound layers.** Naive 48.9pp spread → day-concentration (70%+ one day) → within-day 15.2pp, direction coin-flip → regime doesn't capture day → **symbol** effect → metric itself not symbol-comparable. Carries a **V2 supersession note**; nothing deleted. |
| **RVE-002** | What defines a trading day, in a way that repeats? | **DTE is the only survivor.** NIFTY dte=0 26.4% / dte=1 12.1% / dte=4 6.2%; consistent across symbols and on the failure side (fewer false alerts at dte=0). **ADX/Trend/MTF/Liquidity all spurious** — up to r=−0.95, collapsing to 0.0–1.1pp once DTE is held fixed. |

**Consequence for V9:** the Live Similarity Engine is **blocked** until a
real Day State Descriptor exists. One dimension (DTE) is not a descriptor.
The V9 design isn't invalidated — its *inputs* are.

**Why this isn't final:** VIX, IV Rank, CPR width, gamma exposure and
opening gap — the descriptors most likely to define "what kind of day this
is" — have **never been written to a single record**. They are untested,
not disproven. Re-ask as **RVE-003** once fresh data includes them. This is
now an additional, concrete reason the freeze is worth waiting out.

**Recording requirements the research exposed** (needed before the question
can be asked properly, not features to build now):
1. **Premium ATR** — enables a true ATR-multiple metric, the professionally
   standard symbol-independent normalisation. Not currently computable:
   `engine.atr` is the *underlying's* ATR while `potential`/`peak_rise`
   describe the *premium*, so dividing them mixes units.
2. **`dte` on every record** — currently `None` on 1,633 of 3,619 alerted
   rows (added 2026-07-21).
3. VIX / IV Rank / CPR width / gamma exposure / opening gap.

Also produced **OBS-7** on `main` (logged, deliberately not fixed): the
Opportunity Ladder pools every symbol into one base rate, so a NIFTY trader
sees ~27.4% at 20pt where NIFTY's own measured rate is 13.9%.

## Known open design note (not a blocker)

`MIN_PQI_FOR_PROMOTION = 80.0`, the 40pp stability-spread tolerances, the
`MIN_BUCKET_SAMPLE = 10` regime/session-diversity floor, and every other
threshold introduced across Phase 3A-3C/Evidence Validator/Walk-Forward/
Promotion Gate are **declared, not fitted** — explicitly unvalidated
guesses (see each module's own `THRESHOLD_REGISTRY`/comments). The 2-4
week data-collection window is also the first real opportunity to check
whether any of them need adjusting — that should happen with evidence
before Monte Carlo, not be assumed correct indefinitely.

## Deferred: Research Dashboard v2 (owner, 2026-07-30 — build AFTER the
## freeze ends, not now; recorded here so it isn't lost over 2-4 weeks)

Three additions to `research_dashboard.py`, explicitly NOT to be built
during the current freeze:

- **Dataset Health**: new records today, total episodes, Alerted/Missed/
  False/Runner %, average MFE, average MAE.
- **Pattern Growth**: day-over-day delta in total pattern count (e.g.
  "Yesterday 46 → Today 53, +7").
- **Validation Funnel**: a single funnel view — Raw Patterns → Core
  Patterns → Validated → PQI > 80 → Walk-Forward PASS → Promotion Ready —
  showing the drop-off count at each stage.

All three are still pure aggregation over already-computed pipeline
outputs (no new evidence math), same spirit as the dashboard already
shipped — just not built yet because the freeze's point is to stop adding
code, even freeze-compatible code, and instead watch these numbers move
with real data first.
