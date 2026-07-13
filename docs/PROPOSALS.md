# TRADING-DOCTRINE PROPOSALS LEDGER

*Every Trading-Doctrine parameter change lives here, in pipeline order:
RESEARCH → COLLECTING DATA → READY FOR REVIEW → APPROVED → DEPLOYED → MONITORING.
Nothing skips a stage. Owner approval is the only path to DEPLOYED.*

## 📋 PROPOSAL DASHBOARD (owner-ordered, 2026-07-10 — anti-inflation governance)

| # | Title | Status | Next action | Depends on |
|---|---|---|---|---|
| #001 | Greeks Gate Softening | COLLECTING DATA (572 verdicts; solo-missed 83%) | by-regime table across ≥5 regimes | verdict ledger growth |
| #002 | V28 Quality Bar levels | RESEARCH | validated-trade outcomes | live validation |
| #003 | Fibonacci targets | QUEUED | 12-metric backtest | RC1.17 done |
| #004 | Premium-engine suite | PARTIAL (2/6 already exist/delivered) | spec #1 Confidence Score | premium-accuracy gate |
| #005 | Evidence Panel | QUEUED | wire pipeline+data_quality into recommendations | data-collection phase done |
| #006 | Entry Decision Engine | **MERGED → #012** | — | — |
| #007 | Premium decay→expansion switch | COLLECTING | wall-break episodes across expiries | live expiry days |
| #008 | Leading Structure Detection | RESEARCH | design leading (not lagging) breakdown detector | #012 Phase 1 |
| #009 | Expiry Breakout Regime Detector | RESEARCH | wall-break vs pin episode ledger | #007 data |
| #010 | MODE (opportunity alerts) | **Phase A DEPLOYED → VALIDATION (1–2 wks)** | measure false alerts + missed moves | live sessions |
| #011 | Voice Copilot | QUEUED | — | #010 Phase B |
| #012 | IPMME (+ 012.1–.8) | MEASUREMENT design | Phase 1 detectors + ledgers | queue items 1–5 |

**Owner declaration (2026-07-10): no new proposals until validation data
arrives. The pipeline is designed; the next value is 9:15 market data.**

## IPMME ACCEPTANCE GATE (owner-locked — applies to EVERY #012 sub-module)

A sub-module is "Done" only when ALL five gates pass:
1. **Detection Accuracy** — manual review of detections ≥ 95% correct.
2. **Outcome Ledger** — ≥ 300–500 observations OR coverage of 5 regimes.
3. **Statistical Edge** — beats baseline with adequate CI + sample size
   (e.g. Supply bounce 68% vs baseline 59% = +9%, CI reported).
4. **Performance Budget** — CPU / memory / API calls / WS bandwidth audited;
   20 good ideas must not add up to a slow system.
5. **Decision Contribution** — Observer → Research → Evidence → Approved →
   Contributor. Until Approved, Decision-Engine influence = **0**.

---

## PROPOSAL #001 — Greeks Gate Softening (Regime-Conditional)

**Status: 🔬 COLLECTING DATA** *(owner decision 2026-07-08 — neither approved nor rejected)*

### Evidence so far
122 settled verdicts · Greeks blocked 115 · Missed 87% / Saved 13%.
**Updated 2026-07-10 (Incident #001 investigation, 572 settled):** Greeks
blocked 283 · saved 44% / missed 56% · **solo-blocker missed 83%** (87/106)
· effective n=22 · missed CI95(eff) [36.5, 75.5]. The direction of the
original finding persists at 4.7× the sample. Approval conditions (regime
spread, by-regime table, event-day separation) still unmet — see INCIDENTS.md.

### Why NOT approved yet (owner's reasoning — recorded verbatim in spirit)
Single **High-Momentum Crash Day** dominates the sample → decision-bias risk:
on a day where Trend/Structure/Momentum all aligned, blocked directional
trades were *naturally* going to look like winners. The same logic must be
observed on Sideways, Expiry, Gap-up-Reversal and Low-VIX days first.

### Approval conditions (all three required)
1. **≥5 distinct regimes** in the ledger: Strong Trend Down · Strong Trend Up ·
   Range · Expiry · High Volatility.
2. **By-Regime table** (Saved% / Missed% per regime) — regime-specific rules
   may only be written from this table.
3. **Statistics**: sample size + 95% confidence interval + significance —
   a bare "87%" is not evidence. (Note: shadow autocorrelation means the CI
   is optimistic; weekly digest must state effective independence caveat.)
4. Event-driven sessions (war/news volatility) reported as a SEPARATE bucket —
   never mixed into ordinary trend-day evidence.

### Refined design (owner's preferred shape, if approved)
```
TRENDING regime AND Momentum > 90 AND Trend > 90
AND Structure PASS AND OI PASS
→ Greeks FAIL is NOT a hard block
→ −10 score penalty + visible Warning Banner
(all other regimes: hard block unchanged)
```
Gate opens; score pays; trader sees the warning. Capital protection intact.

### Review checkpoint
Re-presented in every **Weekly Validation Digest** until conditions met.

---

## RESEARCH QUESTION #002 — V28 Quality Bar levels

**Status: 🔬 RESEARCH** — Is `conviction ≥80 · fire ≥85 · trade_quality ≥800`
right for RC? Unknown. Same rule: evidence first. Ledger + validated-trade
outcomes will show how many quality-bar-blocked setups won/lost. No proposal
until the numbers exist.

---

## PROPOSAL #003 — Fibonacci / data-derived underlying targets

**Status: 🔬 RESEARCH** *(owner request, 2026-07-09 — "நம்முடைய டேட்டா
அடிப்படையிலும், Fibonacci அடிப்படையிலும் அந்த target-ஐ fix பண்ணி…")*

### Context that triggered it
The Scalping Tool's T1/T2/T3 looked "always too high / confusing." Root cause
split in two on investigation:
1. The **premium** T1/T2/T3 numbers were a genuine bug — the delta+half-gamma
   Taylor projection exploded on expiry-day gamma (fixed same day: full
   Black-Scholes reprice at market-implied vol, intrinsic-bounded; see
   RELEASE_NOTES RC1.16.1). This fix alone removes most of the "too high".
2. The **underlying** T1/T2/T3 are currently fixed ATR multiples
   (`signal_engine.py`: SL = 1.2×ATR, targets = 1.5 / 2.5 / 4.0 ×ATR).
   This proposal is about #2: replace/augment fixed ATR multiples with
   structure-aware levels — Fibonacci retracements/extensions of the day's
   measured swing, prior-day H/L, VWAP bands — so targets land on levels the
   market actually respects.

### Rule 9 evidence required before any code change
Backtestable from data we already store (candles + tracked signals):
for each historical signal, compute (a) current ATR targets, (b) Fib-based
targets from the active swing. Fib wins only if it beats ATR across ≥3
regimes (trend/range/expiry) with n ≥ 30 each.

**Backtest metric set (owner-specified, 2026-07-09 — all twelve required):**
Target Hit % · Median Holding Time · MFE · MAE · SL-First % · RR Realized ·
Win Rate · Expectancy · Profit Factor · Average Premium Captured ·
Calibration Error (projected target distance vs actual move) ·
Time-to-Target Distribution (time taken to reach T1/T2/T3).
"இவை இல்லாமல் target methodology-ஐ மாற்றக்கூடாது."

### Approval path
RESEARCH (this entry) → backtest table presented → owner approval → deploy
behind the existing target fields (no UI change needed — same T1/T2/T3 slots).

---

## PROPOSAL #004 — Premium-engine enhancement suite (owner list, 2026-07-09)

**Status: 🔬 RESEARCH** — six candidates named after the RC1.16.1 review.
Honest inventory against existing engines first (no duplicated calculations):

| # | Candidate | Existing coverage | Genuinely new part |
|---|---|---|---|
| 1 | Premium Confidence Score | — | New: composite confidence on each premium projection; warn < 70% |
| 2 | IV Sanity Filter | `data_quality` greeks-stream CORRUPT check; `chain_sane()` parity gate | New: per-strike IV outlier rejection before the solver |
| 3 | Market Microstructure Adjustment | spread already scored in strike selection | New: order-book imbalance input (needs DOM depth feed — check rate budget) |
| 4 | Gamma Wall Detector | **Already exists** — Gamma Shield (wall distance, pinning, dealer-hedging warnings) | Possibly: premium-projection coupling only |
| 5 | Liquidity Impact Factor | spread_pct in selection score; order-flow layer | New: slippage estimate on the plan's own size |
| 6 | Auto Premium Calibration (30–60s IV recalibration) | **Effectively delivered by RC1.16.1** — implied vol is re-solved from the live premium on every option-loop tick | Nothing left to build |

Next step when taken up: spec #1 (Premium Confidence Score) first — it wraps
the others as inputs. Each passes the LTS bar only via ↓risk (projection
honesty), not feature count.

---

## PROPOSAL #005 — Evidence Panel (per-recommendation explainability)

**Status: 🔬 RESEARCH** *(owner request, 2026-07-10 — "எதிர்காலத்தில்
சேர்க்க வேண்டிய ஒன்று")*

Every AI recommendation should show which inputs it actually used
(✓ Spot · ✓ Chain · ✗ Greeks unavailable …) plus a Decision Quality label
(Complete / Partial). Foundation already exists: RC1.16.5's pipeline block
derives per-input presence from real state, and `data_quality.report()`
tracks per-stream health — this proposal is wiring that into every
recommendation payload + a small UI panel. Display/explainability only;
no market logic. Take up after the premium-accuracy data-collection phase.

---

## PROPOSAL #006 — Entry Decision Engine Refinement (owner's RC1.19)

**Status: 🔬 RESEARCH** *(owner proposal, 2026-07-10 — 10-part spec; own
sequencing: RC1.17 audit → RC1.18 pricing fix → RC1.19 this)*

**Owner's governing rule (recorded verbatim in spirit):** a new indicator
enters production weights only with measured advantage — "இந்த indicator
False Signal-ஐ 12% குறைத்தது" போன்ற evidence வந்த பிறகே. Not "this
indicator is good."

**Sequencing note:** owner's RC1.18 (premium-projection fix) already shipped
as RC1.16.1–.3. RC1.17 Performance Audit remains the next fresh-session item
(plan in RC_STATUS.md).

### Honest inventory (no duplicate engines — most of the 10 parts exist)

| # | Owner item | Existing coverage | Genuinely new |
|---|---|---|---|
| 1 | 4-state WAIT→PREPARATION→READY→ENTRY with reasons | Signal maturity stages (PREPARING/ARMED/READY/FIRE NOW), "WHY NO TRADE" reasons, "AI WILL BUY WHEN +pts", "Missing to arm" | **Unified vocabulary across cards** (ties into the standing display-truth queue) |
| 2 | Candle-pattern scoring (Marubozu/Engulfing/PinBar/InsideBar/NR7/ORB) | ORB exists (market_context); swing structure exists | **Named-pattern detector + per-pattern score** — needs evidence per rule above |
| 3 | MTF agreement score | EXISTS — MTF alignment (1m–60m shown on dashboard) | — |
| 4 | Option-chain confirmation in entry score | EXISTS — OI/PCR/IV/Greeks layers in the 11-layer checklist | — |
| 5 | Pattern→result reliability DB (research only, no live weight change) | Engine-reliability tracker, DNA, signal outcomes exist | **Per-pattern outcome ledger** (measurement — could precede #2's scoring) |
| 6 | Entry Quality Meter with per-component breakdown | EXISTS — Trade Quality /1000, fire score, decision-matrix per-layer scores | Possibly one consolidated display |
| 7 | False-entry protection (ADX<15, IV crash, low liquidity, news) | EXISTS — trend/capital-protection/liquidity/kill-switch gates; news feed = Not Connected (documented limitation) | — |
| 8 | Global context ±3, never a gate | EXISTS — RC1.8, exactly this design, locked | — |
| 9 | Dashboard output block | EXISTS across cards | Consolidation only |
| 10 | Evidence-first doctrine | EXISTS — Rules 1–10 | — |

### Actionable core when taken up (in order)
1. **#5 first** (pattern outcome ledger — pure measurement, feeds evidence)
2. **#2 second** (pattern detector, research-report scores only)
3. **#1/#6/#9** (display unification — belongs with the display-truth queue)
4. Weight integration LAST, only via the Phase-22 approval pipeline once the
   ledger shows measured advantage across regimes (Rule 9).

---

## RESEARCH QUESTION #007 — Premium-AVOID regime-conditionality

**Status: 🔬 RESEARCH** *(filed from Incident #001, 2026-07-09)*

The premium forecast is a theta-decay (pinning) model. On the expiry-day
breakdown it predicted −13%/hour decay while the premium rose +240% — and
"Premium: AVOID" was the persistent final gate blocker on the day's biggest
winner. But the ledger says the gate is GOOD overall (81% saved on 420
blocks). So the question is narrow: **should a confirmed gamma-wall break
with volume flip the forecast from decay-model to expansion-model?**
Evidence needed per Rule 9: collect wall-break episodes across multiple
expiry days; measure decay-model error in break vs pin outcomes. No change
until then.

---

## RESEARCH QUESTION #008 — Leading Structure Detection

**Status: 🔬 RESEARCH** *(filed from Incident #001 — owner: "Breakdown
confirm ஆன பிறகல்ல, build ஆகும் நேரத்தில் detect செய்ய முடியுமா?")*

Incident #001: mandatory Structure layer sat at neutral 50 through the
14:28–14:58 buildup and printed BREAKDOWN 87 only at 15:34 — after the move.
Question: can structure be detected while forming (e.g. lower-high
compression + volume + failed-bounce sequence) instead of after confirmation?
Evidence path: replay stored candles around historical BREAKOUT/BREAKDOWN
day-types; measure how much earlier a leading detector fires and its
false-positive cost. Owner's indicator rule applies (measured advantage or
nothing).

---

## RESEARCH QUESTION #009 — Expiry Breakout Regime Detector (Research Override Candidate)

**Status: 🔬 RESEARCH** *(filed from Incident #001 — owner's design)*

Owner's condition chain: Expiry Day → Gamma-Wall Break → Volume Spike →
OI Collapse → Premium Expansion. When ALL five fire while a hard blocker
(e.g. Greeks) is active, the setup is tagged **RESEARCH OVERRIDE CANDIDATE**
in the verdict ledger — **entry stays blocked**; the tag only measures how
often this exact pattern would have won. Only after that ledger shows
repeated advantage across expiry days does an override proposal go to the
approval pipeline. (The verdict engine already shadows every blocked setup;
this adds the five-condition tag so the specific pattern is separable.)

---

## RESEARCH QUESTION #008 — Leading Structure Detection

**Status: 🔬 RESEARCH** *(filed from Incident #001 — Structure printed
BREAKDOWN only AFTER the move completed)*

Can breakdown be detected while it BUILDS (leading), not after it confirms
(lagging)? Candidate inputs already computed: liquidity sweep, order-flow
delta, OI velocity, MODE acceleration flag. Design work belongs to IPMME
Phase 1 (012.6 false-breakout classifier shares machinery). Evidence bar:
the leading detector must beat the current structure layer's timing WITHOUT
raising false-positive rate — both measured in the ledger.

---

## RESEARCH QUESTION #009 — Expiry Breakout Regime Detector

**Status: 🔬 RESEARCH** *(filed from Incident #001 — gamma-wall break was
treated as pinning/trap risk while it was a real breakout)*

Owner's 5-condition pattern: Expiry day + gamma-wall break + volume spike +
OI collapse + premium expansion. When all five align while a hard gate
blocks, the shadow trade should be TAGGED "override candidate" in the
verdict ledger (measurement only — entry stays blocked). After enough
tagged episodes across expiries: evidence table → Proposal → approval.
Depends on #007's episode data.

---

## PROPOSAL #010 — Market Opportunity Detection Engine (MODE)

**Status: 🔬 RESEARCH — owner-authored spec, 2026-07-10** *(owner called it
"Research Proposal #007"; renumbered — #007–#009 already taken by the
Incident-#001 research questions)*

### Owner's core requirement (recorded)
"மார்க்கெட் நகர ஆரம்பித்த முதல் 10–20 பாயிண்ட்டிலேயே Alert வேண்டும் —
100–300 பாயிண்ட் move முடிந்த பிறகு அல்ல." No system catches every move;
the goal is fast detection + loud alerting, honestly bounded.

### Architectural law (owner-locked)
**Two separate layers.** Decision Layer (WAIT/PREPARATION/READY/ENTRY —
existing gate, unchanged, sole authority on entries) ∥ Opportunity Layer
(detect · explain · alert — may scream "EXPLODING — WATCH NOW" while the
Decision Layer still says WAIT). MODE must NEVER force, soften, or bypass
an entry decision.

### Owner's 8 items — honest inventory

| # | Item | Exists today | New |
|---|---|---|---|
| 1 | Move Detection (premium +10/20/30/50/100 pt tiered alerts) ⭐ | alerts service (SETUP/SL types, WS broadcast); strike-watch premium ticks already in memory | **Core new engine** — per-watched-strike premium delta tracking + tiered alerts |
| 2 | Momentum Radar (premium/delta/gamma/volume velocity) | scalp radar velocity fragments | **New** — velocity series on chain snapshots (no new broker calls — reuse option-tick data) |
| 3 | Entry Countdown (prob + missing + trigger + ETA) | EXISTS — "AI WILL BUY WHEN +pts", "Missing to arm", readiness %, trigger dist, ETA | Display consolidation only |
| 4 | Voice alert | WS alert channel exists | **New frontend** — speech/audio on alert tiers |
| 5 | Miss Detector (auto-ask "did AI alert?") | missed_winner logs every missed move live with blocker attribution | **New** — join: move ≥ threshold AND no MODE alert fired ⇒ auto-flag |
| 6 | State progress bar | EXISTS (PREPARING→READY→ENTRY→RUNNING→EXIT + maturity stages) | Display only |
| 7 | Premium Explosion Detector (acceleration) | — | Same engine as #1/#2 (acceleration term) |
| 8 | Missed-Opportunity Auto Audit (auto Incident #00N) | verdicts + missed_winner data exist; INCIDENTS.md manual | **New** — auto-draft incident entry when move ≥ 100 pts with no alert |

### Build order when approved
Phase A: #1+#7 (move/explosion detection + tiered alerts — backend, zero new
broker calls) → Phase B: #2 velocity radar + #5 miss-join → Phase C: #4 voice
+ #8 auto-incident → #3/#6 display consolidation folds into the standing
display-truth queue.

**Phase A: ✅ DEPLOYED 2026-07-10** (`services/move_detector.py`, wired into
the option tick on strike-queue strikes, `GET /api/move-alerts`; tiered
alerts via the existing alert engine → WS + Telegram; acceleration flag;
5% noise floor; once-per-episode dedup; 4-alerts/min hard cap; every alert
ledgered for the Phase-B miss-join).

### Guard-rails
Alert-only engine; hard cap on alert rate (no siren fatigue); every alert
logged so the Miss Detector can also measure FALSE alerts (alert fired, move
fizzled) — both error directions ledgered from day one.

---

## PROPOSAL #011 — AI Voice Copilot Engine (owner spec, 2026-07-10)

**Status: 🔬 RESEARCH** — MODE Phase C's voice item, expanded by the owner
into a full copilot: live market narration (Tamil + English mix), tiered
urgency voices, trade-lifecycle commentary (entry/hold/partial/exit), and
Smart Silence (speak only when something changed — quiet market = quiet AI).

**Owner-locked law (One State → One Source → One Truth → Many Consumers):**
the Voice Engine NEVER decides anything. It voices exactly what the Decision
Layer / Opportunity Layer already published — Dashboard, Voice, Mobile,
Telegram all read the same decision source.

Owner's spec highlights (recorded): modes OFF / ALERTS ONLY / MARKET
COMMENTARY / FULL COPILOT · speed 0.75–1.5x · language Tamil / English /
Mixed / Numbers-English · frequency Important-only → Continuous · hotkey M
mute · Emergency voice for EXPANSION-tier alerts · scheduled narrator
summaries. Implementation candidates: browser SpeechSynthesis (zero-cost,
offline, Tamil support device-dependent) vs cloud TTS (better Tamil, cost +
latency + network dependency) — decide at build time. Depends on: MODE
Phase A alerts (done), Phase B miss-join (pending).

**Owner guard-rails #3–#5 (2026-07-10 review, voice-layer rules):**
- **#3 Priority queue**: Emergency > Entry > Exit > Momentum > Commentary;
  higher priority interrupts, lower never interrupts higher.
- **#4 Silent hours**: e.g. 09:15–09:20 commentary OFF / emergency ON;
  no continuous commentary 15:25–15:30. Configurable windows.
- **#5 Voice memory**: never repeat the same message until the underlying
  state changes ("last spoken → suppress until state delta").
- **Modes v2**: Quiet (entry/exit only) / Alerts / Copilot / **Training
  Mode** (explains every decision: "WAIT because delta weak, OI weak, need
  2 more confirmations").
- **"Why am I waiting?" hotkey** (Space or ?): voice reads the live gate
  state — existing blocker_research + waiting_for data, spoken. No new
  computation.
- **Consumer-only law (owner architecture)**: Decision Engine → Opportunity
  Engine → Event Bus → {Voice, Telegram, Dashboard, Mobile}. The Voice
  engine computes NOTHING — it is a pure consumer of published events.

### Voice Copilot v1.0 — owner's production prompt (2026-07-11, recorded)

**ROLE (verbatim-spirit):** "You NEVER make trading decisions / calculate
signals / predict anything. You ONLY narrate verified events already
published by the Decision Engine. Dashboard is the brain. Voice is only the
speaker." Allowed sources whitelist: Market Status · Opportunity Card ·
Decision Engine · MODE premium movement · Kill Switch · Safe Mode · Entry ·
Exit · Global Context · Position Monitor · Risk Manager. "Never invent
data. Never estimate missing values."

**Style:** natural Tamil + English trading terms, sentences ≤ 8–10s.
**Priority:** Emergency > Kill Switch > Exit > Entry > Opportunity >
Momentum > Commentary (lower never interrupts higher).
**Modes:** Silent (emergency only) / Professional (critical only) /
Commentary (30–60s configurable) / Training (explains every reason).
**Memory:** never repeat until state changes.
**FINAL LAW:** Voice never creates decisions, never overrides the gate,
only narrates verified state.

**10 features + build-time notes (existing foundations mapped honestly):**
1–5 (commentary/opportunity/entry/exit/emergency voices): event sources all
exist today (alert feed kinds MOVE/ENTRY/TARGET/SL/SYSTEM, gate state,
kill-switch/safe-mode broadcasts). 6 mute · 7 silent hours · 9 professional
mode: frontend settings. 8 Training-mode answers + 10 spoken questions
("Why waiting?" etc.): **reuse `brain.answer()` — it already answers exactly
these from live state**; voice Q&A = STT → brain.answer → TTS, zero new
decision logic. STT/TTS choice (browser SpeechSynthesis/Recognition vs
cloud; Tamil quality device-dependent) decided at build time.

**Voice Timeline Recorder (new sub-feature):** timestamped log of every
announcement (09:18 Market Open → 09:37 ENTRY READY → 09:49 T1) with
replay. Foundation exists: the alert feed + MODE ledger are already
timestamped; the recorder is a persistence + re-speak layer over them.

**Queue position unchanged (owner's own sequencing):** builds AFTER the
MODE 1–2-week live validation — "voice reads verified events only".

### v3.0 — AI Trading Radio (owner, 2026-07-11 night) — delta vs deployed v0.x

Already live (v0–v0.4 series): briefing rundown · confidence-delta
commentary · MOVE Tanglish · READY/WAIT transitions · narrator commentary ·
no-repeat memory · priority (speak vs speakSoft) · Tanglish standard.

**Genuinely new, planned as Voice v0.5 (next deploy window — Saturday,
market closed, zero restart risk):**
1. **Layer-flip narration** — each checklist layer spoken ONLY on status
   change ("Trend confirmed." when WAITING→PASS; "Liquidity weakened."
   on PASS→WAITING). Frontend tracks previous statuses. The owner's
   no-repeat rule at per-layer granularity.
2. **Periodic mini-update** (FULL mode, ~20–30s, Smart-Silence aware):
   time + spot + fire score + top missing factor — CHANGED values only,
   full silence when nothing changed.
3. **Cycle roll-call** (FULL mode): when a fresh AI cycle lands, narrate
   the real results sequence — "Layer check. Structure PASS. Trend
   waiting…" **Honesty rule: results of COMPLETED checks are narrated;
   no fake real-time 'Checking…' theatre with artificial delays** — true
   per-stage live narration needs the backend Event-Bus stage emitter
   (recorded; benefits Telegram too).
4. Bulls/Bears probability delta line ("Bears probability 43 → 51").
5. Fetch-retry resilience in lib/api req() (2–3 backoff retries) so
   backend restart windows never trip the page error boundary — first
   item of the same deploy window.

5-stream naming (owner): Market/AI-Thinking/Trading/Momentum/Learning
Radio — maps to existing streams + #011 deferred items (Learning Radio
still gated on the daily-review aggregation fix; AI-Thinking Radio full
version gated on the Event-Bus emitter).

### v2 spec additions (owner, 2026-07-11 — "Core Operating Layer" framing)

**The architecturally significant piece — EVENT BUS formalization:**
```
Decision Engine → Event Bus (single source) → Dashboard · Telegram · Voice · Timeline
```
Honest inventory: `alerts.send()` already IS the embryonic bus (one call →
WS broadcast + Telegram + email + timestamped feed ledger). What's genuinely
missing: **state-TRANSITION events**. Today the gate/confidence/blockers are
broadcast as snapshots; nobody emits "WAIT→READY", "confidence 71→89",
"Liquidity confirmed, only Smart Money pending" as events. That transition
emitter is the real Phase-C-precursor backend task — and it pays off before
voice exists (Telegram would carry ENTRY-READY/blocker-change alerts too).

**Five voice streams** (commentary/opportunity/decision/risk/learning) —
all consumer-only. Stream 5 (Learning: "this pattern has 78% historical
success") carries an honesty rule: spoken ONLY from ledgers at MEASURED
status; at LEARNING status the voice must say "insufficient history", never
a number.

**Owner's 8 additions mapped:** ① Market Pulse (30–60s) = commentary cadence
② Premium Speed = MODE velocity (exists) ③ Time Alerts = single time source
(exists) ④ Emotion Guard = consecutive-loss tracking (exists in kill switch;
voice wording new) ⑤ Confidence-change + ⑥ Blocker-change alerts = the
transition emitter above ⑦ Watchlist-only filter = per-symbol event filter
⑧ **Silent Night Review** (2–3 min post-close spoken summary: opportunities
/ entries / blocked / biggest miss) — depends on the daily-review
missed-opportunity aggregation gap fix (closed-snapshot audit item #2);
build that report field first, then voice reads it.

**Expanded controls recorded:** ON/OFF/Mute · Commentary-only /
Decision-only / Emergency-only · Training · Replay · speed · volume ·
language · voice gender. Hot commands list (11) — all answerable via
existing `brain.answer()` + gate state; "Stop talking / Resume" are
client-side.

---

## PROPOSAL #012 — Institutional Price Action & Market Mapping Engine (IPMME)

**Status: 🔬 RESEARCH** *(owner spec, 2026-07-10 — 9 sub-engines, owner's own
phasing: Phase 1 measurement only → Phase 2 validation 300–500 trades by
regime with CIs → Phase 3 weights via Rule 9 approval only)*

### Honest inventory

| # | Sub-engine | Existing coverage | Genuinely new |
|---|---|---|---|
| 1 | Price Action detector (BOS/CHOCH/named candles/fake breakout) | HH-HL-LH-LL structure engine, ORB | **Named-pattern + BOS/CHOCH detectors, score-only** — subsumes PROPOSAL #006 item #2 |
| 2 | Market Mapping (supply/demand/fresh/tested zones, breaker & mitigation blocks, liquidity pools, equal H/L) | Volume-profile value areas; S/R levels in Market Path | **Core new engine** — SMC-style zone taxonomy + zone drawing |
| 3 | Breakout Quality (VALID/FALSE composite) | Trap detection, breakout prob, volume/OI/delta layers | Composite verdict packaging over existing layers |
| 4 | Gap Risk (gap class → SL-reliability) | Next-session gap-likelihood bands (global_feed) | **SL-reliability metric vs gap class** |
| 5 | Automation Risk | Safe Mode + data_quality per-stream + kill switch + feed latency | Clock drift, CPU/memory probes only |
| 6 | Execution Quality (requested/filled/slippage) | — | **⚠ Doctrine conflict flagged**: system NEVER places orders, so broker fill slippage does not exist. Honest scope: paper-trade fills + signal-time vs actionable-price delay (Report Card's `avg_entry_delay_sec` placeholder). Anything more requires manual fill logging by the owner |
| 7 | Supply/Demand outcome ledger | verdict/outcome machinery patterns | New (depends on #2) |
| 8 | Price-action outcome ledger | — | = PROPOSAL #006 item #5 (consolidated here) |
| 9 | Operational Risk monitor | Self-Check panel (broker/WS/quotes/DB/latency/infra) | Clock-drift check (natural RC1.16 follow-on) |

### Consolidation
PROPOSAL #006's candle-pattern detector + pattern outcome ledger fold into
IPMME #1/#8 — one engine, not two overlapping ones.

### Sub-modules (owner extension, 2026-07-10)

| # | Module | Existing coverage | New core |
|---|---|---|---|
| 012.1 | Institutional Liquidity (buy/sell-side pools, sweep, stop hunt, FVG/imbalance, repricing) | Liquidity-sweep score in scalp radar; order-flow layer | Pool mapping + FVG detection + "next liquidity target" output |
| 012.2 | Order Flow Confirmation (OI velocity, volume acceleration, delta change, premium expansion speed) | Volume/OI layers; MODE Phase A velocity fragments | Composite institutional-activity % (bid/ask imbalance only if broker DOM depth allows — verify rate budget first) |
| 012.3 | Market Structure map (range/trend/compression/expansion/accumulation/distribution) | Regime engine (TRENDING/RANGE/VOLATILE/EXPIRY…) | Wyckoff-style accumulation/distribution classification |
| 012.4 | Multi-TF structure compare + alignment | EXISTS — MTF alignment score, 1m–60m per-TF direction on dashboard | Little new; possibly per-TF structure (not just direction) |
| 012.5 | Zone Strength scoring (fresh/tested/failed/broken/mitigated, 0–100) | — | New (depends on 012 core mapping) |
| 012.6 | False Breakout Classifier (breakout→retest→acceptance→continuation vs trap) | Trap engine; RQ-008 leading-structure | New sequential classifier — also the Incident-#001 missed-move analysis tool |
| 012.7 | Market Replay Ledger (daily snapshot → replay → learn) | Replay page exists; Market DNA stores day snapshots | Zone/pattern-level snapshot granularity |
| 012.8 | Regime Memory (pattern × regime success table) | historical_learning regime splits; DNA analogues | Pattern-conditional-on-regime ledger — this is where weights would eventually come from |

### Owner-locked laws (recorded verbatim in spirit)
1. **No pattern gets a weight at birth**: Detect → Measure → Ledger →
   Evidence → Weight. No exceptions.
2. **IPMME progression**: Observer first → Research Engine → only then
   Decision Contributor. It must never directly influence the Decision
   Engine before Phase 3 approval.

### Queue (owner-confirmed order)
1. RC1.17 Performance Audit → 2. MODE validation → 3. Premium-accuracy
validation → 4. Voice (#011) → 5. IPMME Phase 1 (measurement) →
6. IPMME Phase 2 (validation) → 7. IPMME Phase 3 (weight approval).

### Sequencing (doctrine)
Measurement-first (owner's Phase 1: detectors + ledgers, zero decision-path
impact) — but AFTER the current active commitments: MODE 1–2-week live
validation, RC1.17 Performance Audit, premium-accuracy production gate.
Weights only via Phase-22 approval with by-regime evidence (owner: "Fresh
Demand Success 81%"-grade numbers first).

---

## DOCTRINE ADDITION — Global Context is never a hard gate

**Status: ✅ LOCKED (owner, 2026-07-08)**

If/when external global feeds (US futures, DXY, yields…) are connected:
Global Context may only ever be **context** — e.g. Risk-ON +3 / Risk-OFF −3
score adjustment. It must never hard-block and never override Trend.

---

## PROPOSAL #013 — AI OS / LLM Intelligence Layer (owner architecture, 2026-07-11)

**Status: RECORDED — blocked on Anthropic API key + validation queue.**

Owner's 10-engine "AI Operating System for Financial Markets" vision
(Reasoning / Research / Memory / Learning / Strategy Lab / Analyst / Planner /
Developer / Commander + multi-agent layer). Full honest inventory, locked
laws, cost-safe 3-tier design and Phase A–D build plan recorded in
**docs/AI_OS_VISION.md**.

Core rulings (owner-locked): AI never auto-changes trading rules (Phase-22
pipeline is the only path); decision loop stays deterministic/LLM-free
(Tier 1); LLM is a language + research layer on top (Tiers 2–3); includes
the earlier "Design Studio" request as Engine 9 / Phase C.

---

## PROPOSAL #014 — AI Cortex Integration (owner, 2026-07-11)

**Status: RECORDED — blocked on API key + validation queue. Depends on #013.**

Owner's multi-agent framing: use one LLM API (owner named Gemini) as an
**AI Operating System**, not a single chatbot — many role-scoped "agents"
sharing the same API behind one Orchestrator. Full spec in
**docs/AI_OS_VISION.md** → "#014 AI Cortex Integration".

### 10 agents (role prompts, one API)
Orchestrator (Chief — only one that talks to user) + Market Analyst ·
Decision Explainer · Research · Learning · Developer · Architect · Voice ·
Teacher · Planner · Improvement.

### 10 infra modules
AI Orchestrator · Agent Manager · Context Builder · Prompt Manager ·
Memory Manager · Voice Manager · Research Manager · **Cost Controller** ·
**Safety Layer** · **Human Approval Layer**.

### Honest rulings (recorded)
- "Agents" = different **role prompts + structured context**, not different
  models. One API key, one interface. Cheaper and simpler than N models.
- **Cost Controller is not optional** — each agent = 1 API call; a full
  Council/Planner run fans out to ~10 calls. Per-agent + daily caps enforced
  here, else a "council meeting" could cost ₹100+/run.
- **Safety Layer** enforces the hard NOs (no BUY/SELL/SL/strike/override) at
  the code boundary — never relies on the prompt alone.
- **Human Approval Layer** = existing Phase-22. Improvement AI feeds it;
  never writes production.
- Context Builder emits only the published structured snapshot (Rule-10);
  raw candles never reach the LLM.

---

## PROPOSAL #015 — AI Governance & Trust Layer (owner, 2026-07-11)

**Status: RECORDED — depends on #013 + #014. Blocked on API key + queue.**

Every LLM output is watched and validated before it reaches the user. This is
what makes the OS Explainable + Auditable. Full spec in
**docs/AI_OS_VISION.md** → "#015 AI Governance & Trust Layer".

### 8 components
1. **AI Confidence Validator** — cross-check LLM claim vs engine truth; reject
   on mismatch (LLM says "Trend Strong" but engine Trend=49 → REJECT)
2. **Evidence Validator** — every claim tagged with its source engine
3. **Trust Score** — per-agent reliability (measured, starts at "building")
4. **Cost Monitor** — live calls/tokens/₹ today; budget-out halts research
5. **AI Memory Graph** — what the AI has learned per module (measured %)
6. **AI Disagreement Engine** — logs LLM-vs-gate conflicts; **gate always wins**
7. **AI Audit Trail** — every AI answer logged with time/agent/reason/evidence
8. **Self Diagnostics** — daily self-check (voice/research/memory/latency/safety)

### Honest rulings
- Confidence + Evidence Validators are the **enforcement arm of the
  Structured-Context law** — they catch hallucination by comparing LLM text
  to the engine snapshot it was given. High value, low risk.
- **Trust Score / Memory Graph must be MEASURED, never seeded** — they start
  "building / insufficient" and only show numbers after real samples, same as
  every existing ledger (no fabricated 98%).
- Disagreement Engine re-affirms the gate-wins law (MODE Two-Layer): a
  conflict is logged and shown, never resolved in the LLM's favour.

### Final flow (owner-locked)
`Market Data → Decision Engine → AI Governance → AI Orchestrator → 10 Agents → Voice → Dashboard`

---

## ROADMAP LOCK — AI OS (owner, 2026-07-11)

- **#013** AI Cortex (LLM integration + FAIOS 10-layer + Structured-Context law)
- **#014** Multi-Agent AI (10 role-agents + 10 infra modules)
- **#015** AI Governance & Trust Layer (8 validators)

**Build order (owner-locked, complexity-first-minimized):**
Build **#013 Phase A ONLY** first — (1) Context Builder, (2) Safety Layer,
(3) Cost Controller, (4) LLM integration, (5) EOD AI Report — prove it 100%
stable, THEN #014 multi-agent, THEN #015 governance. Does not disturb the
active validation queue (RC1.17 → MODE → premium-accuracy → Voice v0.5).
Still gated on the owner creating an API key.

---

## PROPOSAL #016 — Opportunity Engine v2 (owner, 2026-07-13)

**Status: RECORDED — build AFTER the pending A9–A11 batch ships + is verified live.**

Owner's architectural milestone: make the Opportunity layer world-class and
FIRST-CLASS (surfaced before the Decision gate). "Opportunity never WAITs; only
Decision WAITs." Note: premium_radar ALREADY runs independent of the gate every
option tick (Two-Layer law) — v2 widens + deepens it, it is not a re-architecture.

### 5-layer framing (owner)
1. **Market Hunter** — every tick, scan ALL liquid CE + PE (not ATM±4)
2. **Opportunity Intelligence** — Birth→Building→Acceleration→Runner→Exhaustion per strike (live)
3. **AI Attention** — focus % across strikes (built A11)
4. **Decision** — BUY/WAIT/EXIT (unchanged gate, still the sole trade authority)
5. **AI Thinking** — why-not / what's-missing / when-BUY / invalidation (built A9/A9.1)

### The 10 items → status
Built/partial (7): Rank(A10) · Birth(A8.1) · Prob-of-expansion=runner-score ·
WHY(A9.1 evidence) · WHY-NOT(checklist) · Attention(A11) · Miss(watchlist+MODE).
Genuinely NEW (3), the v2 scope:
- **#2 100% liquid-chain scan** — widen ATM±4 → all liquid CE+PE, rate-safe
  (respect Dhan feed limits; sample/stagger; cap tracked strikes by liquidity).
- **#8 Opportunity Timer** — time-in-stage (EARLY 18s → BUILDING 54s → RUNNER 3m → LATE).
- **#10 Proactive Miss-Prevention** — alert at ~+40% ("Runner building, look
  here"), not "MISSED" at +100%. Ties into the alert bus + AI Radio.

### Doctrine (unchanged)
Deterministic (Dhan LTP/Vol/OI); observer layer — the execution gate still
decides every trade; runner score is a declared blend, never a calibrated
win-probability; Gemini explains, never decides. No "every move guaranteed"
claim — the honest goal is action-oriented early surfacing vs WAIT-centric.

### Sequencing (locked)
Ship the pending 7-commit batch (A9/A9.1/A10/A11 + missed-neg fix + version-
honesty fix + version.json SW bypass) at market close, verify live, THEN build
#2/#8/#10 as Opportunity Engine v2 on the known-live base.

### #016 addition — Lifecycle Memory ("movie, not snapshot", owner 2026-07-13)
Each tracked strike keeps its full intraday journey, not just the current tick:
born-at · velocity-spike-at · volume-arrived-at · OI-confirmed-at ·
acceleration-at · current stage. So a strike already at ₹158 still carries the
context of its ₹85 birth. (Partly built: score_hist + confirmation timestamps
vol_confirm/oi_confirm exist; v2 formalises a per-strike event log + timer.)
This is the substrate for #8 Opportunity Timer and #10 Miss-Prevention.

### Dashboard order (owner-locked, top→bottom, once v2 ships)
1. 🔥 HOT NOW  2. 👀 AI Attention  3. ⏳ Building Opportunities
4. 🚨 Runner Alert  5. 🧠 AI Thinking  6. 🎯 Decision.
i.e. Opportunity → Thinking → Decision (never Decision → Opportunity).
Dashboard's job is "something is forming here / LOOK HERE", not "BUY".

---

## #017 — Opportunity Capture Terminal (owner's 10-layer, 2026-07-13)

Reframe: not an "analysis dashboard" but an **Opportunity Capture System**.
The top of the screen must answer an option buyer's 5 questions, big:
(1) which strike? (2) when to buy? (3) how many points now? (4) exit now?
(5) next opportunity? Analysis/timelines/diagnostics/health/logs go BELOW.

### Layer → status (audited against code, 2026-07-13)
- L1 🔥 HOT OPPORTUNITY top card — DONE `HotNow.tsx`
- L2 Premium Hunter (₹ ladder, velocity, vol/OI) — DONE `PremiumRadar.tsx`
- L3 Point Catch Counter (entry→current→+pts, live) — PARTIAL (PointCaptureStrip = potential pts; no live entry-anchored counter)
- L4 Live Voice milestone ("+10 Target One achieved") — PARTIAL (VoiceAssistant exists; no premium-milestone announce)
- L5 Opportunity Timer (time-in-stage Early/Building/Runner/Late) — MISSING
- L6 Entry/Exit Meter (★) — DONE `EntryReadinessMeter.tsx`
- L7 AI Target Ladder (86→156) — DONE Radar `_ladder` + `PremiumTimeline`
- L8 Miss Prevention (Look Here / Don't Chase) — DONE `MissedMoveProtection.tsx`
- L9 Dashboard Never Sleeps (Premium ∥ Decision) — DONE (radar per-tick, gate-independent)
- L10 Today Point Capture Mission scoreboard — MISSING

### Real remaining work (build on VERIFIED base after ship)
1. **Opportunity Timer** — premium_radar: record stage-entry timestamps per
   strike; expose `time_in_stage` + stage history. Frontend chip row.
2. **Today Point Capture Mission** — backend aggregate per IST day:
   opportunities_detected, entry_ready_count, (taken/captured need a trade log —
   honest "—" until a position feed exists), missed_points (sum of
   session_high−birth on strikes that ran without a READY surfaced in time).
   Frontend scoreboard card, top of page.
3. **Live Point-Catch counter + milestone voice** — anchor to a user-selected
   HOT strike; count live pts from that ₹; fire 🔔 + speech at +10/+20/+30/+40/+50
   (Target1 / Trail / Runner / Book-partial / Exit-suggested). Deterministic
   thresholds; voice reuses VoiceAssistant speech util.

Note: "Opportunity first, analysis below" REORDER is already the page.tsx
structure in the pending batch — ships with the restart, no new work.

---

## #018 — Institutional Entry Intelligence Engine (IEIE) (owner, 2026-07-13)

North star: not an indicator dashboard — an ENTRY DECISION. Fold structure +
momentum + institutional confirmation into one weighted consensus → Entry Score
→ Trade Plan → WHY/WHY-NOT → Window → Ranking → Narrator.

### Audited against code (2026-07-13) — most of IEIE already exists
- L1 Market Structure (VWAP, pivots, ORB, S/R) — EXISTS (market_context, market_path)
- L2 Momentum — GAP: RSI, Elder Force, Bollinger, SuperTrend, Stochastic ABSENT;
  ATR/ADX only partial; VWAP present.
- L3 Institutional (OI/PCR/IV/Greeks/Chain Wave/Premium Radar/Coil) — EXISTS
- L4 Entry Score /100 — ~EXISTS (Entry Score Timeline, Fire Score, 11-layer checklist)
- L5 Trade Plan (entry/SL/T1-3/trail) — EXISTS (scalping plan)
- L6/L7 WHY / WHY-NOT — EXISTS
- L8 Entry Window Meter — ~EXISTS (Entry Readiness, Signal Maturity)
- L9 Opportunity Ranking — EXISTS (Strike Queue, Index Selector)
- L10 AI Narrator — EXISTS (Voice Narrator, AI Timeline)

### THE real gap
1. Classic TA indicator layer from candles: RSI, ADX (verify existing), ATR,
   ADR, Elder Force Index, Bollinger (expansion/squeeze), SuperTrend, Stochastic
   (owner's "Scotch" = Stochastic; pair with RSI for reversal timing).
2. A single weighted **Indicator Consensus %** (owner weights: CPR20 VWAP15
   EFI12 ADX10 OI10 Volume8 RSI8 Premium7 ATR5 ADR5) → STRONG BUY / WAIT.
   Must remain a DECISION, never a soup of gauges.

### Discipline gate (do NOT build until evidence justifies)
Build only if tomorrow's Black Box shows the miss/loss cause is a CONFIRMATION
gap or false entries — i.e. the indicator consensus would raise point-catch %.
If misses are detection-delay, this engine doesn't help; a different fix wins.
Data note: RSI/ADX/etc need candle history — confirm the candle feed depth
before building. Owner's test governs: "does it raise point-catch %? if no,
don't build even if pretty." Ties to [[cat-lts-freeze-rule]].
