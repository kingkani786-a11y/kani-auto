> **IEIOS PRIME DIRECTIVE:** Every improvement must improve Expected Value
> (EV), not just accuracy. Accuracy alone rising is never sufficient reason to
> build. (owner, 2026-07-20 — this line stands permanently first.)

# Cloud AI Trader X PRO — IEIOS V2.0 Architecture Charter (PERMANENT)
_Adopted 2026-07-17 (owner). This charter supersedes scattered vision docs;
proposals #013–#020 fold into it. It survives every context compaction._

## Mission
Build an **Institutional Entry Intelligence & Optimization System** — an
institutional decision engine, never an indicator panel. Answer only five
questions: (1) Should I trade? (2) Which direction? (3) Is this the right
time? (4) Probability of success? (5) How to manage until exit?

## Objective (not prediction — production)
Consistently produce **High-Probability · Low-Risk · Timely · Well-Explained**
trade decisions. Never chase exact tops/bottoms. Never promise 100%. Optimize
for consistency, probability, risk management, explainability, continuous
learning.

## Twelve independent intelligence layers
Each layer: structured output, independently testable, no duplicated logic/UI.

| # | Layer | Output | Status 2026-07-17 |
|---|-------|--------|-------------------|
| 1 | Market Context (trend/range/breakout/reversal/expansion/compression/gap) | Bias + confidence | EXISTS (regime/DNA) — needs one composite readout |
| 2 | Price Action (swings, BOS, MSS, liquidity sweep, FVG, order block, mitigation, S/R) | PA score, structure quality, entry zone | PARTIAL (structure/BOS yes; FVG/OB/mitigation NEW) |
| 3 | Candle Intelligence (context-gated patterns only) | Candle confidence | NEW |
| 4 | CPR Intelligence (virgin/narrow/wide/trend/range CPR → day-type probs) | trend/range/expansion day % | NEW |
| 5 | Indicator Consensus (VWAP ADX ATR RSI EFI Stoch BB EMA Volume → ONE score, raw never primary) | 0–100 | GATED on false-rate evidence (#018) |
| 6 | Move Prediction (Fake/Small/Medium/Big/Runner + prob, reward, duration, range) | class probs | NEW — black box move-size distribution is the training evidence |
| 7 | Entry Quality (unified) | A+/A/B/C/Reject | PARTIAL (fire score/grades exist — unify) |
| 8 | Institutional Flow (OI ΔOI PCR Greeks radar chain-wave coil) | Institutional confidence | EXISTS |
| 9 | Trade Execution (entry/ideal zone/SL/T1-3/trail/partials, adapts live) | plan | PARTIAL (plan exists; live adaptation = V5 L8 tracker) |
| 10 | Trade Review (grade every completed trade A+–D + why) | review | PARTIAL (audit tracker → add grading) |
| 11 | Black Box Learning (context, decision, PnL, delay, confidence, outcome, root cause, entry edge, wave_n, cold_start — replayable, never lose data) | log | EXISTS (opportunity_log) |
| 12 | AI Decision Brain (only layer users see): BUY/WAIT/EXIT/NO TRADE + reason, confidence, risk, plan, expected move, exit strategy | decision | EXISTS (Decision Engine v5) — consolidate presentation |
| + | **AI Challenger** — every BUY challenged (reasons NOT to buy/sell, weaknesses, hidden risks; strong disagreement ⇒ WAIT) | challenge | PARTIAL (devil's advocate line → formalize as gate) |
| + | **AI Doubt Engine** — every decision carries explicit uncertainty + weaknesses | doubt | PARTIAL (WHY-NOT exists → attach to every decision) |

## Dashboard rule — THREE sections only
1. Market Context · 2. Opportunity Engine · 3. Decision Engine.
No indicator dashboards, no gauge farms, no repeated information. The user
never interprets indicators — the AI interprets everything.

## Engineering rules (the gate for every feature)
A feature ships only if it improves ≥1 of: **Higher Win Rate · Lower Risk ·
Lower Decision Time.** Otherwise reject. Low latency, modular, strong logging,
replayable, versioned, deterministic outputs.

## Continuous learning
Learn from: black box, trade reviews, historical performance, regime, entry
edge, false signals, missed opportunities. Adaptive weighting allowed.
**Rule changes always require manual approval.**

## Doctrine boundary (carried forward, non-negotiable)
The system NEVER places orders. "Trade Execution Engine" = plan generation +
live tracking of the USER's manually executed trade. LLM never decides
(explain/research only). Capital protection > profit. Honest UNKNOWN over
fabricated data. Informational only — not investment advice.

## Final mission
Every module answers one question: **"Is this the highest-probability trade
available right now, and if so, how should it be executed and managed?"**

---

# V2.1 Governance Charter (owner, 2026-07-17 evening)

## The ten governance rules
| # | Rule | Status map |
|---|------|-----------|
| 1 | **AI never guesses** — no data / poor quality / indicator conflict ⇒ WAIT; confidence never inflated | EXISTS (honest-UNKNOWN convention, data-quality gates, kill switch) |
| 2 | **Every BUY earns its right** — Structure + Price Action + Institutional + Risk + Execution ALL PASS, else no BUY | EXISTS (11-layer checklist + final gate) — map to these 5 named pillars |
| 3 | **Confidence is evidence** — 95% must decompose (Trend 19/20 + PA 18/20 + …= 95) | PARTIAL (WHY-CONFIDENCE has component weights → render as the /20 ledger) |
| 4 | **Explain every BUY** | EXISTS (WHY panels) |
| 5 | **Explain every WAIT** + expected wait (e.g. 2–4 candles) | EXISTS (WHY-NO-TRADE) + expected-wait estimate = NEW |
| 6 | **Every miss teaches** — multi-question autopsy (late detection? wrong confirmation? liquidity? trap? human delay?) | PARTIAL (root_cause single tag → extend to autopsy checklist) |
| 7 | **Perfect Entry Score** — A+…Reject with timing/risk/momentum/probability breakdown | PARTIAL (grades scattered → unify, = charter L7) |
| 8 | **Entry Window Meter** — how long is this BUY valid, live countdown (OPEN 52s → Closing 12s) | NEW (window label exists; live seconds = new) |
| 9 | **Confidence decay** — stale signal decays 95→91→87→81→WAIT; never hold an old BUY | PARTIAL (Signal-Aging/STALE exists → formalize the decay ramp) |
| 10 | **Trade Personality** — SCALP / Momentum / Trend Runner / Expiry Gamma / Reversal per signal | EXISTS (Animal + regime playbook → surface as personality label) |

## Decision Contract (the unifier — entry/hold/exit in ONE logic)
Every BUY ships as a contract: action · confidence · risk · expected move ·
expected holding time · RR · **pre-stated invalidations** (e.g. VWAP breakdown
OR OI-support loss OR ADX<18) · and the standing instruction: invalidation ⇒
EXIT immediately. The radar's AI-Thinking invalidation + decision SL/targets +
exit intelligence merge into this single object. This is how the platform stops
being a signal generator and becomes trade management (ties V5 L7 User-Confirm
and L8 Trade Tracker together).

## Mission statement (final)
Not "what does this indicator say?" — but: "Combining ALL market evidence at
this second, should a high-probability, low-risk, well-rewarded action be
taken?" An Institutional Decision Engine.

## Rule 11 — Explain Before Execute (owner, 2026-07-19)
The AI never outputs a bare BUY or NO TRADE. Every action ships with its
because-clause (Trend + Institution + Momentum + Risk …), and every WAIT with
its WHY. Implemented as the Decision Contract's mandatory `why` block —
explainability is institutional table stakes.

---

# IEIOS V3.0 — Evidence Intelligence OS (owner, 2026-07-19) — PERMANENT VISION

V2.1 foundations + five new evidence systems. Governance unchanged and absolute:
AI may learn/analyse/compare/recommend/rank/measure/calibrate/hypothesise;
AI must NOT modify rules, rewrite thresholds, change execution logic, deploy
code, execute trades, or bypass human approval.

## New systems over V2.1 (all evidence-gated, none built yet)
1. **Historical Market Intelligence** — ~100 trading days via Dhan API (spot,
   futures, chains, OI, premium, IV, greeks, VWAP, breadth, VIX, expiry/gap/
   trend/range behaviour) → the Market Memory.
   ⚠ HONEST CONSTRAINT (verify before promising): Dhan provides historical
   CANDLES (spot/futures/index — 100d likely fine) but historical OPTION-CHAIN
   SNAPSHOTS (per-day OI/IV/premium ladders) are generally NOT retro-fetchable.
   Chain-history depth must be accumulated FORWARD (daily EOD snapshot job,
   like the black box) — Market Memory matures over weeks, not on day one.
2. **Market Memory Engine** — today vs history: "seen this before? N sessions
   resemble → continuation 68% / range 21% / false-break 11%." PARTIAL today:
   Market DNA (Phase 20) already does historical-similarity matching — V3.0
   deepens it with the forward-accumulated chain library.
3. **Strategy Ranking Engine** — Coil, Path-2, Wave, Momentum, Flow, PA, False-
   Breakout, Liquidity-Sweep ranked ONLY by measured performance.
   RECORD-OR-LOSE: the black box does not yet tag WHICH ignite path/strategy
   fired each alert — that tag must be recorded before ranking is possible.
4. **Confidence Calibration** — shown % auto-adjusted statistically from
   realized outcomes (92% shown → 64% real ⇒ future display corrected).
   Agreed sequencing: build after 2–3 weeks of black-box data.
5. **Research AI** — continuous hypothesis generation ("VWAP delay may cut
   false signals, expected +7%, evidence 2 days, confidence 81%") — every
   hypothesis needs human approval (extends Weekend AI; Knowledge Law applies).

## Success metrics (continuous)
Capture Rate · Detection Delay · False Rate · Money Recovered · Missed Rate ·
Entry-Grade Success · Calibration Error · Pattern Accuracy · Regime Accuracy ·
Decision Consistency.

## Sequencing note (validation lock, 2026-07-19)
Monday = VALIDATE ONLY (C6 + V2.1 live). V3.0 systems build in evidence order:
(a) forward chain-snapshot recorder + strategy-tag recorder (record-or-lose
instrumentation — the raw material for 1/2/3/4), (b) then Market Memory
derivations, (c) calibration after data depth, (d) Research AI last.

---

# IEIOS V4.0 — Institutional AI Decision Platform (owner, 2026-07-20 evening)

Terminal architecture vision, layered on top of the observe→understand→predict→
decide→execute→learn→self-evaluate→research→knowledge-update loop used by
frontier AI systems. NINE new layers over V3.0:

1. **AI Research Engine** — nightly: winner/loser commonalities, why-late, why-
   miss, best/worst RR setup → dated Research Reports ("Path2 works better after
   11:20, 86% prob, recommend confidence +4%") → PENDING APPROVAL, never auto-applied.
2. **Knowledge Graph** — not facts, RELATIONSHIPS (Narrow CPR → Big Move → Low
   VIX → OI Build → Coil → Path2 → Winner). The structure GPT-style systems lean on.
3. **Market DNA (deepened)** — daily/weekly/monthly DNA, not just 100-day
   candles; "today resembles 12-Mar-2026 at 82% similarity → big move after
   11:40 that day."
4. **Multi-Agent AI** — 5 opinion-agents (Price Action / Flow / Option / Risk /
   Research) + a Judge AI for final synthesis — reduces single-model hallucination.
5. **Challenger AI** — every BUY/WAIT/EXIT gets a formal "why NOT" debate
   (extends Rule 11 + Devil's Advocate already in Decision Intelligence).
6. **Confidence Calibration** — shown 90% vs realized win-rate, continuously
   measured and corrected (ties to V3.0 Confidence Calibration, same gate).
7. **Strategy Ranking** — Path2/Coil/ChainWave/etc ranked by 100-day measured
   win%+RR, AI-generated table, never hand-written.
8. **Market Regime Memory** — trending/range/expiry/holiday/gap/event days each
   carry their own learned behaviour profile.
9. **Continuous Learning discipline** (reaffirms V3.0 governance): Observation →
   Research → Suggestion → HUMAN APPROVAL → Deploy. AI never rewrites its own
   rules — restated here because it is the hinge the other 8 layers depend on.

## Explicitly rejected (owner, cost > benefit)
40+ raw indicators · duplicate scores · unexplainable deep-net predictions ·
AI auto-order execution · confidence scores that can't be explained.

## V4 pipeline (canonical, supersedes prior diagrams)
Market Data → Market Intelligence → Detection Engine → Institutional Decision
Engine → Decision Contract → Execution Intelligence → Trade Review → Black Box
Recorder → Research AI → Knowledge Graph → Market DNA → Strategy Ranking →
Confidence Calibration → Human Approval → Production.

## Build gate (unchanged discipline, stated explicitly for V4)
Layers 1/2/3/6/7/8 are DATA-HUNGRY — they derive patterns/relationships/
calibration/rankings FROM the black box, which as of 2026-07-20 has ~1 mixed-
result validation day (C6 needs 3: Mon done, Tue+Wed pending). Building any of
these now would be fitting a model to one noisy day. Sequencing: finish the 3-
day C6 window → let 2-3 MORE weeks of clean black-box data accumulate (the
owner's own stated calibration timeline applies to all of 1/6/7 equally) → THEN
layers 4/5 (Multi-Agent, Challenger) which are architecture, not data-dependent,
can be prototyped in parallel since they restructure REASONING over existing
engine outputs rather than requiring history. Layer 9 is already governing.

---

# IEIOS V4.1 — Core AI Principles (owner, 2026-07-20 night)

## Principle 1 — AI Memory ≠ Data Storage
The black box stores episodes; the AI must distill EXPERIENCE → PATTERN →
CONFIDENCE → LESSON, not just retain rows. ("When these 5 conditions co-occur,
win probability rises" — a lesson, not a record.) This is what Research AI (V4
layer 1) must output, not raw stats.

## Principle 2 — Adaptive Knowledge (versioned, decaying)
The Knowledge Graph (V4 layer 2) is not static — each edge/fact carries
confidence, evidence-count, last-updated, accuracy, and versions forward
(v18→v19→v20). Knowledge with eroding accuracy retires itself automatically —
this is DATA-DRIVEN pruning, distinct from the RULE-change approval gate (Rule
9/Governance): the knowledge graph adapts on evidence; trading RULES still
never change without human approval.

## Principle 3 — Explainable AI (not just predictive)
Every BUY decomposes into its pillars with values, not a bare confidence number
— this is the Evidence Ledger (already shipped, V2.1 C3) generalized as a
platform-wide requirement: no score without its breakdown, anywhere in IEIOS.

## GOLDEN RULE — AI Never Chases Accuracy
Optimize **Expected Value** (win% × avg-win − loss% × avg-loss), not accuracy.
90% accuracy at 0.5 RR loses to 62% accuracy at 3.4 RR. Priority order: Expected
Value → Consistency → Risk-Adjusted Return. Accuracy is a secondary, diagnostic
metric — never the target a feature is judged against. This reframes every KPI
in the Capture Score / Entry Grade / Strategy Ranking: report accuracy, but
GATE on EV.

## V5 (noted, not started) — AI Mentor
Post-trade coaching for the HUMAN, not just the system: "profit, but late
entry" / "loss, but the decision was right — execution was the miss" / "should
never have been taken — MTF conflict + VWAP reject + weak flow." Distinct from
Trade Review (V3 layer 10, which grades the SYSTEM's call) — Mentor grades the
USER's execution against that call. Deferred behind V4.

## UNIVERSAL BUILD GATE (supersedes/absorbs the engineering-rules gate stated
earlier in this charter — this is now the single filter for every future layer)
A new AI layer ships ONLY if it is simultaneously:
1. **Measurable** in the Black Box (a concrete field/metric it moves),
2. **Explainable** (decomposes to named, inspectable components — no bare
   scores), and
3. **Governed** (subject to human approval before any rule/threshold changes).
Fail any one → do not build, regardless of how compelling the idea sounds.

---

# IEIOS V4.2 — Institutional Decision Governance (Final Governance Layer, owner 2026-07-20 night)

## Rules
1. **Decision ID** — every BUY/WAIT/EXIT gets a unique ID (timestamp-based),
   carrying confidence/EV/RR/regime/supporting-evidence/outcome=Pending — full
   audit trail per decision.
2. **Confidence Calibration** — shown-% vs realized-win-% by confidence band
   (92-100 → actual 91% ✓ / 80-90 → actual 64% ✗) — ties to V3/V4 calibration,
   same 2-3wk data gate.
3. **Expected Value on every recommendation** — EV(+1.87R)/RR/holding-time/
   failure-probability alongside confidence, not confidence alone.
4. **AI Self-Challenge MANDATORY** — Challenger AI (V4 layer 5) must run on
   EVERY decision, not opportunistically — this hardens layer 5 from "exists"
   to "always-on."
5. **Decision Replay** — replay a single trade's own timeline (coil→volume-up→
   trail-start→exit) so the AI can inspect "what did I know, when."
6. **Strategy Lifecycle** — Created→Validated→Active→Weak→Retired; no strategy
   is permanent, evidence-triggered retirement (ties to V4 Strategy Ranking).
7. **Human Override Log** — record AI-said-X/user-did-Y/result-Z (both
   directions: overridden-and-lost, overridden-and-won) to measure the AI
   recommendation's own value net of the human's judgment.
8. **Weekly Learning Report** — auto-generated: signal count, best/worst
   strategy, accuracy, EV, new pattern, retire-candidate.

## Final Institutional Rule (mission statement, supersedes prior phrasing)
> "The AI's objective is not to predict the market. Its objective is to
> maximize long-term risk-adjusted expected value through explainable,
> evidence-backed, governed decisions."

## Honest categorization against the Universal Build Gate (V4.1)
Applying Measurable+Explainable+Governed to these 8, split by data-dependency
(the same lens used for V4's 9 layers):

**Buildable now (bookkeeping/architecture, NOT blocked on data maturity):**
- Rule 1 (Decision ID) — pure tagging, strengthens the audit trail Monday's
  own validation report needed (episodes already lack a stable ID across restarts).
- Rule 4 (mandatory self-challenge) — formalizing an always-on requirement is
  architecture, not history.
- Rule 5 (Decision Replay) — the black box ALREADY carries coil/ignite/peak/
  exhaust timestamps + score trajectory per episode; a replay view is a pure
  derivation of data already captured, not new history.

**Data-hungry (blocked until the stated gates clear):**
- Rule 2 (Calibration) — needs 2-3wk (owner's own timeline, V3/V4).
- Rule 3 (EV number) — a REAL expected-value figure needs realized win-rate
  history; until then it would be a fabricated number wearing an EV label —
  violates Rule 1 (AI never guesses). Defer with Calibration.
- Rule 6 (Strategy Lifecycle) — needs the strategy-tag recorder (flagged
  2026-07-17, still pending) before any strategy can be ranked or retired.
- Rule 8 (Weekly Report) — needs a full week of clean post-C6 data.

**Blocked on a DIFFERENT gap (not data-hungry, but missing a prerequisite):**
- Rule 7 (Override Log) — needs V5 Layer 7 (User Confirm / actual-entry
  tracking, noted since the V5 charter) to know what the user actually did;
  the system cannot log an override it never observes.

## Sequencing note (this section is the last vision addition per owner)
No further architecture layers after V4.2 — the owner has closed the vision
phase. All future work executes existing charter layers in evidence order,
inside the validation discipline already governing C6 (3-day window) and
calibration (2-3wk). The "buildable now" items above are NOTED, not started,
absent a separate explicit go-ahead — they do not override the Tuesday lock.

---

# IEIOS EXECUTION DOCTRINE (FINAL — owner, 2026-07-20 night)
_This is not a layer. It is the process that governs every future layer.
Charter architecture is now FROZEN — no new layers for 2-3 weeks per this
doctrine. What follows is the only lens for any future proposal._

## The 5 Gates — mandatory for every future feature, no exceptions
1. **What problem does this solve?** (Detection Miss? Late Entry? False
   Signal? Poor Exit? User Confusion?) No clear problem ⇒ no build.
2. **Can the Black Box measure it?** Must state Current → Build → Expected KPI
   Change BEFORE building (e.g. "Coil Memory: Misses 12 → expected 6"). Can't
   measure ⇒ no build.
   - **Documented exemption — Category 2 (Visualization) only** (owner,
     2026-07-21): pure presentation work is exempt from Gate 2 when it
     provably changes no decision logic, no threshold and no engine — i.e. it
     only re-renders values the backend already publishes. Rationale: the
     Black Box measures *market episodes* (capture %, detection delay, root
     cause); it has no UI instrumentation, so decision latency / interaction
     depth / time-to-first-action are **not measurable today** and no code
     path can produce them.
   - **The honest cost of this exemption, stated plainly:** UX improvements
     under it are *asserted, never proven*. The 2026-07-21 UX passes 1–4 ran
     this way de facto, and each was followed by "still too much
     information" — unmeasured UX iteration converges slowly, by observation.
   - **Limits.** The exemption does NOT cover: anything touching decision
     logic/thresholds (Gate 2 applies in full), or any claim that a UX change
     improved a *trading* KPI (EV, capture %, false %) — such a claim needs
     real measurement like any other. Building actual UI telemetry, to make
     Gate 2 genuinely satisfiable for UX, remains open as a Category-1 item.
3. **Can an existing engine derive this?** (Price Action + Institutional Flow +
   Consensus + Black Box already there?) If yes ⇒ no new engine — extend
   existing derivation instead.
4. **Is it explainable?** "BUY" alone is insufficient; must be "BUY because…".
   Unexplainable AI output never reaches production.
5. **Does it need human override?** AI never changes its own rules — it only
   ever proposes; approval is always the human's.

## Development Priority Pyramid (this ordering itself is doctrine)
- **Level 1 (highest) — Measurement:** Black Box, Recorder, Evidence, Governance
- **Level 2 — Decision Quality:** Contract, Grade, Replay, Challenge
- **Level 3 — Prediction:** Memory, Research, Knowledge Graph, Strategy Ranking
- **Level 4 — Self-Learning:** Calibration, Adaptive Knowledge, Mentor

Reading: for this platform, measuring correctly outranks the AI learning
anything — Level 1 is not infrastructure to rush past, it IS the priority.

## The failure mode this doctrine exists to prevent
Most trading-AI projects die from: Idea → Feature → Another Feature → Another
Feature (unbounded accretion, never validated). This project's loop instead:
Idea → Charter → Validation → Evidence → Decision → Build. Every idea earns a
charter entry; only evidence promotes a charter entry to a build.

## Standing instruction (effective now)
No new architecture layers for 2-3 weeks. Instead: keep the charter frozen,
keep collecting Black Box data, keep producing validation reports, keep
watching KPI trends, and implement ONLY features that already pass all 5 gates
above with real evidence behind them. V5/V6 evolution must emerge FROM the
data, never from a fresh idea arriving out of sequence.

---

# IEIOS Prime Directive & Permanent Rules (owner, 2026-07-20 — final entry)

## Golden KPI Hierarchy (dashboard + every report, in this order — EV first, Accuracy last)
1. **Expected Value (EV)** ⭐
2. Recovery %
3. Drawdown
4. Risk : Reward
5. Decision Consistency
6. Capture %
7. False %
8. Accuracy % — diagnostic only, never the target

## Permanent Rules (never violated)
- **Rule A** — No Black Box → No Build
- **Rule B** — No Measurement → No Decision
- **Rule C** — No Evidence → No Rule Change
- **Rule D** — No Human Approval → No Deployment

## Future Build Categories (all future work sorts into exactly one)
1. **Measurement** — Black Box, Recorder, Metrics, Evidence
2. **Visualization** — Dashboard, Replay, Contract, Reports, Charts
3. **Intelligence** — Research AI, Knowledge Graph, Memory, Strategy Ranking, Calibration
4. **Execution** — Decision Engine, Entry, Exit, Risk, Trade Management

## Current status (owner's assessment, 2026-07-20 night)
- **✅ FROZEN:** Architecture · Decision Logic · Governance · Development Process
- **🔄 OBSERVE (daily):** C6 Validation · Feed Stability · Black Box · KPI Trend · EV Trend
- **⛔ NOT building:** new indicators · new layers · new scores · new AI models
- **✅ Can still build (measurement/visualization only, evidence-gated):**
  Recorder extensions · Reports · Visualization · Investigation tools · Debug
  instrumentation — i.e. Categories 1 & 2 above remain open; 3 & 4 wait for evidence.

## Daily discipline for the freeze window (2-3 weeks)
Not one line of Decision Logic changes. Daily: Market Replay, Validation
Report, KPI Trend, Root Cause Analysis. Weekly: Weekly Review. After 3 weeks,
Black Box data — not a new idea — nominates the next feature.

## Closing assessment
Charter + Governance + Execution Doctrine + Prime Directive together make this
an Institutional-Grade AI Decision Platform Development Framework, not a
trading dashboard. Ideas no longer drive this project's growth. Evidence does.

---

# V6 Trader UX — APPROVED SPEC, DEFERRED BUILD (owner, 2026-07-21)

Owner's V6 proposal, run through the 5 Gates. **Gates 1/3/4/5 pass.** Gate 2
does not pass as originally written (it claimed decision-latency / scroll-depth
/ confirmation-time were measurable — they are not; no UI telemetry exists) and
proceeds instead under the **Category-2 Visualization exemption** recorded
above. Classification: **UI/UX refactor, NOT a Decision Engine change.**

## Sequencing decision (owner, 2026-07-21)
C6 validation comes FIRST. V6 builds only after the 15:30 close. Rationale:
2026-07-21 is C6 validation day 2 of 3, and a **backend** restart wipes
`premium_radar._tracks` (the known, still-unfixed P0 phase-2 gap) — i.e. the
exact coil state C6 is measuring. Frontend-only restarts do not carry that risk.

## Target layer order
1 Trade Light · 2 Decision Hero · 3 WHY Checklist · 4 Execution · 5 Radar ·
6 AI Thinking · 7 Research · 8 System

## Build list, by risk

**A. Frontend-only (data already in the API payload — no backend restart):**
- **Confidence meter + 5-pillar breakdown.** The Evidence Ledger already
  computes this (`ledger[]`, /20 per pillar; Institutional / Price Action /
  Risk match the owner's list literally). *Regression note: this was rendered
  until UX pass 3 (commit 1763a41) trimmed DecisionContract.tsx; only the bare
  total survives. V6 is partly asking to undo an over-trim.*
- **Entry-window countdown in the hero.** `entry_window_live` is computed every
  cycle and has had **no consumer at all** since that same pass-3 trim.
- Bigger Runner badge ("23/100 · EARLY BUILD") — `runner_tag` exists.
- Bigger Grade badge + sub-scores — `entry_grade.parts` is close but not
  identical to the owner's Signal/Execution/Risk split.
- `MANUAL EXECUTION` label. **No BUY button has ever existed** in this
  codebase — the "AI never trades, human executes" rule is already satisfied
  structurally; this label only makes it visible.
- Panel reorder to the 1–8 order above.

**B. Needs backend (deploy at close only):**
- WHY checklist 4 items → 7 (add Calibration PASS, Structure PASS, Volume
  PASS to `buy_checklist` in `decision_contract.py`).

## Open Category-1 item (not scheduled)
UI telemetry — decision latency, interaction depth, time-to-first-action — so
Gate 2 becomes genuinely satisfiable for UX work instead of exempted.

## V6 spec revision (owner, 2026-07-21 pass 5) — THRESHOLDS CHANGED

**Runner bands REVISED** (supersede the 25/40/60/80 set shipped in 1c8893b):
`0-29 Ignore · 30-49 Watch · 50-69 Prepare · 70-84 Ready · 85-100 Buy Candidate`
Owner's rule: "70க்கு கீழே நான் entry பார்க்க மாட்டேன்" (no entry below 70).
Live code currently labels 60-69 as "BUY Candidate" — actively contradicts this.

**Stars must be re-derived from the SAME bands.** `_stars()` is `1 + score//20`
(cuts at 20/40/60/80) which disagrees: it gives 82 → 5★ while the owner's own
hero example says Runner 82 → READY → ★★★★☆ (4★). One threshold set must drive
band + tag + zone + stars. New: `<30=1★ · 30-49=2★ · 50-69=3★ · 70-84=4★ · 85+=5★`
Star meanings: 1 Ignore · 2 Watch · 3 Prepare · 4 Ready · 5 Buy Candidate.

**Other Level-1/2 items:** Best Strike · Entry Grade (D/C reject, B watch,
A ready, A+ buy) · Risk YES/NO · R:R ≥1:3 · BUY Checklist 7/7 (adds Structure,
Volume, Calibration to the existing 4) · AI Thinking as a 7-item checklist
(Premium/Structure/Flow/Volume/Risk/Wave/Calibration) · Decision Contract cut
to 2 lines (ENTRY + EXIT IF). Premium: Building=Observe, Growing=Prepare,
Exploding=Buy Candidate. Wave: Bullish⇒CE only, Bearish⇒PE only, Range⇒avoid both.
Early Warning / COILED / SPRING / HOT NOW are explicitly NOT buy signals.

### THREE CONFLICTS — must be resolved by the owner before building
1. **Trade Light loses the in-position states.** Proposed 5 states
   (🔵 STRONG BUY · 🟢 BUY · 🟡 PREPARE · 🔴 WAIT · ⚫ NO TRADE) are ALL
   pre-entry. Live mapping uses 🔵=RUNNING (holding) and ⚫=EXIT. Adopting the
   new list as-is **deletes the EXIT signal** — the one that tells a trader to
   get OUT of an open position. Safety-relevant; not a cosmetic reassignment.
2. **`[ MANUAL BUY ]`** is drawn like a button, but pass-3 instruction was
   "BUY button இல்ல... MANUAL EXECUTION என்று மட்டும்". Reading it as a
   NON-clickable label (system never places orders — permanent doctrine).
3. **Decision Contract at 2 lines drops the stop-loss** from that card. SL
   must stay visible in the hero's Entry/SL/T1-T3 row, or capital protection
   loses its display. Do not remove both.

## EXECUTION DASHBOARD ROADMAP — LOCKED (owner, 2026-07-21 01:15 IST)

Sequencing agreed: **today = C6 validation ONLY.** No deploys during the
session. The Execution Hero pass lands after the 15:30 close.

**Locked priority order:**
1. **Hero Premium Bug (CRITICAL)** — TradeNowCard labels UNDERLYING INDEX
   levels as Entry/SL/T1-3. A "7850 PE" card reads "Entry 7,927 · SL 7,944"
   — NIFTY points, readable as the option price. Fix: show `premium_entry`,
   `premium_stop_loss`, `premium_target1/2/3` (already written by
   strike_selector.py); demote index levels to small print labelled
   "Underlying". Owner: an option buyer could misread ₹7927 as the premium.
2. **Dead Backend Keys (CRITICAL)** — `execution_card.py` reads
   `premium_sl` / `premium_targets`; strike_selector writes
   `premium_stop_loss` / `premium_target1..3`. The read names are NEVER
   written anywhere. Effect: SL is always None ("SL ₹None" in the actionable
   line) and the target list is always empty. Backend consistency bug.
3. **Strike Intelligence** — "Why THIS strike?" from existing
   selection_score / spread_pct / prob_itm / greeks. Category 2.
4. **Live Entry Status (NEW, owner 2026-07-21)** — showing BUY RANGE alone is
   not enough; the card must answer "can I buy RIGHT NOW?":
   `NOW ₹499 🟢 INSIDE BUY RANGE` · `NOW ₹507 🟠 ABOVE ENTRY — wait pullback`
   · `NOW ₹492 ⚪ BELOW ENTRY — watch`. Pure comparison of live premium
   against the entry band; no new logic.
5. Position Manager — BLOCKED: needs a user-confirmed entry path that does
   not exist (V5 L7 User-Confirm, noted-not-built). Not derivable.
6. Exit Intelligence — engine exists; surfacing depends on (5).
7. Trade Review / AI Mentor — AFTER C6 validation completes.

**Mentor clarification (owner).** The freeze is a *Decision Logic* freeze.
A Mentor that reviews a trade AFTER completion does not modify the decision
engine, so it is not inherently freeze-violating — but it stays **Future
Phase, NOT NOW**. Recorded so the earlier "❌ Mentor AI" line is read as
sequencing, not a permanent prohibition.

**Owner's framing for this pass:** the Execution Hero is already ~80% built.
Do not write a new hero — `correct + complete + clean` the existing one.
Order of value: correctness first, then clarity, then new capability.

## C6 ACCEPTANCE RULE — PRE-REGISTERED (owner, 2026-07-21 ~01:30 IST)

Locked BEFORE the evidence arrives, deliberately: a criterion chosen after
seeing the data is a rationalisation, not a test.

**Why the original 3-day window cannot settle C6.** Corrected capture% (phantom
falls removed) per session: 19% · 67% · 83% · 81% (pre-C6) · 60% (post-C6 day 1).
Pre-C6 spread is 19–83%; Monday's 60% sits inside it. Between-day SD ≈ 30pp, so
detecting even a 15pp effect at day level needs ~16 sessions per arm. Three days
was never enough — and the owner's first proposal ("5–10 real runner events")
does not bind either, since one active session supplies 80+ runner events
(Jul-16 had 86). The scarce resource is SESSIONS, because the noise is daily.

**The deeper problem (fixed today).** C6 *is* ignite path 2 (the was_coiled-gated
slow-runner breakout). `record()` received only `coil_state="IGNITING"` — the
path was discarded at the boundary, so NO recorded field could attribute any
outcome to C6. Under Rule B (No Measurement → No Decision) C6 could never have
earned a verdict at all. This is validation starvation in its literal form:
sessions spent collecting data that cannot answer the question.
Fixed pre-market: `_coil()` now returns `path` (1 = velocity spike, 2 = C6
breakout, 0 = none) and it is persisted as `ignite_path` on every black-box line.

**THE RULE (mechanism-based, not day-level):**
- C6 is judged on **≥30 recorded path-2 (`ignite_path == 2`) ignitions with
  settled outcomes**, scored on THOSE events' EARLY / LATE / FALSE rates.
- n grows per EVENT, not per session, which isolates C6 from market-condition
  variance — reachable in days rather than the ~16 sessions a day-level test needs.
- Until 30 such events exist the verdict is **EVIDENCE INSUFFICIENT**. Never
  "Accepted", never "Rejected". ("Evidence decides. Assumptions wait.")
- Sessions before 2026-07-21 carry NO `ignite_path` and are therefore excluded
  from the path-2 count — the counter starts at today's open.

**Also pre-registered:** day-level capture% may be reported for context but is
NOT the acceptance criterion, precisely because its variance is known to swamp
the effect size.

**Phase 2 (at close) gains one item:** a Validation Status card under Build
Version — `C6 VALIDATION · Day n · path-2 events k/30 · EVIDENCE INSUFFICIENT`
— driven by this rule so the system states its own evidential standing.

## C6 STRATIFICATION — PRE-REGISTERED (owner, 2026-07-21 ~02:00 IST, before open)

Locked before today's expiry session produces any data.

- **Primary C6 verdict: NORMAL sessions only.** The 30 path-2 threshold counts
  ONLY events with `session_type == "NORMAL"`.
- **Expiry sessions: reported separately**, never merged into the primary sample.
- **Mixing the two into one sample is forbidden.**

Rationale: expiry is a different POPULATION, not a noisier version of the same
one. Theta crush inverts what a COILED reading means; `RUNNER_PCT=30%` is
cleared by a ₹5 option touching ₹6.50; `MIN_RUNNER_PTS=5` flips from a floor
into a huge move when strikes trade ₹2-20; gamma makes near-ATM premiums
non-linear. A verdict drawn from a mixed sample would describe expiry
behaviour while claiming to describe normal behaviour.

Later, and separately, the data may justify a distinct "C6 Expiry Mode" — that
is a future decision, not part of this verdict.

### Two stratification axes, deliberately NOT merged
The owner asked for a `market_regime` field. Recorded as TWO fields, because
two different things could claim that name and collapsing them would destroy
the very stratification requested:
- **`session_type`** — the CALENDAR axis, a fact about the DATE:
  `NORMAL` · `EXPIRY` (dte==0) · plus anything the owner declares.
- **`regime`** — the TAPE axis, from the existing `engines/regime.py`:
  `TRENDING` · `HIGH_MOMENTUM` · `VOLATILE` · `LOW_MOMENTUM` · `RANGE_BOUND` ·
  `EXPIRY_PINNING`.
Together these give "C6 on Expiry", "C6 on Normal", "C6 on High Volatility"
— all three slices the owner named.

**Budget Day / RBI Policy are NOT auto-detected.** This system has no economic
calendar, and inventing detection would be fabricated data. They are DECLARED
by the owner in `data/session_calendar.json` (`{"2026-02-01": "BUDGET"}`); a
declaration overrides the derived value, and absent one the day is NORMAL (or
EXPIRY when dte==0). Honest UNKNOWN over a guess, per doctrine.

### `validation_bucket` — the sampling rule, made machine-readable (owner, 2026-07-21)
One derivation in `opportunity_metrics._validation_bucket()`, so the code can
never drift from the pre-registered rule above (same principle as the single
runner-threshold table):

| condition | bucket | meaning |
|---|---|---|
| `session_type == NORMAL` | `PRIMARY` | counts toward the 30 path-2 events |
| `session_type == EXPIRY` | `SECONDARY` | reported separately, never merged |
| `session_type == UNKNOWN` | `EXCLUDED` | conditions unknown — must not contaminate |
| root_cause FEED_OUTAGE / BROKER_COOLDOWN | `EXCLUDED` | a data-availability failure is not a detection outcome |

`WHERE validation_bucket='PRIMARY'` is now the whole C6 dataset definition.

**Contamination fix found while building this.** `_session_type()` previously
returned `NORMAL` whenever `dte` was unavailable — which happens on the first
ticks after open, before the expiry layer publishes. Those episodes would have
landed silently in PRIMARY while asserting a session condition we could not
actually know. It now returns `UNKNOWN` (→ EXCLUDED), and `_black_box()` makes
one best-effort re-resolve at close, by which time the layer has normally
published — so genuine episodes are not lost to over-exclusion.

### Timezone audit (2026-07-21) — one fixed, 13 logged
`dte` is now load-bearing: it decides `session_type` → `validation_bucket` →
which dataset an episode counts in. It was computed with
`datetime.date.today()` (SERVER-LOCAL date), which `core/clock.py` exists
expressly to forbid — its docstring records two prior Greeks failures from
naive datetime reads. The machine is currently in IST so results were correct,
but a timezone change would have silently dropped expiry episodes into the
PRIMARY C6 sample. Fixed in `engines/expiry.py` to use the IST clock.

**Deliberately NOT fixed today:** 13 further naive wall-clock reads exist
(`broker/dhan.py` ×4, `engines/regime.py`, `engines/probability.py`,
`engines/scalp_radar.py`, `services/global_feed.py` ×3,
`services/historical_learning.py`, `services/market_service.py` ×2). All are
currently correct because the host is IST. A 14-site refactor immediately
before a validation session is disproportionate risk; logged as a follow-up
audit item to be done in a quiet window, not on a live day.

## INCIDENT + RESEARCH MODE (2026-07-21, live session)

**Incident.** A synthetic episode from my own verification run leaked into
production measurement state. Verification called `opportunity_metrics.record()`
directly; `record()` triggers `_checkpoint_open()`, which writes to the
PRODUCTION `data/opportunity_log/` path — there is no test isolation. The
02:15 backend restart then ran `_restore_open()` and loaded it into live memory.
Because `report()` includes open episodes, it was counted in live KPIs:
`detected_early` read 1 when the true value was 0, and `capture_rate` read 8.3%
when the true value was 0%.

Scope: LIVE KPIs distorted only. It could never close (no further ticks for
that key), so it never reached the persisted `.jsonl`, never reached PRIMARY,
and `_eps.clear()` discards it at day roll. Deliberately NOT hot-fixed — the
only purge is a backend restart, which would wipe `premium_radar._tracks` (the
real coil state then producing C6 data). Destroying real evidence to remove one
fake row is the worse trade.

Classification: not a decision, trading or execution bug — a **testing
isolation** bug. The production path was the DEFAULT, so writing to it required
no explicit intent.

**RESEARCH MODE (owner, to build at close).** Isolation by convention would
fail again; it must be structurally impossible to touch production data
without saying so.

| context | data path | checkpoint | restore | jsonl write |
|---|---|---|---|---|
| PRODUCTION (explicit only) | `data/opportunity_log/` | yes | yes | yes |
| TEST | `tmp/opportunity_log/` | yes | yes | yes |
| RESEARCH / UNIT TEST | memory only | **never** | **never** | **never** |

Implementation agreed: `CAT_RESEARCH_MODE=1` sets a module flag that makes
`_checkpoint_open()` and `_restore_open()` no-ops and skips the disk write in
`_close_episode()` (in-memory `_closed` still populated, so assertions work);
`CAT_DATA_DIR` redirects `_LOG_DIR` wholesale. Every future verification script
must run under it.

**Close-pass list (5):** Execution Hero · Validation Card · `Premium Building`
→ `Premium Strength (Weak)` · Test isolation · Research Mode.

## BUG #8 — `_layers()` reads the wrong path; Evidence Ledger never worked (2026-07-21, found live)
`decision_contract._layers()` walks `state.intelligence → layers → intelligence
→ rows`. The rows actually live at `intelligence → decision_matrix → rows`
(`execution_gate.py` reads them correctly). `_layers()` has therefore returned
`{}` on every cycle since it was written.

Silently dead as a result:
- **Evidence Ledger** — all five pillars `None`, `ledger_total` `None`. This is
  the persistent `Evidence /100 —` on the dashboard. Charter **Rule 3**
  ("confidence is evidence — 95% must decompose") has never functioned.
- **Entry Grade** — `layer_breadth` always `None`; grade computed from 2 of 3
  declared inputs.
- **BUY checklist** — `Institutional Flow` and `Volume` permanently ○
  ("not measured") when both were measurable all along.
- **`why` fallback** — could never name the strongest confirming layers, so it
  emitted "No published reason — engine idle" while Trend sat at 90 PASS.

Verified live: 11 rows present, every name the ledger/checklist needs is there.
Post-fix values at the moment of discovery: Evidence 69/100, breadth 7/11 = 64,
Volume ✔ (68), Institutional Flow ✗ with a real 11/20 rather than ○.

Same signature as the other seven: a defensive `.get()` chain that returns `{}`
on a wrong path, never raises, and reads as "no data yet".

FIX DEFERRED to the close pass — found at 11:12 IST with the market open, and a
backend restart would wipe `premium_radar._tracks` (live C6 coil state).
Display-only: it cannot confound C6, which is measured in `opportunity_metrics`.

## BUG #9 — broker health_score: cumulative penalty used as a live gate, and invisible (2026-07-21)
Safe Mode freezes ALL signals when `broker_stats["health_score"] < 40`
(`safe_mode.py:31`). That score (`broker/dhan.py:195`) is:
`100 − min(_total_429*5, 40) − max(util−80,0)*1.5 − 30·cooling − 10·(lat>800)`

`_total_429` is initialised once at class definition and only incremented —
**never reset, never decayed**. After 8 rate-limit hits in the whole process
lifetime it is a permanent −40. One transient cooldown (−30) then puts the
score at 30, below the threshold, and Safe Mode freezes trading. The same
cooldown early in the session would leave it at 70 and freeze nothing.

⇒ The broker trigger becomes progressively more sensitive the longer the
backend runs. Same defect class as the 3-day Kill Switch deadlock already
fixed (cumulative state used as a live gate with no session window).

**Also a display-honesty failure.** The only `health_score` rendered in the UI
is `SystemVerify.tsx`, showing a DIFFERENT same-named metric (the composite
`100% Stable`). The dashboard therefore shows `100% Stable` + `🟢 Broker
connected` + `FEED 🟢 100% healthy` while the one number freezing trading is
displayed nowhere. `state.connected` (a bare boolean) is what the Broker row
reports; broker call-health is never surfaced.

FIX (close pass, needs owner sign-off — it changes a gate, not just a label):
1. Window `_total_429` to the current session/rolling hour so it decays.
2. Surface broker `health_score` in Feed Diagnostics / System Verify, named
   distinctly from the composite score.
Does NOT affect C6: Safe Mode gates signals/execution only; `premium_radar` and
`opportunity_metrics` keep recording (Two-Layer Law).

## LANGUAGE COLLISION — observation layer must never say "BUY" (owner, 2026-07-21)
Owner: the dashboard answers "should I buy?" in several languages at once —
Trade Light `NO TRADE`, Premium Radar `BUY ZONE / Buy Candidate`, Scalping Tool
a full plan (`24200 PE ₹44 · SL ₹26 · T1 ₹94 · 7 lots`), Decision Contract
`No Active Contract`. The 4e893a8 reconciliation covered Trade Light ↔ Decision
Contract ↔ Execution Detail but never included Premium Radar or Scalping Tool.

Partly self-inflicted: implementing the owner's runner bands put the literal
word BUY into the OBSERVATION layer (`85-100 → "Buy Candidate"`, zone
`"BUY ZONE"` at 70+).

**The owner's own Layer-1 spec resolves it** — their MARKET layer reads
"Market Opportunity · Runner ★★★★★ · Growing", with no BUY. Rule adopted:
**the word BUY belongs to the execution layer only.**

Close-pass renames (thresholds 30/50/70/85 unchanged — labels only):
- `BUY ZONE` → `PRIME ZONE`
- runner_band `Buy Candidate` → `Prime Runner`
- Scalping Tool: when the gate is closed, a HEADER saying so — not a trailing
  "· fires only if the gate opens" after the ₹ amounts and lot counts.

### Three-layer target (owner)
1. **MARKET** — observation only, no BUY language.
2. **EXECUTION** — strike · entry · SL · targets · lots. The only BUY.
3. **WHY NOT** — one line. `execution_gate.blocking_reasons[0]` ALREADY exists
   (rendered at page bottom as "ENTRY STATUS: WAIT · missing: …"); the hero
   shows the vague `Confirmation Missing – Wait` instead. Surface it as
   `block_reason` on the contract.

### Universal Opportunity Tracker — splits in two
- **Display half (close pass):** show every tracked move, alertable or not.
- **Detection half (FROZEN):** the `rise_pct < 18` / `< 20` ignition caps that
  made the 40-pt CE move invisible. That is a threshold change to the SAME
  ignition logic C6 is under validation on — changing it now would destroy the
  C6 answer. Deferred until C6 has a verdict; `RISE_CAP_BLOCKED` measurement
  ships first so the change arrives with evidence (Rule C).

# CLOUD AI TRADER V15 — Dual Intelligence Architecture (owner, 2026-07-21, LOCKED)

| # | Layer | Status |
|---|---|---|
| 1 | **Decision AI** (risk brain) — BUY/WAIT/NO TRADE only | EXISTS |
| 2 | **Opportunity AI** — is there a move? | EXISTS (Two-Layer Law) — scattered across 5 panels, needs consolidating |
| 3 | **Forecast AI** — today's expected move | **NEW, unbuilt** (charter Layer 6) — needs normal-session black-box data |
| 4 | **Historical Reality** — observed outcome statistics | SHIPPED 2026-07-21 |
| 5 | **Manual Entry** — premium entry/SL/targets even when refused | SHIPPED (premium_plan) |
| 6 | **Block Analysis** — why the engine said no | exists as blocking_reasons; needs surfacing |
| 7 | **Override** (default OFF) | not built — see doctrine note below |
| 8 | **Trade Review** — per missed move, blocked-by + would-have-reached | needs premium-based shadow scoring first |
| 9 | **Learning AI** — daily auto-written summary | not built |
| 10 | **Adaptive Recommendation** — proposes, never self-modifies | partially exists (`proposal_readiness`, already holding #001 Greeks Softening for want of samples) |

## THE NAMING RULE (owner, 2026-07-21) — now a permanent rule
**The word "Probability" may appear in ONE place only: Forecast AI.**
Everywhere else must use its own honest name:
`Observed Frequency` · `Historical Outcome` · `Forecast Confidence` ·
`Decision Confidence` · `Opportunity Strength`.

Rationale, learned the hard way today: a 3×–50× overstatement survived for
months *because* it wore the word "probability". A number called probability is
trusted as one. Naming is not cosmetic here — it is the control that makes the
error visible.

**Audit outstanding** (labels still saying Probability, to be reclassified):
`Entry Probability` (entry_probability layer) · `Probability` in Scalping Tool ·
`Probability Candle Projection` · `Probability Ladder` · `Reversal Probability`.
Each must be re-labelled as forecast, observation, or confidence — or justified.

## Confidence must split three ways (owner)
One blended number hides which part is weak:
`Forecast Confidence` · `Execution Confidence` · `Historical Support`.

## Doctrine note on Layer 7 (Override)
Showing a blocked opportunity with its reason and its premium plan is
information, and is built. A control that makes the system print "BUY NOW"
while its own gates say no would be the system contradicting its own risk
assessment. The decision already rests with the human — nothing auto-executes —
so the honest form is "blocked · here is what it was worth", not a second BUY.

## SOURCE TAGS — every metric declares where it came from (owner, 2026-07-21) — PERMANENT
Today's lesson generalised: a formula can be wrong, a label can be wrong, but a
measurement must never lie. From here, every number on the dashboard carries a
source tag:

| tag | meaning | example |
|---|---|---|
| 📈 **Forecast** | AI model, forward-looking | Forecast AI (Layer 3, unbuilt) |
| 📊 **Observed** | historical frequency from the black box | outcome_stats(), n=1694 |
| ⚙️ **Decision** | engine rules / gates | BUY/WAIT/NO TRADE, blocking_reasons |
| 🧪 **Estimated** | declared heuristic, not calibrated | runner score, coil strength |

Why it matters: for months a 🧪 Estimated decay curve was displayed as though it
were 📈 Forecast, and nobody could tell by looking. With tags, that mislabelling
is visible on the surface instead of buried three files deep.

**The three that must NEVER blend:** History (Observed) · Forecast · Decision.

## THE PATTERN — ten bugs, one shape (2026-07-21)
Every bug found today produced plausible output and raised no error:
1. `peak_rise` scored declines as runs · 2. `ignite_path` discarded at a
boundary · 3. expiry unrecorded · 4. `UNKNOWN` session defaulted to `NORMAL` ·
5. sampling rule lived only in prose · 6. feed outage scored as detection
failure · 7. `dte` from server-local date · 8. `_layers()` wrong path (Evidence
Ledger dead since written) · 9. non-decaying 429 counter gating Safe Mode ·
10. fabricated decay curve shown as probability — **twice**, in two files.

Nine HID information. #10 MANUFACTURED it, which is worse on a card a trader
acts from. Standing lesson: **when a defect is found, grep for the pattern, not
just the instance** — #10's second copy was missed on the first pass.

# HANDOFF — 4 LOCKED DECISIONS (owner sign-off, 2026-07-21 end of session)

## ORDER OF WORK NEXT SESSION (owner, explicit)
**ORDER (owner, severity-ranked — do NOT bundle):**
1. Case A/B → ship `_total_429`
2a. **Confidence `—` fix** → read `intelligence_synthesis.conviction`
2b. **Verify `context_builder.py:63` separately** — same fix, or different?
    **#2 is NOT done until 2b is traced.** Do not close it on 2a alone.
    Three times on 2026-07-21 two problems that looked identical had different
    causes (Kill Switch daily-reset vs `_total_429` missing-decay; fallback vs
    root-cause on conviction; `state.strike` absent vs assigned-by-test).
    Same pattern is not evidence of same cause — grep each one.
3. Calibration rename + delete duplicate checklist row
4. Trace `premium_accuracy._errors`
5. Watch `calibration_score` move

### #2 Confidence `—` — ROOT CAUSE FOUND, not a fallback
`decision.py::_conviction()` returns a CATEGORICAL grade label
(HIGH/MODERATE/LOW/**NONE**) plus `conviction_label` for display. `'NONE'` is
CORRECT output — there is no upstream bug. The defect is that
`decision_contract.py:116` reads `dec["conviction"]` (the label) while SIX
other consumers — alpha_engine, execution_card, signal_maturity,
execution_gate, brain, market_service — all read
`intelligence_synthesis.conviction` (the NUMBER, live value 74).
Fix = follow the existing convention, not add a fallback:
```python
conviction = (dec.get("intelligence_synthesis") or {}).get("conviction")
```
Effect: hero shows Confidence 74 instead of `—` while the same page already
prints CONVICTION 74 two panels down.
**UNVERIFIED, same shape:** `cortex/context_builder.py:63` also reads
`dec.get("conviction")` — trace before assuming safe.
**Evidence /100 is NOT part of this** — it reads decision-matrix layers
continuously and is correctly independent of trade arming (observation ≠
decision). R:R `—` is also correct: reward_risk is genuinely None with no
active setup.
Rationale: an approved-but-undeployed fix must land before an unrelated
refactor begins, or the context splits and the approved fix slips. Do not
start the naming work with #2 still pending.

## 1. Calibration gate — SETTLED, no action
`institutional` moved 56→61 on real signal strength, so the confluence gate
self-corrects and is NOT deadlocked. A gate that recovers on genuine market
strength must not be patched because of one bad morning. **Do not touch.**

## 2. `_total_429` windowing — APPROVED, test before deploy
Copy the sibling idiom in the SAME function (`_req_times`), NOT the Kill
Switch (see #3 — I recommended that first and was wrong; it is a fixed daily
boundary and would have introduced a midnight cliff).
```python
_429_times: deque = deque(maxlen=500)     # on 429: append(time.monotonic())
recent = [t for t in cls._429_times if now - t < 3600]
score -= min(len(recent) * 5, 40)
```
- maxlen=500 verified safe: the cap saturates at 8 events, so 500 dwarfs it.
- **Keep `_total_429` for display.** `stats()["rate_limit_events"]` is a
  lifetime figure; scoring moves to `_429_times`. Separating DISPLAY HISTORY
  from LIVE HEALTH is the actual lesson, not just the decay.
- **MANDATORY before deploy** (owner): synthetic test, not code review alone —
  `Case A: 8×429 over 2h → score must NOT reach −40`
  `Case B: 8×429 within 1h → score MUST reach −40`

## 3. Kill Switch midnight reset — INTENTIONAL, documented so nobody "fixes" it
`_day0` (IST midnight) resets the consecutive-loss count. This is **correct
design**, not a missing-decay bug: "new trading day, fresh loss count" is valid
risk semantics and aligns with the daily trading rules. **Leave as is.**

**PRINCIPLE (owner, supersedes my framing):** "sliding good, fixed bad" is NOT
a blanket rule. For every gate ask: *is this reset business-meaningful, or
accidental?* `_total_429` had no business reason for its behaviour — a bug.
Kill Switch's daily reset has one — a design decision.

## 4. Two calibration paths — NEXT SESSION, **SECOND** task (after #2 ships)
Three names for two concepts is the root confusion, and I added the third.
| now (colliding) | rename to | meaning |
|---|---|---|
| `confluence.calibration` | `confluence_gate` | point-in-time, 5-check pass/fail |
| `analytics.calibration_score` | unchanged | rolling historical accuracy 0–100 |
| BUY-checklist "Calibration" row | **DELETE** | my duplicate of `confluence_gate` |
They are legitimately independent — record that as an EXPLICIT design decision,
not an implicit gap.

## 5. `premium_accuracy._errors` — UNVERIFIED, trace before assuming safe
The third monotonic counter; I did not trace whether it feeds a score or gate.
Do not carry "probably fine" — `_total_429` looked fine too.
(`_total_requests` is display-only: confirmed harmless.)

---

# V16 MASTER CHARTER — Evidence-Driven Institutional AI Framework
_(owner, 2026-07-21 — governance document, not a build order)_

## PRIME DIRECTIVE (V16)
Never optimise for "more BUY signals." Optimise only for: higher EV · earlier
evidence detection · honest confidence · measured outcomes · **zero fabricated
probability** · **one Decision Engine only**.
The software must never be a signal generator. It is an Evidence Provider.

## THREE PERMANENT LAYERS (order never changes)
- **AI-1 Decision** — the ONLY authority. BUY / WAIT / EXIT / HOLD. No other
  module may emit a BUY.
- **AI-2 Evidence** — runs continuously, never gated, never blocked. Detects
  opportunity BEFORE AI-1 approves. Reports strength, readiness, block reason,
  premium behaviour, strategy agreement, historical context. Never executes.
- **AI-3 Blocked Opportunity** — when AI-1 refuses: "this opportunity exists,
  the engine blocked it because…" with exact reason, missing confirmations and
  the premium plan. **Never hide opportunities. Never promote a blocked
  opportunity into a BUY.**

## STRATEGIES ARE EVIDENCE PROVIDERS, NEVER SIGNALS
Directional · Alpha · Synthetic · Straddle · Strangle · Iron Condor · Iron
Butterfly · Butterfly · Calendar · Gamma · Volatility · Smart Money.
Each outputs ONLY: evidence strength · historical success · alignment · risk ·
entry quality · missing confirmation · blocked reason · suggested premium.
**Never BUY.** Consensus ("6/8 agree") is evidence, never execution.
_(Owner dropped Arbitrage and Market Maker after the data-honesty objection —
neither is buildable on a retail feed without fabricating certainty.)_

## ENGINE INDEPENDENCE — measure, never assume
Agreement is not strength. Low correlation ⇒ raise confidence; high
correlation ⇒ reduce it. Requires `_engine_snapshot()` (bug #11) working.

## NAMING (enforces the 2026-07-21 rule)
"Probability" may appear ONLY in Forecast AI. Everywhere else:
**Observed Historical Frequency** — labelled *Historical Observation, NOT
Prediction*. Forecast AI must label output *Forecast — Not Guaranteed*.

## MEASUREMENT RULE
Measured · Verified · Evidence logged · Outcome logged · Historical comparison
— all five BEFORE a feature may affect Decision AI. **No Measurement, No Decision.**

## ⚠ CHARTER RULES CURRENTLY VIOLATED BY LIVE CODE (gaps, not compliance)
Recording these as OPEN so V16 is not filed as satisfied when it isn't:
1. **"Never use Probability outside Forecast AI"** — 5 live violations remain:
   `Entry Probability`, Scalping Tool `Probability`, `Probability Candle
   Projection`, `Probability Ladder`, `Reversal Probability`. Each must be
   reclassified AND checked against outcomes (a label alone proves nothing —
   that is exactly how the 3×–50× overstatement survived).
2. **"Never hide opportunities"** — the ignition caps (`rise_pct < 18` path-1,
   `< 20` path-2, coil memory erased ≥20%) structurally hide fast movers; this
   is why a +40pt CE move was never alerted. Frozen until C6 has a verdict,
   because it is the same logic C6 is being validated on.
3. **"Forecast AI uses Machine Learning"** — no ML exists in this codebase.
   Forecast AI is unbuilt (charter Layer 6) and needs normal-session black-box
   data first. Do not let the charter imply a capability that is absent.

## V16 REFINEMENT (owner, 2026-07-21 — supersedes/extends the V16 entry above)

**Rule 1 — Evidence First (formalises the source-tag principle).** Every
displayed value must come from exactly one of: Live Market Data · Historical
Database · Statistical Measurement · Forecast AI (labelled) · Decision Engine.
**Nothing may be guessed.** This is the rule the fabricated decay curve broke.

**Rule 3 — Detection never stops.** Radar, detection, learning, logging and
research continue through Kill Switch, Safe Mode, calibration failure, WAIT and
broker pause. **Only EXECUTION may stop.**

**Consensus must show its own independence.** Not just "8/10 agree" but
`Engine Independence 73% · Shared Inputs 31%`. Correlated engines must not
inflate confidence.

**Forecast AI mandatory labels:** Forecast Confidence · Horizon · Training
Samples · Model Version · Confidence Interval. It may never overwrite the
Decision Engine.

**Dashboard layout:** TOP = Decision (AI-1) · CENTER = Opportunity (AI-2) ·
RIGHT = Blocked Reason (AI-3) · BOTTOM = Evidence Providers, Forecast,
Observed Statistics, Validation, Research, Learning.

### ⚠ ADDITIONAL VIOLATION (new in this refinement)
4. **Forecast AI's mandatory labels imply a trained model that does not exist.**
   "Training Samples / Model Version / Confidence Interval" describe an ML
   artefact; there is no ML, no training pipeline and no model in this
   codebase. Forecast AI is unbuilt (charter Layer 6) and blocked on
   normal-session black-box data. Emitting those fields before a model exists
   would be Rule 1's own failure mode — a displayed value that is guessed.

### Precision on violation #2 (rise caps)
Rule 3 says detection never stops. The radar *tracking* genuinely never stops —
it holds all 18 strikes through every gate. What stops is **alerting**: the
ignition caps (`rise_pct < 18` / `< 20`) prevent an alert once a move is
already large, which is why a +40pt CE move showed on the radar but never fired
an alert. So Rule 3 is satisfied for tracking and violated for alerting. That
distinction matters — the fix is to the alert path, not the tracker.

---

# ★ V16 MASTER SPECIFICATION — CANONICAL
_(owner, 2026-07-21 — consolidates and SUPERSEDES the two V16 entries above.
Read this one.)_

## THE EIGHT GOLDEN RULES
1. No fabricated numbers.
2. No hidden opportunities.
3. No strategy decides trades.
4. **No probability without ML.**
5. No duplicated evidence.
6. No engine counted twice.
7. Every displayed value must have a measurable source.
8. **Evidence first · Decision second · Execution last.**

## THREE AIs
- **AI-1 Decision** — the only engine that may approve a trade.
- **AI-2 Opportunity** — never decides, never blocks, never executes. Asks
  "what opportunity exists?", never "should we buy?".
- **AI-3 Explanation** — when AI-1 refuses, explains why. Never hides the
  opportunity, never promotes it.

## STRATEGIES = EVIDENCE PROVIDERS
~35 named strategies (directional, synthetic, spreads, volatility, structure,
flow). Each outputs ONLY: strength · evidence · historical match · pattern
confidence · risk notes. **Never BUY.**

## CONSENSUS IS WEIGHTED BY INDEPENDENCE
Correlation is measured BEFORE consensus is used. Highly correlated engines
cannot be counted twice; consensus is weighted by independence, not by vote
count. Consensus never approves a trade — AI-1 consumes it as one input.

## LEGAL EVIDENCE SOURCES (Rule 7)
Live Market · Database · Historical Episodes · Research Mode · Machine
Learning. Anything else MUST display **Unknown / Unavailable / Not Enough
Data**. Never fabricate.

## VALIDATION BEFORE DISPLAY
Every engine must carry: evidence · accuracy · false-alert rate · hit rate ·
observed statistics · last validation · sample count · confidence.
**Nothing may display unless validated.**

## RESEARCH MODE (already shipped 2026-07-21)
Must never write the production database, modify the checkpoint, or pollute
learning. Isolated storage only. → `CAT_RESEARCH_MODE=1` / `CAT_DATA_DIR`.

## STATUS OF THE FOUR RECORDED VIOLATIONS
1. **Five surviving "Probability" labels** — ⚠ STILL OPEN. `Entry Probability`,
   Scalping Tool `Probability`, `Probability Candle Projection`, `Probability
   Ladder`, `Reversal Probability`. Reclassify AND check against outcomes.
2. **Rise caps suppress ALERTING** (not tracking) — ⚠ STILL OPEN, frozen until
   C6 has a verdict; it is the same logic C6 is validating. Fix belongs to the
   alert path, not the tracker.
3. **"Forecast AI uses ML" implied a capability that is absent** — ✅ RESOLVED
   by Golden Rule 4: probability is now conditioned on ML existing, so
   Forecast AI simply stays unbuilt until it does. Rule and reality now agree.
4. **Forecast mandatory labels implied a trained model** — ✅ RESOLVED, same rule.

---

# ★ FINAL MASTER ROADMAP (owner, 2026-07-22) — 4 phases, 7 locked principles

## SEVEN GOLDEN PRINCIPLES (locked)
1. **One Decision Engine** — BUY/WAIT/EXIT issued in exactly one place.
2. **Many Evidence Engines** — strategies supply evidence only.
3. **No strategy may issue BUY** — Strategy ≠ Signal.
4. **Probability only in Forecast AI** — elsewhere: Observed Statistics ·
   Evidence Strength · Decision Confidence.
5. **No Measurement → No Promotion** — a new engine may not join the decision
   system until it has demonstrated positive EV.
6. **Engine Independence** — the same data must not be counted twice under
   different engine names.
7. **Evidence First → Decision Second → Execution Last.**

## PHASE 1 — Measurement & Validation *(BLOCKS all of Phase 2)*
⚠ The owner's draft marked these ✅. **None is complete.** Recorded truthfully
so the next session does not inherit a false done-state:

| item | real status |
|---|---|
| `_engine_snapshot()` live verification | ⏳ code live (`aabec53` via `6f71e10`), **UNVERIFIED** — needs a live payload at 09:15 |
| Engine Independence data collection | ❌ **not started** — 0 of 2363 episodes carry layer context; only begins if the above works |
| Existing 56-engine validation | ❌ not started |
| Safe Mode / Kill Switch validation | ◐ **partial** — `verdicts` has 600 settled shadow trades with gate efficiency MEASURED, but scored in **INDEX points**, the wrong instrument for an option buyer. Distorts saved/missed in both directions (gamma understates misses; theta understates saves). Needs premium-based re-scoring. |
| Premium Accuracy validation | ❌ `premium_accuracy._errors` **still untraced** — do not assume safe |
| Evidence Ledger stabilization | ◐ `_layers()` path fixed and verified against a captured payload; **not yet confirmed on a live session** |

**Only two things were genuinely completed in this window:** the `_total_429`
sliding window (5/5 acceptance, `54d1fe7`) and the Gemini floating-alias fix
(`6f71e10`). Both were unplanned; neither is a Phase-1 item.

## PHASE 2 — Strategy Intelligence Layer
Alpha · Synthetic · Gamma · Trend · Momentum · Volatility · Straddle ·
Strangle · Breakout · Range. Each outputs evidence strength · historical
outcome · readiness · block reason. **Never a BUY.** Gated on Phase 1.

## PHASE 3 — Decision Intelligence
AI-1 alone consumes all evidence and emits exactly one of BUY / WAIT / HOLD / EXIT.

## PHASE 4 — Forecast AI *(the only ML component)*
Requires: thousands of validated sessions · Engine Independence Matrix ·
strategy-wise outcomes · model versioning · confidence calibration.
Until all exist, Forecast AI stays unbuilt and Principle 4 keeps the word
"probability" out of the rest of the system.

## DSRI — Dynamic Support & Resistance Intelligence (owner, 2026-07-22) — SPEC'D, PHASE 2, DEFERRED
An always-visible S/R side panel: R1–R5 / LIVE / S1–S5, each with a strength
score, evidence count, and — the genuinely new part — **historical touch/reject
stats** (reject %, touch count, last tested, average move). Correctly framed as
an Evidence Engine: emits evidence only, never BUY/SELL; feeds AI-1.

**8 of its 10 layers already exist** — do NOT rebuild them:
structure (swing/BOS/CHOCH) · volume_profile (HVN/LVN) · index_analytics
(OI/max-pain/gamma-wall) · technicals (VWAP) · market_context.institutional_
levels (prev day/week) · institutional_scores (which ALREADY fuses them at
:133 — `resistance = struct.resistance or prev_day_high`). So DSRI is ONE
aggregator + ONE panel, not a new engine stack.

**Why it is DEFERRED (not rejected):**
- It is a Phase-2 evidence engine; the Final Master Roadmap (locked minutes
  earlier) makes Phase 1 block all of Phase 2. Building it now would be the
  first breach of a charter still being written.
- Its headline feature — `Historical Reject 84% · Touch 27` — CANNOT be built
  honestly today: that history lives in the black box, which recorded ZERO
  layer context until `_engine_snapshot()` was fixed this morning
  (`aabec53`, verifying now). Emitting those numbers before the data exists
  would break Golden Rule 1 (no fabricated numbers) — the exact failure of the
  Point-Capture curve.

**Correct order:** Phase 1 completes → black box accumulates level-touch
history → THEN DSRI's aggregator + panel, with real reject-rates. The static
levels (R/S with evidence count, no history) could ship earlier as a pure
display of existing fused levels; the historical strength scores must wait for
data. Do not ship the two together, or the honest half lends false authority
to the fabricated half.

## Violation-list update (owner audit, 2026-07-22, live session)
Owner's live audit confirmed a 6th surviving "Probability" label, verified by grep:
- **`runner_probability`** → rendered "Runner Prob 65%" in EntryFirstDeck.tsx:137
  and ScalpingTool.tsx:197, with a % sign, on a score whose OWN disclaimer says
  "not a calibrated probability". Golden-Rule-4 violation.
  **Fix (owner's wording):** rename to **"Radar continuation score"** — no %,
  no "probability". Backend field `expansion.runner_probability` stays; only the
  DISPLAY label changes (frontend-only, safe mid-session).

Owner's live-session audit score: 8.5/10. Direction engine 9, Premium Radar 9,
Risk Gate 10, Data Safety 10, Probability Calibration 6, UI clarity 7.
Confirmed the two-brain behaviour is working, NOT conflicting: WAIT (decision)
alongside IGNITING (radar) is the Two-Layer Law behaving correctly. The gap is
UI legibility, not logic.

## V7 vision (owner) — the Trigger Ladder / Radar→Decision bridge
Owner wants the Radar→Decision transition made EXPLICIT as a visible ladder:
  OBSERVE → EARLY WARNING → RADAR ACTIVE → STRUCTURE CONFIRM → ENGINE READY → BUY
so a strike shows WHERE it is on the path and exactly which condition flips
WAIT→READY. This is the same need as work-order #3 (block-reason-in-hero) seen
from the opportunity side: #3 answers "why not now", the Trigger Ladder answers
"what would make it yes". Build them together — one shows the missing
confirmations, the other shows the path to arming. Phase-2 UI work; gated on
Phase 1, but low-risk and high-clarity.

## RENAME: Kill Switch → Execution Lock (owner, 2026-07-22) — HIGH VALUE, spec'd
Owner's own best insight, correcting their own premise: the recurring belief
that "Kill Switch freezes analysis" is FALSE (proven: 155 episodes recorded
today while Kill Switch active all day; premium_radar.py has zero kill_switch
references). The architecture already does what V18 asks — analysis/radar/black
box run through the gate; only execution locks. The problem is the NAME, not the
behaviour: "Kill Switch" + "SIGNALS FROZEN" reads like a total halt.
Same pattern as every 2026-07-21 bug: correct logic, misleading label.

FIX (display-only, ~22 files — do carefully with full build+verify, NOT rushed):
- "Kill Switch" → "Execution Lock" everywhere user-facing (keep the internal
  module name kill_switch.py if churn is risky; rename the LABELS).
- Banner "SIGNALS FROZEN (WAIT)" → "EXECUTION LOCKED · radar & analysis live".
- Safe Mode banner likewise: make clear only execution halts.
This resolves the owner's most-repeated confusion by making the screen state
what is already true. NOT an architecture change — a labelling fix.

Note: the rest of V18 (Point Detector / Strategy Detector / S&R side panel /
Replay Engine) is the same Point-Capture vision already recorded in V16/V17;
stable, gated on Phase 1. Institution Replay Engine is the one genuinely new
buildable idea (replay.py + black box exist; needs the engine.layers data that
only began recording 2026-07-22).

## IDSR enrichment of DSRI (owner, 2026-07-22) — two genuinely new pieces
The owner's Institutional Dynamic S/R spec is mostly the DSRI already recorded
(see DSRI entry). TWO parts are genuinely new and worth keeping:

1. **Multi-SOURCE, not single-method** (owner's key insight): a candle-only OR
   premium-only S/R fails in option markets. Fuse with declared weights —
   Spot 40% · Option-chain OI/gamma 25% · Premium structure 20% · Candle
   confirm 10% · Institutional 5%. institutional_scores.py already fuses
   struct+levels; this is the weighted, multi-source version.
2. **PREMIUM support/resistance** — S/R computed on the OPTION PREMIUM series
   itself (premium swing / premium-VWAP / premium-ATR), not just the index.
   BUILDABLE NOW from existing data: premium_radar already keeps a per-strike
   premium series (deque of premium/vol/oi). This is the piece an option buyer
   actually enters on. Good early Phase-2 candidate.

Plus the owner's ENTRY rule, which aligns with the charter: a level touch ALONE
must never trigger — require confluence (touch + candle + volume + OI + premium
bounce + smart-money) or it's WAIT with the missing confirmation named. This is
Rule 2 ("every BUY earns its right") applied to S/R.

**Naming check — owner got it right:** their bounce-% draft was labelled
"Observed Historical Behaviour, NOT Probability." Golden Rule 4 holding
voluntarily now, which is the point of writing it down.

Status: all Phase 2, gated on Phase 1 (started 2026-07-22). Premium-S/R is the
one buildable-today slice once the block-reason/rename UI work clears.
