# RC STATUS

**Current stage: RC1 — VALIDATION** (entered 2026-07-08)

Progression is gated by **evidence-based exit criteria**, not fixed trade
counts — some metrics stabilise at 300 samples, some don't at 1000.

| Stage | Exit criteria |
|---|---|
| **RC1 – Validation** | Architecture stable · ≥100 validated trades · critical bugs = 0 |
| **RC2 – Calibration** | Calibration error consistently inside the accepted band · Gate Efficiency stable |
| **RC3 – Reliability** | Verdict/efficiency reports exist across ALL regimes (Trend, Range, High-Vol, Low-Vol) |
| **Production v1.0** | Metrics stable across multiple weeks/months · rollback + git tags + docs complete |

## Success is measured by the SIX metrics (never by version numbers)

1. False Signal % — decreasing?
2. Win Rate — increasing?
3. Capital Saved — increasing?
4. Missed Winners — decreasing?
5. Calibration — improving?
6. API Efficiency — improving?

## RC1 dashboard (update per session)

| Metric | Value | Source |
|---|---|---|
| Validated trades | 0 / 100 | Report Card |
| Critical bugs open | 0 | this doc |
| Supabase persistence | ACTIVE | /api/health/persistence |
| Historical knowledge run | pending first real run | POST /api/historical-learning/run |
| Verdict ledger | collecting | /api/verdicts |

## Reports & where they live

- 100-Validated report → Report Card page
- Gate Efficiency (+ regime split) → `GET /api/verdicts`
- Verdict Distribution → `GET /api/verdicts`
- Calibration report → Report Card / decision matrix calibration block
- Opportunity Accuracy → `GET /api/opportunities` → `board_quality`
- Monthly Evolution Report (Phase 4) → Evolution Center (proposals → approval queue)
