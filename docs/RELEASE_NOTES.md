# RELEASE NOTES

*(newest first; every RC milestone gets an entry — "6 மாதம் கழித்து பார்த்தாலும் தெளிவு")*

---

## RC1.16.1 — 2026-07-09 — Premium-Projection Fix (Black-Scholes reprice)

### Purpose
Owner-reported: Scalping Tool premium T1/T2/T3 "always too high, everything
confusing." Investigation across four live dumps found a real math bug with
same-day exchange confirmation.

### Root cause
`strike_selector.prem_at` projected premium at SL/target levels with a Taylor
parabola (`premium + delta·move + ½·gamma·move²`). Valid for small moves and
small gamma; on expiry-day ATM gamma it fabricated numbers in both directions:
- **14:58** — 77000 PE T1 claimed ₹381.94; the exchange later printed ₹257.70
  at an even deeper level (intrinsic ceiling ~₹230 at T1). SL risk shown as
  ₹8/unit (real ~₹55) → position sizing suggested **62 lots at "1% risk"**
  that was really ~7% of capital.
- **15:34** — SL projected ABOVE entry (₹57.75 → "SL" ₹142.14) because the
  always-positive gamma term exceeded the delta loss; T3 ₹2,871 vs intrinsic
  ceiling ₹513. The `entry > SL` sizing guard silently suppressed the qty line
  but still displayed the nonsense plan.

### Fixed
`prem_at` now does a full Black-Scholes reprice at each underlying level, at
the vol implied by the live premium (exact at entry by construction), floored
at intrinsic. One source (`greeks.bs_price` / `implied_vol` — already
existed), consumed by Scalping Tool, Strike Queue, Strike Engine and
Opportunity board alike.

### Verified
Three cases from today's real market: power-hour case now gives T1 ₹240.43
(exchange-confirmed ceiling ~₹230–258), SL ₹32.01 (real loss, sane sizing);
post-close inversion case now SL ₹18.38 < entry, T3 ₹512.86 ≈ intrinsic;
7-day normal-regime case unchanged in character. Position sizing inherits the
fix automatically (same premium fields).

### Hardening (same day, owner-requested non-expiry verification)
Owner asked for verification at non-expiry times too. The 30-day-tenor test
caught a second edge: with r=risk_free_rate the BS floor can sit ABOVE the
live premium (index carry ≠ risk-free assumption), pegging the IV solver and
re-inverting the SL. Fixed with a fit-check chain: solve at r=rf → verify the
model reproduces the market entry → else re-solve at r=0 (spot-as-forward) →
else intrinsic+time-value fallback whose SL==entry degeneracy the sizing
guard correctly refuses to size. Full grid green: solver round-trip exact
across 6 tenors (3h→30d) × 4 vols × 3 moneyness × both sides; ordered &
intrinsic-bounded plans for 1/2/7/30-day CE+PE including carry-mismatch
quotes; expiry-day cases regression-checked unchanged.

### Also
Owner's Fibonacci/data-derived underlying-target idea recorded as
PROPOSAL #003 (RESEARCH) in PROPOSALS.md — Trading-Doctrine change, needs
Rule 9 backtest evidence first (owner's 10-metric set recorded there).
Underlying targets today remain 1.5/2.5/4.0×ATR (`signal_engine.py`).
Owner's six premium-engine enhancement candidates recorded as PROPOSAL #004
with an honest inventory: Gamma Wall Detector already exists (Gamma Shield);
Auto Premium Calibration is effectively delivered by this fix (IV re-solved
from the live premium every option tick).

---

## RC1.16 — 2026-07-09 — Time Consistency Audit + Single Time Service

### Purpose
Owner-ordered follow-on to RC1.15: audit every clock in the system (Market
Countdown, Session Clock, US Open Timer, Europe Session, Daily Reset, Weekly
Reset, Validation Window, Kill Switch Timer, Global Context Capture) against
Rule 10 — one source, one truth. "Do they all come from a Single Time
Source, or from scattered `datetime.now()` / `zoneinfo()` calls that can
drift?"

### Findings
1. **Naive-datetime bug (real, numerically meaningful)**: `engines/
   index_analytics.py` and `engines/strike_selector.py` computed Black-Scholes
   time-to-expiry with a bare, timezone-less `datetime.datetime.now()` —
   silently wrong on any host not OS-configured to IST (would misprice every
   Greek/IV by the host's UTC offset). Every other clock in the codebase
   pinned Asia/Kolkata explicitly; these two didn't.
2. **Structural gap**: 12 separate files each independently constructed their
   own `zoneinfo.ZoneInfo("Asia/Kolkata")`. All 12 happened to agree — nothing
   guaranteed they would keep agreeing.
3. **Daily Reset mismatch (Vocabulary/Scope Audit)**: `services/
   missed_winner.py`'s `summary()` computed "today" as a rolling 24-hour
   window, while the RC1.13 UI label reads "(Today)" and `services/
   analytics.py`'s own "today" is calendar-day-since-midnight-IST — same
   word, two different meanings across two modules feeding the same screen.
4. `services/analytics.py`'s `_midnight_today()` used `time.localtime()` /
   `time.mktime()` — host-OS-local-time, not explicitly IST (same latent
   class of bug as #1, just not yet numerically wrong on this host).

### Fixed
- New `app/core/clock.py` — the single Time Service. `IST`, `NY` (US-session
  only), `now()`, `today_str()`, `midnight_today_ts()`. Every one of the 12
  files now imports from here; zero independent `zoneinfo.ZoneInfo(...)`
  construction remains outside this module.
- `missed_winner.summary()`'s "today" now uses `midnight_today_ts()` —
  calendar-day, matching its own UI label and `analytics.py`'s convention.
  "Week" (rolling 7 days) was already consistent between the two modules —
  left unchanged.
- `analytics._midnight_today()`, `market_dna._date()`,
  `evolution._by_day()` — all now route through `core.clock` instead of
  host-local `time.localtime()`.

### Verified
- Full import + call-graph smoke test across every touched function
  (`is_market_open`, `market_status`, `now_phase`, `session_now`, `_clock`,
  `_midnight_today`, `missed_winner.summary`, `_date`) — all return correct,
  numerically-unchanged-on-this-host values.
- Zero naive `datetime.now()`/`datetime.datetime.now()` calls remain
  anywhere in `app/` (grep-verified).
- Backend restarted clean; `/api/self-check`, `/api/missed-winners` both
  200; `missed_today` now reflects the corrected calendar-day window live.

### Exit criteria (owner-specified) — all met
Naive datetime = 0 · Single Time Service = `app/core/clock.py` · Single
Timezone Policy = IST (+ NY for the US-session clock only) · Daily semantics
verified & aligned · Weekly semantics verified & aligned · UI labels match
backend semantics · Greeks expiry clock centralized.

### Doctrine
- **Rule 10 refined**: "One State → One Truth" → **"One State → One Source →
  One Truth → Many Consumers"** (docs/DECISION_DOCTRINE.md).
- New corollary **"One Time → One Clock"** added.
- Market State & Time Source Map documented in docs/ARCHITECTURE.md.
- **Deferred to RC2/Production (owner-ordered, not built now)**: replacing
  the RC1.15 20s polling `_status_loop` with an event-driven broadcast.
  Logged as an explicit backlog item in docs/ARCHITECTURE.md so it isn't
  lost — current polling is sufficient for RC1.

---

## RC1.15 — 2026-07-09 — Market-Open Transition Stale-Status Fix

### Purpose
Owner-reported: dashboard left running across 9:00–9:15 kept showing
"Market Closed" after the market had actually opened.

### Root cause (Source-of-Truth Audit — new category, see QUALITY.md)
`state.status()` (market_open, market_status, countdown) was broadcast over
WebSocket only on connect / disconnect / symbol-switch — never periodically.
The backend always computed `is_market_open()` fresh; the frontend's copy,
once received, was frozen until one of those rare events fired again. The
banner's own text — "resumes automatically... no refresh needed" — was
false.

### Fixed
New `_status_loop`: broadcasts `state.status()` every 20s, unconditionally.
Zero broker calls (pure local time computation) — safe at this interval
regardless of market hours or connection state. The open/close transition
now self-corrects within one tick instead of requiring a reload.

### Doctrine additions (owner-ordered)
- **Rule 10: One State → One Truth** (docs/DECISION_DOCTRINE.md)
- Two new audit categories: **Truth Consistency Audit** (RC1.14) and
  **Source-of-Truth Audit** (RC1.15) — added to the standing RC checklist.

---

## RC1.14 — 2026-07-09 — Kill Switch Pre-Market False-Caution Fix

### Purpose
Applying the RC1.13 "no contradictory cards" checklist item surfaced a new,
more subtle case: Kill Switch showed "CAUTION — Degraded data" while the
header said "Data: GOOD" for the identical pre-market moment.

### Root cause
Two independent data-quality signals exist: `state.data_quality` (simple
spot-tick flag, shown in the header) and `data_quality.report()['overall']`
(rich per-stream engine feeding Self-Check / Feed Diagnostics / Kill Switch).
The rich engine has no market-hours awareness, so pre/post-market MISSING
checks routinely compute "DEGRADED". RC1.11 gave Self-Check and Feed
Diagnostics market-closed awareness; Kill Switch's soft caution never got
the same treatment.

### Fixed
`kill_switch.evaluate()` takes `market_closed: bool`; the soft "Degraded
data" caution is suppressed only when the market is closed. Every hard veto
(broker cooldown, genuine POOR data, completeness < 60%, calibration < 55,
3 consecutive losses) is completely unchanged — verified with 4 test cases
including that hard vetoes still trip even while market_closed=True.

### Doctrine note
This is capital-protection-adjacent code. Confirmed via explicit tests that
no real safety trigger was weakened — only a cosmetic advisory label that
fired on an expected, harmless condition.

---

## RC1.13 — 2026-07-09 — UI Consistency Audit (pass 1)

### Purpose
Owner-ordered standing RC validation checklist (recorded in docs/QUALITY.md):
one vocabulary per state, explicit scope on every number, calm/live mode,
no test data or placeholders in production, no contradictory cards.

### Fixed (violations visible in dumps reviewed this session)
- DailyReview `ai_status`: "Idle — ...sleeping" → "PAUSED — ..." (now matches
  Self-Check / Feed Diagnostics wording for the identical market-closed state)
- Scope labels added: MissedWinners (Today ×4), DailyReview (Today ×5),
  GlobalStrip Tomorrow-Bias Accuracy (rolling, last 30)

### Deliberately left alone
SafeModeBanner's "FROZEN" and Kill Switch's "ACTIVE/FORCE WAIT" — these
describe a genuinely different state (a triggered protective event) from a
calm expected market-closed pause, so unifying the wording would blur a
distinction RC1.11 exists to preserve.

### Backlog
Full sweep of every remaining card is a separate future RC-cycle item —
checklist lives in docs/QUALITY.md so it isn't lost.

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
