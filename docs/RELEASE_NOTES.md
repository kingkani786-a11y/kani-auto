# RELEASE NOTES

*(newest first; every RC milestone gets an entry — "6 மாதம் கழித்து பார்த்தாலும் தெளிவு")*

---

## RC1.11 / RC1.12 — 2026-07-09 — Market-Closed Consistency Bug Fixes

### Purpose
Owner reported a page-crash and a confusing pre-market dashboard state.
Investigation found: (1) test scripts had leaked synthetic data into the real
Supabase evidence tables — cleaned up (7 rows deleted: 2 fake missed_winners,
5 fake evolution_reports; the "historical learning" data reported earlier that
day was actually FakeClient random-walk output, not real Dhan history — this
has since been correctly re-run for real); (2) two real, separate UI bugs.

### Fixed
- **FeedDiagnostics (RC1.11)**: showed a red "FEED 🔴 0% — Top failing: quotes
  (MISSING)" alarm every time the market was closed, even though AI Self-Check
  correctly treated the same missing feeds as a calm paused state. Now reads
  `status.market_open` and shows "FEED 🟡 PAUSED — Market closed, feeds resume
  automatically at open" instead. Live-market failure detection unchanged.
- **DailyReview (RC1.12)**: showed a specific Best/Worst trade result directly
  below "No settled trades yet" — contradictory-looking, though not fabricated
  (backend intentionally shows the WEEK's best/worst on a zero-trade day).
  Added a "This week:" label so the two facts no longer read as conflicting.

### Process note
Root-caused the original page-crash report to (a) evidence-ledger
contamination from my own test scripts hitting production Supabase, now fixed
with a policy change (mock/clean up after any test that touches persistence),
and (b) transient ECONNREFUSED during today's ~10 backend restarts, which the
error boundary correctly contained.

---

## RC1.10 — 2026-07-08 — US-Open Verification + Layer-4 Prediction Accuracy

### Purpose
Owner asked for cross-check of US market open time against an authoritative
reference before Production, plus a Prediction → Actual → Accuracy layer for
the Next-Session engine (owner-ordered, RC1.9 follow-up).

### Verified
Cross-checked 4 independent financial-data sources: NYSE/Nasdaq 9:30 AM ET =
**7:00 PM IST during EDT** (Mar–Nov), 8:00 PM IST during EST. Our existing
zoneinfo-based clock already computed this correctly (19:00 IST) — no logic
change needed. The commonly assumed "6:30 PM IST" figure is inaccurate;
documented in code so it's never "corrected" backwards.

### Added
- `market_context.institutional_levels()` returns `day_open`
- `global_feed.score_overnight_prediction()`: scores yesterday's stored
  tomorrow_bias against today's actual gap direction (GAP_UP/GAP_DOWN/FLAT).
  NEUTRAL predictions excluded from the ratio. Never double-scores a date.
- Rolling accuracy_pct, persisted + rehydrated on boot
- GlobalStrip.tsx "Tomorrow-Bias Accuracy" line

### Doctrine
This closes the Observation → Evidence loop for Layer-3: the engine now
grades its own forecasts instead of only making them.

---

## RC1.9 — 2026-07-08 — 3-Layer Global Clock + Next-Session Prep

### Purpose
Owner-ordered: use US/global market reaction to prepare the NEXT India
session (gap risk, overnight-hold risk) — explicitly not an entry engine.

### Added
- DST-safe US-open clock (America/New_York zoneinfo — corrects the commonly
  assumed 6:30 PM IST; actual is 19:00 IST under EDT)
- 3-layer phase detection: Morning (US-close bias) / Afternoon (Europe DAX+FTSE
  join the feed) / US-Open-Reaction
- Layer-3 Next-Session Preparation snapshot: tomorrow_bias, gap_likelihood
  (declared band, not fabricated %), overnight_risk, holding_note
- Persisted each evening, rehydrated on boot for the next morning

### Doctrine
Global context remains NEVER a hard gate (RC1.8 lock unchanged). Next-session
block is preparation only — feeds BTST/overnight-hold judgment, not entries.

---

## RC1.8 — 2026-07-08 — Global Market Context Engine

### Purpose
Owner-ordered: US/Nasdaq/Crude reaction as context for India entries.

### Added
- Yahoo chart API feed (unofficial, best-effort): NQ, ES, CL, GC, DXY, VIX, USDINR
- Transparent vote scoring → ±3 dynamic-confidence adjustment (never a gate)
- GET /api/global + GlobalStrip.tsx

### Known Limitations
Unofficial source, no SLA — falls back to "Waiting for Data Source" on failure.

---

## Release: RC1.0 — 2026-07-08

### Purpose
Validation Framework Freeze — architecture complete, doctrine locked,
measurement machinery armed. Development mode retired; the project now runs in
Research / Validation / Production modes only.

### Added
- Decision Verdict Engine (4-way verdicts, verdict confidence, per-module +
  per-regime Gate Efficiency)
- Opportunity board feedback loop (AI-score bucket accuracy)
- Historical Learning Engine (5-yr daily setups, vol-regime + day-of-week
  splits, Knowledge Score, analogue days / Market Memory, nightly refresh)
- Universal put-call parity chain sanity (ingest + publish, every instrument)
- AI Self-Check, Signal-truth display, Commander headline, AI Trust,
  Master Score, Mission status
- /docs suite (architecture, doctrine, quality, RC status, limitations,
  validation-report templates, changelog)

### Changed
- Greeks blocking reason now explains the skew conflict (was bare ATM IV)
- False-signal probability surfaced on the Trading card
- Expected move fixed to intraday horizon (to-expiry kept separately)
- Blocker categories normalised (13 stable buckets)
- Deep-scan defers politely under broker rate cooldown

### Fixed
- Structure "NONE" display
- Stock chain strike-step collapse (TATA STEEL bogus-premium bug)
- Stale feed-quality banner; WAIT-signal explainer side-flip;
  opportunity chain-error handling; expiry ordering

### Known Limitations
See docs/KNOWN_LIMITATIONS.md (historical option chains unavailable;
global/news feeds optional external APIs; stock universe = watchlist;
learning quality tracks validated live trades).

### Exit criteria for RC1
Architecture stable · ≥100 validated trades · critical bugs = 0.
