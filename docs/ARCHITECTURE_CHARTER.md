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
