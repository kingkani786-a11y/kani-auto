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

## Rule 10 — One State → One Truth

> When the system is in ONE real state (e.g. Market Closed), every component
> that displays that state must show the SAME reality — Paused / Expected —
> at the same moment. No card may independently declare Failure for a state
> every other card correctly shows as calm.

Corollary consistency rules (docs/QUALITY.md "Consistency Rules"):
1. **One State → One Truth** — see above.
2. **One Metric → One Definition** — a number's scope (Today/Week/Rolling-N)
   must be fixed and labeled, not implied differently by different cards.
3. **One Event → One Vocabulary** — a given real-world condition is described
   with the same word everywhere it appears, unless the underlying state is
   genuinely different (a triggered safety event vs. a calm expected pause
   are allowed different words — see RC1.13's SafeMode/KillSwitch exception).

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
