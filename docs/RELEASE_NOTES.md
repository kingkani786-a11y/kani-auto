# RELEASE NOTES

*(newest first; every RC milestone gets an entry — "6 மாதம் கழித்து பார்த்தாலும் தெளிவு")*

---

## AI-A5 — 2026-07-11 — AI Timeline + 4-block Analysis (+ thinking-off fix)

### AI Timeline (AI Journal)
backend/app/services/ai_timeline.py — records timestamped engine transitions
(trend flip · structure confirmed/BOS · liquidity +8 · entry ready · decision
change · target hit · back-to-wait). scan() hooked at the END of the AI cycle
(market_service, read-only + guarded — never touches the decision path).
GET /api/ai-timeline. components/AITimelineCard.tsx on the home dashboard:
glance after 30 min away → the whole session story. Quiet on a closed market.

### 4-block AI Analysis (WHY / NEXT / WATCH / CHANGE)
cortex/analysis.py now asks Gemini for 4 labelled blocks and parses them
(tolerant: falls back to raw text). AIAnalysisCard renders a 4-quadrant grid
(WHY reason · NEXT path · WATCH level · CHANGE what-flips-it) + engine decision
+ Safety banner. Verified LIVE (closed market): all 4 blocks populate, ₹0.04.

### Fix — disable Gemini "thinking" on utility calls
gemini-flash-latest was spending the output-token budget on thinking and
truncating replies (only WHY appeared). provider.py now sets
thinking_config.thinking_budget=0 for all cortex calls → complete replies,
cheaper, faster. Fixes the 4-block truncation; benefits chat/reports/weekend AI.

### Verified
tsc clean · build compiled · both services restarted · home renders AI Analysis
+ AI Timeline. Live transition events verify Monday (closed tape is quiet).


## AI-A4 — 2026-07-11 — AI Analysis card (Gemini on the dashboard)

### Purpose
Owner directive: use the live Gemini API to analyse the engine's data and show
the answer ON THE DASHBOARD (and let the radio speak it). The Cortex explainer,
surfaced as a live card at the top of the home screen.

### Added
- backend/app/services/cortex/analysis.py — analyze() explains the CURRENT
  decision, CACHED by (symbol, decision-band, market, data-quality). While the
  decision view is unchanged, dashboard polls return the cached answer with
  ZERO new Gemini calls; a 180s min-interval guards rapid band flips. Cost stays
  ~1 call per real decision-change. latest_text() lets the radio speak it.
- GET /api/cortex/analyze (?force=true to regenerate) · api.cortexAnalyze().
- components/AIAnalysisCard.tsx — top-of-dashboard card: Gemini's plain-language
  read of the live decision + engine authoritative decision + Safety banner +
  🔊 speak + ↻ refresh. Hides entirely when the cortex is off (no broken card).
  Polls every 60s (cheap due to server cache).

### Verified LIVE (Gemini, Sat market-closed)
analyze #1 fresh (Tanglish "NIFTY CLOSED… WAIT", ₹0.02) → #2 cached (age 0, no
new call) → budget shows 1 call total. Proves the cost cache. tsc clean, build
compiled, both services restarted; home renders "AI Analysis".

### Doctrine
Engine decides, Gemini phrases; Safety + Cost caps wrap the call; provider-
agnostic (Gemini now, Claude/others via settings). No decision-path change.


## AI-A3 — 2026-07-11 — AI Radio v1.0 (FAIOS Layer 9)

### Purpose
The OS's face (owner: "Screen பார்க்காமல் Market புரியணும்"). Voice ON →
the engine's state transitions are spoken as a continuous radio stream. FINAL
LAW intact: every word comes from engine-published state; the radio narrates,
the engine decides. No LLM in this path.

### Added — components/VoiceAssistant.tsx (AI Radio transition watcher)
COMMENTARY/FULL modes now announce, via speakSoft (never interrupts alerts/
decisions), the moments a trader wants to hear:
- Market OPEN → "Good morning, market is now open" + auto Good-Morning briefing (once)
- Market CLOSE → "Market closed. That's a wrap."
- Trend flip → "Trend is now <state>"
- Structure confirmed / BOS → spoken
- Liquidity score +8 → "Liquidity improving"
- Confidence crossing a 10-pt band → "Confidence up/down to N"
- Target hit → priority "Target N hit"
Tolerant readers (layerTag/layerScore) over published `layers`; transition
memory in a ref so nothing repeats. Builds on the existing alert/decision/
confidence/narrator voice streams — no rewrite.

### Verified
tsc clean · production build compiled · frontend rebuilt + restarted (200).

### Live verification pending
Market is closed (Sat) — the open/trend/target transitions can only fire on a
live tape. Full spoken-radio verification is Monday at 09:15 open. Logic is
deterministic and compiles; nothing in the trading path changed.


## AI-A2 — 2026-07-11 — AI Workspace page + Weekend AI (live Gemini)

### Purpose
Make the live Cortex VISIBLE (owner: AI Experience felt low because there was
no frontend for it) and put the AI to work when the market sleeps. Engine
untouched; LLM stays explanation/research only, never the decision path.

### Weekend AI (backend/app/services/weekend_ai.py)
Rotates Review -> Research -> Plan, one cost-capped Gemini call each, while the
market is closed. Broker-independent loop in main.py lifespan, 1/hour,
CAT_WEEKEND_AI_ENABLED toggle. Grounded in measured ledgers (report_card,
verdicts, weekly evolution) — no fabricated numbers. brain._status_brief now
shows "Weekend AI ready — Research / Review / Plan" instead of "PAUSED".
Endpoints: GET /api/weekend-ai, POST /api/weekend-ai/run.

### AI Workspace (frontend/app/ai-workspace/page.tsx)
AI Chat (6 roles -> /cortex/ask, every answer shows the engine's authoritative
decision + Safety banner) · AI Reports (EOD) · Weekend AI outputs + run-now ·
live budget header. Linked from home Research quick-links. Honest roadmap
footer (Council/Architect/News = coming #014/#015).

### Verified LIVE (real Gemini, Sat market-closed)
Weekend auto-loop ran on boot; manual run: Review Rs0.148 + Research Rs0.041,
Safety clean, budget Rs0.19/100. /ai-workspace serves 200; tsc clean; both
services restarted.

### Honest
News/Calendar/FII-DII are external DATA feeds (not LLM) — shown "coming",
never faked. Research-depth history needs real data (Phase D). Council = #014.


## AI-A1 — 2026-07-11 — AI Cortex Phase A (#013): provider-agnostic LLM layer

### Purpose
First increment of the AI Operating System (Proposal #013). Adds an OPTIONAL
LLM "cortex" that explains/reviews/researches on top of the deterministic
engine — it NEVER touches the decision path, never emits BUY/SELL/SL/strike,
never overrides the gate. Disabled until an API key is present; the trading
engine runs identically with or without it.

### Added — backend/app/services/cortex/
- **context_builder.py** — the ONLY engine→LLM bridge. Emits the owner's
  locked structured snapshot ({market{trend,trendScore,liquidity,
  liquidityScore,structure,decision}, blockers[], confidence, reason[],
  status}) from PUBLISHED state only (Rule 10). Raw candles never sent.
- **safety.py** — code-enforced hard NOs. Scans LLM text for imperative
  trade-directive patterns; flags + records them; always attaches the
  engine's authoritative decision. Prompt-injection-safe by construction.
- **cost_controller.py** — mandatory budget guard. Per-IST-day call cap
  (CAT_AI_DAILY_CALL_CAP=200) + ₹ cap (CAT_AI_DAILY_COST_CAP_INR=100), live
  ledger resetting at IST midnight, per-model $/1M pricing → ₹ estimate.
- **prompts.py** — owner's Master Prompt (verbatim charter) + 7 role prompts
  (explainer/analyst/teacher/reviewer/planner/developer/research).
- **provider.py** — `cortex.ask(role, context, question)`; auto-detects
  provider from whichever key is set (Gemini or Anthropic), lazy-imports the
  SDK, wires Cost check→call→record + Safety guard around every request.
- **report.py** — EOD AI Report: first Tier-3 consumer; grounds prose in
  measured daily_review/report_card/verdict ledgers, never invents figures.

### Config (backend/app/config.py, CAT_ prefix)
ai_provider · gemini_api_key · anthropic_api_key · ai_model ·
ai_max_output_tokens(1024) · ai_daily_cost_cap_inr(100) ·
ai_daily_call_cap(200) · usd_inr(88).

### API + frontend
GET /api/cortex/status · GET /api/cortex/snapshot · POST /api/cortex/ask ·
POST /api/cortex/eod-report. Frontend api.ts: cortexStatus/Snapshot/Ask/
EodReport helpers.

### Verified (key-independent, offline)
Backend imports clean with NO key and NO SDK installed. Unit-checked:
context builder shape · Safety flags 3 directives in a bad string & passes a
clean one · Cost Controller ₹1.54 for a 1500/400 opus call · disabled ask/EOD
return honest notes · 4 routes registered. All passed.

### Not done (by design)
No live LLM call yet — gated on owner adding CAT_GEMINI_API_KEY or
CAT_ANTHROPIC_API_KEY to backend/.env + one restart. #014 multi-agent and
#015 governance follow AFTER Phase A proves stable (roadmap locked).

### Doctrine
LLM = consumer of published state (Rule 10 extended); decision path untouched;
Phase-22 remains the only route to production changes.

---

## RC1.16.14 — 2026-07-11 — Voice v0.3: Trading Radio deltas

### Purpose
Owner's "AI Trading Radio" spec. Channel mapping against what exists:
Ch1 Market Radio = narrator stream (live since v0.2) · Ch3 Trading Radio =
alerts + decision transitions (live) · Ch2 AI-Brain Radio ("Checking
PCR…") = needs backend pipeline-stage events, deferred with the Event-Bus
emitter · Ch4 Learning Radio = night review, deferred on the daily-review
aggregation fix. Smart Silence already emergent (narrator lines change only
when state changes; nothing new ⇒ nothing spoken).

### Added (the three buildable deltas)
- **Playback speed** 0.75×/1×/1.25×/1.5×/2× — wired into every speech path.
- **🚨 Emergency Override** (default ON): SL/SYSTEM-class alerts speak with
  "Attention." prefix even in Silent mode — nothing else ever does.
- **Voice Memory slice**: spoken "what happened / timeline / replay /
  என்ன நடந்தது" → replays the timestamped alert feed aloud (the system's
  own recorded history — nothing invented). Full Timeline Recorder (time-
  range queries, prior days) still queued.

### Verified
tsc + build, frontend restarted 200 OK.

---

## RC1.16.13 — 2026-07-11 — Voice v0.2: Live Market Narrator (owner v2.0 spec)

### Purpose
Owner's v2.0 spec: "Dashboard Thinks → Voice Speaks." Key realization: the
AI Market Narrator engine ALREADY generates the dashboard's own Tamil+
English tape commentary every AI cycle — the narrator stream is those
existing lines spoken aloud. No second brain.

### Added (frontend only)
- **4 modes**: 🔇 Silent (mic Q&A only) → 🔔 Alerts+Decisions → 🗣 +Market
  Commentary → 🎧 Full Copilot.
- **Decision-transition narration**: speaks only on gate STATE CHANGE —
  "Setup ready. [strike] Premium X. Stop loss Y. Target one Z." /
  "Setup no longer ready." (owner's no-repeat rule; snapshot polling stays
  silent).
- **Market commentary stream**: reads the existing AI Market Narrator lines,
  one per 15s max, each line once, via `speakSoft()` which NEVER interrupts
  — the priority ladder in code: alerts/decisions/Q&A use `speak()` (cancel
  + replace), commentary skips its turn if anything is speaking.
- Training-mode ("Checking Futures… Checking PCR…") deferred — needs
  per-stage pipeline events from the backend (Event-Bus emitter task).

### Verified
tsc + build, frontend restarted 200 OK.

---

## RC1.16.12 — 2026-07-11 — Voice Copilot v0: push-to-talk Q&A + alert narration

### Purpose
Owner order ("Please add the voice recognition") — the first #011 slice,
strictly inside the FINAL LAW: voice never calculates or decides.

### Added (frontend only — zero backend changes)
- `VoiceAssistant` on the dashboard: push-to-talk mic (browser
  SpeechRecognition; no always-on listening) → the spoken question goes to
  the EXISTING `brain.answer()` (same engine as the chat page) → the answer
  is spoken back (SpeechSynthesis) and shown as text. "Stop talking / mute"
  spoken commands cancel speech.
- Optional "Speak alerts" toggle (default OFF): narrates incoming
  MOVE/ENTRY/TARGET/SL/ARMED alerts from the existing feed, each at most
  once (owner's no-repeat rule); a new event replaces current speech.
- Language selector en-IN / ta-IN (recognition + speech quality is
  device-dependent — documented, not promised).
- Hidden entirely on browsers without Web Speech support — no fake mic.

### Deferred (per #011 queue)
Priority ladder, silent hours, market-pulse commentary, transition-event
announcements (needs the Event-Bus transition emitter), Timeline Recorder.

### Verified
tsc + build, frontend restarted, live Q&A path test ("why are we waiting?"
→ gate's real WAIT answer), 200 OK.

---

## RC1.16.11 — 2026-07-10 — MODE Phase B.1: Move Intelligence Panel

### Purpose
Owner-approved design after MODE's first live day (10 alerts): "Incident
#001's real failure was not 'no entry' — it was the system not TELLING me a
big move had started." Two brains, one card, never mixed.

### Added
- `move_detector.active_episodes()`: live open-episode view — premium path
  (from-low → now), velocity pts/min, acceleration, tiers fired, Move
  Strength ★1–5 (declared tier map), next tier (name + the premium it fires
  at), episode start/elapsed, and average episode duration measured from
  REAL completed episodes only ("— (learning)" until ≥5 exist — the mock's
  "11 min" is not fabricated).
- Move Intelligence Panel (evolves the Missed Move Protection card):
  Layer 1 Market Observer (facts) ∥ Layer 2 Decision Engine (🟢 READY +
  entry/SL/T1 from the strike plan, or 🟡 WAIT + missing factors). Border
  turns green when the gate opens. Pure consumer of both sources.
- Owner's "IF YOU ENTER NOW → Expected Win %" block replaced with the
  honest equivalent: the top blocker's REAL ledger record ("Entering against
  'Premium: AVOID' historically: saved 81% / missed 19% — research only,
  not an approval") — no invented conditional win rates.
- Voice announcements deferred to #011 per the queue.

### Verified
Episode lifecycle unit tests (fire → strength/next-tier math → give-back
close → duration recorded → honest avg=None), tsc + build, both services
restarted, endpoint live.

---

## RC1.16.10 — 2026-07-10 — Display-Truth Queue: 7 verified fixes

Seven display-only fixes from live-dump auditing (no gate/veto/scoring
change): ① GLOBAL CONTEXT label collision → internal engine now "INDIA RISK
CONTEXT (VIX·REGIME)" + honest alert text ② OverviewPanels Confidence →
dynamic_confidence (one truth) ③ Expired setups → "STALE — setup outlived
its window" ④ "False Signal Rate" → "Loss Rate (taken)" ⑤ "Signal age" →
"Setup updated Xm ago" ⑥ owner's market-closed precedence: "Broker issue —
retrying" → "Awaiting market open…" (both branches verified) + Kill Switch
market-closed context note (all hard vetoes regression-tested unchanged)
⑦ "BUY NOW · 92" under an active override → "CONFIRMED — GATE BLOCKED".

---

## RC1.16.9 — 2026-07-10 — MISSED MOVE PROTECTION panel + Entry Command Center spec

### Added
- `MissedMoveProtection.tsx` on the main dashboard: MODE's live move alerts
  (tier, strike, rise, confirmations, time) rendered NEXT TO the execution
  gate's current state + top blocker — a building move is visible even
  while the Decision Layer says WAIT (the exact Incident-#001 blindness).
  Pure consumer of the existing WS alert feed + gate state; computes
  nothing; hidden until the opportunity layer first speaks.
- Owner's full Entry Command Center UI spec recorded in QUALITY.md for the
  queued display-unification pass (3 states PREPARING/READY/EXIT, quantified
  WHY-WAIT, premium live tracker, strike competition). Two honesty flags
  recorded: "estimated wait minutes" and "NOW-vs-later advantage %" may not
  ship without a real model or a DECLARED-BAND label — no fabricated
  numbers to fill the mock.

---

## RC1.16.8 — 2026-07-10 — MODE guard-rails #1 + #2 (owner review, pre-validation)

### Purpose
Owner's 5-guard-rail review of Phase A. #1 and #2 change what Phase A alerts
on, so they land BEFORE the 1–2 week live validation window — the
validation must measure the final design. #3/#4/#5 are voice-layer rules →
appended to PROPOSAL #011.

### Changed
- **Dynamic threshold (#1)**: fixed +10/20/… replaced by
  `base = max(8 pts, 8% of rolling low, 3× premium ATR)`, tiers =
  base × 1/2/3/5/10. Premium ATR uses 1-MINUTE buckets, not raw ticks —
  tick-to-tick diffs would make the threshold depend on the polling
  interval (caught in test: non-deterministic).
- **Multi-factor confirmation (#2)**: WATCH/STRONG fire only with premium +
  ≥1 more factor (volume spike: last-60s > 1.5× prior-60s; or OI shift ≥1%
  in window). MOMENTUM+ fire regardless — a big move is its own evidence.
  Per-strike delta velocity is NOT in the visible chain → documented, not
  faked. Alerts carry their confirmation list ("confirmed by premium+volume").

### Verified
Incident series with confirmations → all five tiers once each at 8/16/24/
40/80; +16 pts premium-only correctly silent, +70 fires MOMENTUM/BREAKOUT;
₹600 premium +14 pts silent (base 48); ₹40 premium +9 pts fires (floor 8).

---

## RC1.16.7 — 2026-07-10 — MODE Phase A: Move Detection + Tiered Alerts

### Purpose
Owner (PROPOSAL #010, post-Incident-#001): "மார்க்கெட் நகர ஆரம்பித்த முதல்
10–20 பாயிண்ட்டிலேயே Alert வேண்டும்." Opportunity Layer, strictly separate
from the Decision Layer.

### Added
- `services/move_detector.py`: tracks premium per watched strike (strike
  queue, top 5) against a 10-min rolling low; tiered alerts +10 WATCH /
  +20 STRONG / +30 MOMENTUM / +50 BREAKOUT / +100 EXPANSION with
  acceleration flag (last-60s vs prior-60s rise). Alerts go through the
  existing alert engine (WS + Telegram + email when configured).
- Guard-rails per the proposal: 5% noise floor (₹10 on a ₹600 premium is
  not a move), once-per-episode tier dedup (episode closes on give-back or
  15-min quiet), 4-alerts/min hard cap, every alert ledgered for the
  Phase-B miss-join. IST-pinned timestamps (single time source).
- `GET /api/move-alerts` — fired-alert ledger + tier counts.
- Wired into the option tick beside the accuracy tracker — zero new broker
  calls.

### Doctrine
Alert-only: the engine cannot force, soften, or bypass the gate. Alert body
itself says "the entry gate is unchanged and decides separately."

### Verified
Owner's own incident series (75→92→108→132→170) fires WATCH→STRONG→
MOMENTUM→BREAKOUT exactly once each, EXPANSION on crossing +100; no
duplicate fires on flat re-ticks; +2% move on an expensive premium
correctly suppressed; endpoint live.

### Also
Owner's AI Voice Copilot spec recorded as PROPOSAL #011 (voices only what
the decision source already published — One Source law). Build deferred:
depends on Phase B.

---

## RC1.16.6 — 2026-07-10 — Blocker Explainability (Incident #001 follow-up)

### Purpose
Owner's Incident #001 verdict: not a bug, a policy failure — and the
biggest quality improvement is explainability. WAIT must read as "AI saw
the setup; this rule refused — and here is that rule's track record", never
a bare WAIT.

### Added (research display only — gate logic untouched)
- `verdicts.blocker_research()`: joins each active blocking reason to its
  own ledger record via the same `_blocker_key` normalization the verdict
  engine uses — saved% / missed% / solo-missed% / blocks / LEARNING-MEASURED
  status, each row stamped "Research only — not approved for override."
- `execution_gate.blocker_research` attached every cycle in market_service;
  Execution Control Center renders it under "Blocked by" (e.g. "Greeks:
  saved 44% / missed 56% · solo-missed 83% · 283 blocks · MEASURED ·
  research only — no override").
- RQ-008 (Leading Structure Detection) and RQ-009 (Expiry Breakout Regime
  Detector / Research Override Candidate tag — entry stays blocked, pattern
  gets measured) filed in PROPOSALS.md per the owner's three-way split.

### Explicitly unchanged
No gate softening, no adaptive override — owner: changes only after RQ data.

---

## RC1.16.5 — 2026-07-10 — Real-State Pipeline + Waiting-For (fallback v2)

### Purpose
Owner's RC1.16.4 review: show WHICH inputs the AI is waiting for, and a
pipeline view with real stage states instead of percentages.

### Added (display/honesty only)
- `_status_brief().pipeline`: six stages (broker → spot → chain → OI →
  Greeks → confluence), each marked done/loading/pending purely from whether
  that data actually exists in state right now — no fabricated progress.
  "loading" only when connected + market open.
- `waiting_for`: the exact missing mandatory inputs, listed by name.
- Strategist page renders ✓/⟳/○ pipeline + waiting-for line; chat fallback
  carries the same in points.
- Owner's Evidence Panel idea (per-recommendation evidence used + decision
  quality Complete/Partial) recorded as PROPOSAL #005 — deferred until after
  the premium-accuracy data-collection phase per the standing no-new-features
  directive.

---

## RC1.16.4 — 2026-07-10 — Honest AI-Status Fallback (Brain + Chief Strategist)

### Purpose
Owner: the bare "I don't have live analysis yet — connect and let the first
AI cycle run" fallback reads like a broken feature, not an AI analyst. Say
WHY there is no answer, what happens next, and when analysis arrives.

### Added (display/honesty only — no market logic, no new engines)
- `brain._status_brief()`: structured AI STATUS built entirely from real
  state (broker connected?, market open + IST clock + next-open countdown
  from the single time source, data quality, configured AI-cycle interval).
  Three honest branches: not-connected / market-closed / first-cycle-running.
  Nothing fabricated — no invented health %, no fake progress bars.
- Chief Strategist not-ready response now carries the block; the strategist
  page renders it (status grid, reason, next action, first-cycle pipeline,
  ETA, discipline line). AI Brain chat fallback answers with the same facts
  as points.

### Explicitly NOT built (freeze honored)
Owner's 9-module wishlist audit: all nine already exist as live engines
(Market Regime = regime engine · Institution Footprint = futures build-up +
institutional activity · Premium Projection = RC1.16.1 · Trap Detector =
trap engine · Entry Optimizer = entry probability + fire score · Exit
Optimizer = exit intelligence · Runner Predictor = expansion runner prob ·
Confidence Engine = dynamic confidence + calibration · Narrative Generator =
AI Market Narrator). No duplicates created; the fix was surfacing, not
rebuilding.

---

## RC1.16.3 — 2026-07-09 — Accuracy Distributions + Regime Breakdown + Production Gate

### Purpose
Owner's final RC1.16.2 review: "mean error alone can mislead" — add
median/p95/max distributions; report accuracy per regime; encode the
production-promotion gate directly in the report.

### Added (still measurement-only)
- Error **distributions** (mean/median/p95/max, nearest-rank p95) for entry
  reproduce, target touches, SL touches.
- **Regime breakdown**: expiry-vs-not (from the plan's own expiry date),
  session bucket (morning/mid/closing/evening, IST, declared bands), IV band
  (HIGH ≥15, declared), fit mode (BS vs fallback).
- **Production Gate** auto-evaluated in `production_gate`: ≥50 touches ·
  both day types · entry median ≤1% · T1/SL median ≤5% · ordering
  violations 0 · fallback <5% · tracker errors 0 — status PASS/NOT YET with
  every blocking criterion named. Criteria also recorded in RC_STATUS.md.
- `note_error()` wired into the tracker's exception paths so "critical
  exceptions = 0" is itself measured, not assumed.

### Fixed during test
p95 index used truncation and could land below the median on small n —
switched to nearest-rank (verified n=1/2/100).

---

## RC1.16.2 — 2026-07-09 — Premium-Accuracy Tracker (live validation machinery)

### Purpose
Owner-ordered after the RC1.16.1 review: "synthetic tests மட்டும் போதாது —
live market data-வுடன் cross-check செய்யுங்கள்"; capture per-setup projected
vs actual premiums until 20–30 samples exist.

### Added (measurement only — zero broker calls, zero trading-logic changes)
- `strike_selector` output now carries `pricing` metadata (solver IV vs chain
  IV, r used, fit mode BS/INTRINSIC_TV, entry-reproduce error %) and the
  underlying levels each projection was computed at.
- New `services/premium_accuracy.py`: every AI cycle records the active
  plan's projections (`observe`) with an ordering check
  (SL < entry < T1 < T2 < T3 — violations counted and logged); every option
  tick scores stored projections against the live chain premium when spot
  reaches a projected level within tolerance (`check`, deduped per plan).
- `GET /api/premium-accuracy` — owner's pass criteria in the report: entry
  reproduce < 1% · T1/SL premium error < 5% · ordering violations = 0 ·
  LEARNING label until ≥ 20 scored touches.

### Verified
Unit tests: selector metadata flows; ordering violation detected and counted;
T1 touch scored once per plan (deduped) against live ltp; endpoint live and
honestly empty after restart.

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
