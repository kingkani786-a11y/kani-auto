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

## RC1 SUCCESS = these six questions, all "YES"

1. Did the system give every decision a Verdict?
2. Were verdicts recorded correctly (spot-checked vs charts)?
3. Do the reports generate automatically?
4. Can any proposed rule change show its evidence?
5. Is there a git tag to roll back to?
6. Can a new developer understand the system from the docs alone?

## Pre-Production Independent Audit ("we verified", not "we believe")

- [ ] Documentation vs code consistency
- [ ] Metrics correctness (recompute a sample by hand)
- [ ] API failure handling (broker down / rate-limited / malformed payloads)
- [ ] Data integrity (Supabase rows vs in-memory state)
- [ ] Performance under load (full session, no drift/leak)
- [ ] Recovery after restart (rehydration complete)
- [ ] Backtest vs live consistency (same inputs → same decisions)

## Reports & where they live

- 100-Validated report → Report Card page
- Gate Efficiency (+ regime split) → `GET /api/verdicts`
- Verdict Distribution → `GET /api/verdicts`
- Calibration report → Report Card / decision matrix calibration block
- Opportunity Accuracy → `GET /api/opportunities` → `board_quality`
- Monthly Evolution Report (Phase 4) → Evolution Center (proposals → approval queue)

## Planned — RC1.17 Performance Consistency Audit (owner-scoped 2026-07-09, not started)

Owner-ordered next audit cycle, deliberately scoped for a **fresh session**
(clean RC history, its own log/report/release-notes entry — not to be
started mid-session). An investigation only — like RC1.16, no optimization
is applied until Evidence → Proposal → Approval.

**Phase 1 — Duplicate Broker/API Calls (highest priority).** Map how many
times each API is actually called per AI cycle — Option Chain, Futures,
Spot, VIX, OI, Greeks — across Scanner / Strike Selector / Gate /
Opportunity Engine. Output as a matrix: consumer ✓/✗ per data type, current
call count vs. required count, duplicate YES/NO.

**Phase 2 — Cache Consistency.** For each data type, is it fetched once and
shared, or does each module (Scanner → Opportunity → Strike → Dashboard)
fetch its own copy independently? Target pattern: **One Fetch → Many
Consumers** (the same Rule 10 shape already applied to Market State/Time in
RC1.15/RC1.16).

**Phase 3 — WebSocket Payload Audit.** Per broadcast cycle: payload bytes,
compression, duplicate JSON keys across channels, unused fields the
frontend never reads.

**Phase 4 — Scanner / Opportunity Overlap.** Does `services/scanner.py`
L1 and `services/opportunity.py` L2 recompute the same thing on the same
candidates? If so, share the result instead of recomputing.

**Phase 5 — Hot Path Timing.** Profile one full AI cycle stage-by-stage
(market fetch → indicators → Greeks → scoring → dashboard broadcast) to find
the actual bottleneck, not a guessed one.

**Deliverables** (report only, no code changes until approved): Duplicate
API Matrix · Cache Utilization Report · WebSocket Payload Report · Hot Path
Timing Report · Reuse Opportunity Report. Then, per standing doctrine:
Evidence → Proposal → Owner Approval → Optimization.
