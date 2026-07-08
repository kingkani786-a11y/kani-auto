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

## Statistical discipline

Rule 9 applies: proposals need repetition across samples AND regimes.
Minimum bucket size 30; monthly cadence for evolution proposals; every
proposal states evidence count + confidence and waits for human approval.
