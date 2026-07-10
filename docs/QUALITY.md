# QUALITY FRAMEWORK (V40 program)

Goal: **fewer mistakes, not more features.** Every module must answer:
how many signals? how many right? how many wrong? — otherwise it is not
production-ready.

## Measurement machinery (all live, all data-gated)

| Question | Machinery | Endpoint |
|---|---|---|
| Was each BUY right? | Audit tracker (target/SL/45-min settle) | /audit, Report Card |
| Was each BLOCK right? | Verdict Engine — shadow trades at the plan's own SL/T1, 90-min window | GET /api/verdicts |
| Which gate rule earns its keep? | Gate Efficiency per module, split by regime | GET /api/verdicts |
| Is 80% really 80%? | Calibration tracker + Brier score | Report Card |
| Which engine to trust? | Engine Reliability tracker | Evolution / Weights |
| Is the AI-score honest? | Opportunity board 30-min direction grading by score bucket | /api/opportunities → board_quality |
| False signals? | signal_maturity false-signal probability + outcomes | Trading card "Signal truth" |

## Verdict definitions

- ✅ **WINNER** — taken, target before stop
- ❌ **LOSER** — taken, stop before target
- 🛡️ **CAPITAL_SAVED** — blocked, and the plan's SL was hit first
- ⚠️ **MISSED_WINNER** — blocked, and the plan's T1 was hit first
- ➖ **NEUTRAL** — blocked, neither level within the window (confidence 54%,
  excluded from saved/missed ratios)

Verdicts carry their own confidence (touch-based 88–97%; timeout 54%).
Buckets are labelled **LEARNING** below 30 samples, **MEASURED** after.

## Audit Categories (owner's standing RC validation taxonomy)

1. **Vocabulary Audit** — one word per state, everywhere (RC1.13).
2. **Scope Audit** — every number states its time window (RC1.13).
3. **Meaning Audit** — a label must mean what it appears to mean (RC1.12).
4. **Truth Consistency Audit** — for a given real state, do Header / Self-Check
   / Feed Diagnostics / Kill Switch / Scanner / Opportunity / Market Banner
   all agree? (RC1.14 found Kill Switch disagreeing with the header on an
   identical pre-market moment — root cause was two independent data-quality
   variables, not a display bug.)
5. **Source-of-Truth Audit** — for each major state, map Source → Consumers.
   Do all consumers read the SAME variable, or does each recompute/cache its
   own copy that can drift? (RC1.15 found `market_open` was broadcast once at
   connect and never again — every consumer held a stale copy across the
   9:15/15:30 transition until manual reload, contradicting the banner's own
   "no refresh needed" promise.)
6. **Time Consistency Audit** — does every clock (market countdown, session
   phase, US-open timer, Greeks expiry, daily/weekly reset, kill-switch
   timer) come from one Single Time Service, or do scattered
   `datetime.now()` / `zoneinfo()` calls risk drift? (RC1.16 found 12 files
   each independently building an IST timezone object — including 2 genuinely
   naive, timezone-less `datetime.now()` calls in the Greeks time-to-expiry
   path — and a "Today" scope label on Missed Winners that didn't match its
   own backend's rolling-24h computation. See docs/ARCHITECTURE.md "Market
   State & Time Source Map".)

## Entry Command Center — owner's target UI spec (2026-07-10, display workstream)

Recorded for the display-unification pass (queued after validation, per the
owner's own "no new proposals / market data first" declaration). Three
top-level states only — 🟡 PREPARING / 🟢 READY / 🔴 EXIT — with every
engine output shown as supporting evidence, never competing verdicts:

- **WHY ENTRY / WHY WAIT quantified**: not bare WAIT — each missing factor
  with current vs required (e.g. Volume 1.2× vs 2× · OI shift 0.4% vs 1% ·
  premium expansion 7 vs 12 pts). Data largely exists (checklist gaps,
  MODE confirmations); presentation is the change.
- **Premium Live Tracker**: the MODE tier ladder rendered inline (74 → 81 →
  89 🔥WATCH → 128 🚀MOMENTUM …). Data: /api/move-alerts ledger.
- **Strike Competition** (top 3): exists (Strike Queue) — reposition.
- **Entry Countdown meters + Fire Meter**: exists (checklist scores/fire
  score) — reposition.
- **MISSED MOVE PROTECTION box**: MODE alert + gate state + blocker + tier
  on one card — built 2026-07-10 (the MODE validation window's UI face).
- **⚠ Honesty flags (must resolve before build)**: "Estimated wait 3–5 min"
  and "NOW vs 5-min-later advantage 93%→71%" require a real time-decay
  model or must ship as DECLARED BANDS with that label — these numbers may
  not be fabricated to fill the mock. Voice lines belong to #011.

## UI Consistency Audit Checklist (owner's standing RC validation criteria)

Applied to every card, on every RC cycle:
- [ ] **One vocabulary per state** — 🟢 ACTIVE / 🟡 PAUSED / 🔵 WAITING / 🔴 ERROR.
      No card may use "Idle", "Stopped", "Frozen", "Inactive", "Sleeping" etc.
      for a state another card already calls PAUSED — unless the underlying
      state is genuinely different (e.g. Safe Mode / Kill Switch describe a
      triggered protective event, not a calm expected pause, and keep their
      own distinct language on purpose).
- [ ] **Every number carries an explicit scope** — Today / This Week / This
      Month / All-Time / Rolling-N. A metric with no scope word is not
      RC-clean, even if the card title implies one.
- [ ] **Market-Closed UI = calm mode**, **Market-Open UI = live mode** — a
      closed market must never render as a red/error state.
- [ ] **No test data reaches the UI** — verification scripts must not persist
      to production Supabase; if they must, clean up immediately (RC1.11/1.12
      incident: synthetic verdicts leaked into the evidence ledger).
- [ ] **No placeholder text in production** — every string a user can see
      must come from real computed state, not a hardcoded example.
- [ ] **No contradictory cards** — two cards must never assert different
      facts about the identical state (RC1.11: Self-Check said paused,
      Feed Diagnostics said failing, for the same market-closed condition).

Status: **pass 1 done** (RC1.13 — fixed the violations visible in dumps
reviewed together this session: DailyReview vocabulary + MissedWinners/
DailyReview/GlobalStrip scope labels). **A full sweep of every remaining
card is a separate, later RC-cycle item** — not yet done, tracked here so it
isn't lost.

## Statistical discipline

Rule 9 applies: proposals need repetition across samples AND regimes.
Minimum bucket size 30; monthly cadence for evolution proposals; every
proposal states evidence count + confidence and waits for human approval.
