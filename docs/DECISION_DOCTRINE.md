# DECISION DOCTRINE — the Constitution of Cloud AI Trader X Pro

*Locked 2026-07-08. Changes to this document require explicit owner approval.*

## TWO DOCTRINES — kept strictly separate

### 1. PROJECT DOCTRINE (software) — IMMUTABLE
Evidence decides · No auto weight change · Every decision gets a verdict ·
Git + Release Notes for every milestone · Documentation first.
These never change. They are not up for research.

### 2. TRADING DOCTRINE (market) — RESEARCH PARAMETERS
Entry threshold · Greeks threshold · Liquidity threshold · OI threshold ·
Confidence threshold · confirmation counts · window lengths.
These are NOT constitution — they are hypotheses. With repeated evidence
(Rule 9) they MAY change, but only through the approval pipeline below.

> Software stability and strategy adaptability are protected by never
> confusing the two lists.

## The 8 Permanent Engineering Rules

1. **No Feature without Evidence.**
2. **No Weight Change without Approval.**
3. **Every Decision gets a Verdict** (WINNER / LOSER / CAPITAL_SAVED / MISSED_WINNER).
4. **Every Verdict teaches the AI.**
5. **Historical creates Knowledge.**
6. **Live creates Experience.**
7. **Knowledge never overrides Experience** — production weights are driven only
   by validated live outcomes.
8. **Evidence decides the next version; we don't.**

## Rule 10 — One State → One Source → One Truth → Many Consumers

> Every real system state (Market Open/Closed, a metric's time window, a
> Greeks clock) is computed in exactly ONE place. Every UI component or
> backend module that needs it is a CONSUMER that reads that single source
> fresh — never recomputes it, never caches an independent copy that can
> drift. One State → One Source guarantees One Truth for however Many
> Consumers display it. No card may independently declare Failure for a
> state every other card correctly shows as calm, and no two consumers may
> silently disagree on what "today" or "now" means.

Corollary consistency rules (docs/QUALITY.md "Consistency Rules"):
1. **One State → One Source → One Truth → Many Consumers** — see above.
2. **One Metric → One Definition** — a number's scope (Today/Week/Rolling-N)
   must be fixed and labeled, not implied differently by different cards
   (RC1.16 found `missed_winner.summary()`'s "today" was a rolling 24h
   window while the UI labeled it "Today" and `analytics.performance()`'s
   own "today" was calendar-day — same word, two meanings; fixed by routing
   both through the same `core.clock.midnight_today_ts()`).
3. **One Event → One Vocabulary** — a given real-world condition is described
   with the same word everywhere it appears, unless the underlying state is
   genuinely different (a triggered safety event vs. a calm expected pause
   are allowed different words — see RC1.13's SafeMode/KillSwitch exception).
4. **One Time → One Clock** — every wall-clock read funnels through
   `app/core/clock.py` (RC1.16); no module builds its own timezone object.
   See docs/ARCHITECTURE.md "Market State & Time Source Map".

## Rule 11 — One Hero → One Decision (Hero Hierarchy Rule)

*Locked by owner 2026-07-26, ahead of V7.0 Step 2 (Hero Dashboard Finalization),
explicitly to prevent the class of duplicate-panel/duplicate-confidence drift
the 2026-07-26 Dashboard Cleanup Audit found and fixed.*

> The Hero Card (`TradeNowCard` — the Trade Light verdict, confidence, best
> strike, R:R, evidence score) is the ONLY Primary Decision surface on the
> dashboard. No other panel may contradict it. Every other panel is
> supporting evidence for the Hero's own decision — never a second, competing
> verdict, score, confidence, or probability computed independently.

Fixed role hierarchy (do not blur these across panels):
- **Hero → Decision** — the one verdict.
- **Evidence → Why** — S/R, Structure, Fibonacci, evidence chips: why the Hero decided this.
- **Risk → Can I trade?** — SL, R:R, position size, capital gates.
- **Structure → Market context** — HH/HL/LH/LL, BOS/CHOCH, liquidity, trendline.
- **Explainability → AI reasoning** — WHY / WHY NOT / NEXT LEVEL / INVALIDATION, voiced.

Note: `SRHeroCard` ("S/R Hero") is NOT the Hero under this rule despite the
shared name — it is explicitly self-documented as "not a Trade Light," i.e.
an Evidence surface. Only `TradeNowCard` is the Hero. Any future panel named
"Hero"/"Primary"/anything implying a verdict must route through the same
`decisionContract()` the real Hero reads — never compute its own score.

## Rule 9 — Repeated Evidence

> **Correlation is not enough; changes require repeated evidence.**

One good week never changes a weight. A proposal may be raised only when the
same pattern repeats across many samples AND across multiple market regimes
(Trend / Range / High-Vol / Low-Vol buckets in the verdict ledger).

## The only change pipeline

```
Observation → Evidence → Proposal → Approval (human) → Deployment → Monitoring
```

Nothing — no weight, threshold, gate rule, or engine — changes outside this
pipeline. The system never places orders; it is decision-support only.

## Core safety hierarchy (unchanged since V1)

Capital protection > opportunity. Kill switch > everything. Probabilities,
never certainty. Missing data is shown as missing — never estimated.

## Change workflow (Kanban)

```
BACKLOG → RESEARCH → DESIGN REVIEW → COLLECTING DATA → READY FOR REVIEW
        → APPROVED → DEPLOYED → MONITORING → ARCHIVED
```

DESIGN REVIEW asks exactly one question: **"இந்த மாற்றம் உண்மையில் Data-ஆல்
தேவையா?" (Is this change actually demanded by the data?)** If not — rejected.
