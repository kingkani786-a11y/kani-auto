# CLOUD AI TRADER X — MASTER ARCHITECTURE AUDIT
**Date:** 2026-08-07 · **Scope:** Full backend (`backend/app/engines/*.py` — 61 files, `backend/app/services/*.py` — 46 files, broker + API wiring) · **Method:** Direct code read + grep, zero fabrication — every claim below traces to a file/line. No code was written or modified to produce this report. No thresholds were changed.

**Scoping note on the 13-field template you specified (Status/Purpose/Strength/Weakness/Missing Data/Missing Logic/Required APIs/Required Historical/Required Live/Priority/Dependency/Risk/Expected Benefit):** applying all 13 fields to every one of 107 files would produce ~1,400 mostly-repetitive entries (a TTL cache and a directional evidence engine don't need the same depth). Full profiles are given for the ~35 modules that actually participate in the BUY CALL / BUY PUT / NO TRADE decision or its explanation. Support/infrastructure modules (caches, journals, alert dispatch) get a lighter table — purpose, status, wiring, and a priority note only — with that scoping stated so nothing is silently skipped.

---

## 0. How the system actually decides today (ground truth, not aspiration)

Three loops in `market_service.py` are the entire live system:

- **`_spot_tick()` (~3s)** — LTP, depth, lifecycle price updates, `market_event.on_tick()`, memory outcome updates, paper mark-to-market, audit tick tracking.
- **`_option_tick()` (~15s)** — full option chain fetch → `index_analytics.analyze_chain()` (PCR/OI/max-pain/Greeks) → `smart_money.analyze_option_flow()` → `move_detector.scan()` → `premium_radar.scan()` → `anomaly.observe()`.
- **`_ai_cycle()` (~180s)** — 1-min candles → **`confluence.run()`** (the actual directional synthesis) → ~30 more derivation-only engines bolted on sequentially, each independently `try/except`-wrapped → publish to `state.decision`/`state.signal`/`state.intelligence` → websocket broadcast.

`confluence.run()` returns `(ts, signal, layers, strike, strikes, warning, narrative, coach, risk)`. Its `layers` dict literally contains (in assembly order): `trend, structure, oi, smart_money, greeks, volume_profile, mtf, expiry, market_profile, regime, _instrument_mode, probability, order_flow, candles, _tech, session, vix_correlation, gift_correlation, global_context, market_strength, entry_probability, institutional_activity, institutional_levels, capital_protection, no_trade_zone, traps, global_feed, evidence_rank, structural_targets, trade_quality, future_path, futures, decision_explainer, intelligence, future, risk`.

Only **7 of these are in the scored composite**: `trend(.16) · structure(.16) · oi(.16) · mtf(.16) · smart_money(.12) · greeks(.12) · volume_profile(.12)`. `MANDATORY = (trend, structure, mtf, oi)`. `MIN_CONFIRMING_LAYERS = 5 of 7`. `CONFIRM_LEVEL = 55.0`. Everything else in the list is observational, a veto, or an explanation layer — not part of the score. This matters for your PRIMARY OBJECTIVE section below: the system already separates "what scores" from "what explains," which is the correct shape — it just isn't fully populated yet (see §3 Missing Evidence Layers).

`decision_contract.py` (the Trade Explorer's actual data source) is **on-demand only** — rebuilt fresh on every `GET /api/decision-contract` from whatever `_ai_cycle` last published. It re-checks `execution_gate`'s verdict against `decision.primary_action` a third time at read time (its own comment: "Rule 1 — fail to WAIT, never to a broken card").

**Confirmed already compliant with your stated rules**, with code-path proof (§7 below):
- **Rule 6 (Live Analysis must never stop):** Kill Switch (`kill_switch.py`) is a pure function. Traced every consumer — it only appends veto strings inside `confluence.py`'s `vetoes` list and `execution_gate.py`'s `blocking_reasons`. It is never referenced in `_spot_tick()` or `_option_tick()` at all (zero grep hits). Data collection, option-chain fetch, Greeks, memory, anomaly detection, premium radar, and dashboard broadcast all run unconditionally regardless of kill-switch state — the kill switch's own state is itself broadcast every cycle, proving broadcast isn't suppressed by it.
- **Rules 3/4 (no self-modifying AI, AI learns but doesn't change live logic):** searched the entire codebase for any auto-threshold/auto-weight/auto-gate path. Found none. `weight_approval.py` is the one mechanism that exists for weight changes, and it's explicitly `QUEUE → APPROVE → SIMULATE → APPLY`, human-gated at every step; `confluence.py` defaults to all-1.0 multipliers unless a human has walked a change through that full pipeline. `memory.py`'s `engine_reliability()` weight field is explicitly commented "advisory; not auto-applied to the gate." `evolution.py`'s "upgrade list" is explicitly "never auto-applied to the live trading gate."

---

## 1. CORE DECISION PIPELINE

### `services/market_service.py`
- **Status:** Live, central orchestrator, working.
- **Purpose:** Owns all three background loops; the only writer to `state.*`.
- **Strength:** Each of the ~30 engines bolted onto `_ai_cycle` is independently try/except-wrapped — one engine failing cannot break the cycle. This is a real, working resilience pattern.
- **Weakness:** `_ai_cycle` has grown to ~30 sequential engine calls in one function; no engine-level circuit breaker or per-engine timing budget exists, so a single slow engine silently lengthens the whole 180s cycle.
- **Missing Data/Logic:** No per-engine execution-time telemetry (which of the 30 engines is slow, which fails most often) — `research_lab.py` gives system-level health, not per-engine-in-cycle timing.
- **Priority:** Medium (stability, not decision quality).
- **Dependency:** Everything downstream depends on this.
- **Risk:** Low today (proven stable), but the un-budgeted engine count is a scaling risk as more layers are added.
- **Expected Benefit of fixing:** Faster diagnosis of "why did this cycle take 4 minutes."

### `engines/confluence.py`
- **Status:** Live, working, the actual decision synthesizer.
- **Purpose:** Assembles all directional layers into one scored composite + narrative.
- **Strength:** Clean separation of MANDATORY vs scored vs observational layers; `MIN_CONFIRMING_LAYERS` requires broad agreement, not one strong layer overriding everything.
- **Weakness:** Docstring claims "ten layers"; literal weighted set is 7. Not a functional bug (confirmed via evidence_rank.py's own byte-identical test) but a documentation/expectation mismatch worth fixing so nobody designs against a wrong mental model.
- **Missing Data:** VIX/GIFT correlation only apply a ±3 confidence nudge by explicit design (`global_feed.py` docstring: "NEVER a hard gate") — correct by design, but means macro backdrop is currently the weakest-weighted evidence class.
- **Priority:** High (it's the core; any evidence-layer work routes through here).
- **Dependency:** Everything in §2/§3 feeds this.
- **Risk:** Medium — it's the single point where a new layer could be wired in wrong (this session's own evidence_rank.py build used a byte-identical-packet test specifically to guard against this).
- **Expected Benefit:** Fixing the docstring costs nothing; it's listed for completeness/honesty, matching your rule against fabricated claims about the system's own state.

### `engines/decision.py`, `services/decision_intelligence.py`, `engines/execution_gate.py`, `services/decision_contract.py`
- **Status:** All four live, all four working, but they form a **triple-gate chain**: `decision.py` builds the trader-simple fields → `execution_gate.py` runs a second, stricter institutional checkpoint → `decision_contract.py` re-checks `execution_gate`'s verdict against `decision.primary_action` a **third** time, at read time, and downgrades to WAIT on any disagreement.
- **Strength:** Fail-safe by construction — three independent chances to catch a bad ENTER, and the final one (`decision_contract.py`) explicitly degrades to a hardcoded honest-WAIT card on any internal exception, never a broken UI.
- **Weakness:** Three sequential re-derivations of "should this trade go" is real complexity — a future contributor could patch one gate's logic and not realize two others also need the same fix. No single "the gate" function exists; there are three.
- **Missing Logic:** No single test currently proves all three gates agree on the same set of inputs (the kind of byte-identical-packet regression test this session used for evidence_rank.py doesn't exist for gate-agreement).
- **Priority:** Medium-high — not urgent (it currently works and fails safe), but a genuine architectural fragility for anyone modifying gate logic later.
- **Dependency:** `execution_gate.py` depends on `confluence.py`'s full layer output; `decision_contract.py` depends on both.
- **Risk:** Medium — divergence between the three gates would currently manifest as an over-cautious WAIT (safe direction), not a false ENTER, because `decision_contract.py`'s tie-break rule is "disagreement → WAIT." So the risk is silently missed entries, not bad entries.
- **Expected Benefit of consolidating:** One authoritative gate function, called three times for defense-in-depth, instead of three independently-written gate implementations — reduces the chance a future edit fixes one and misses the other two.

### `engines/lifecycle.py`, `engines/quality.py`
- **Status:** Live, working.
- **Purpose:** Lifecycle = signal state machine (SETUP→WATCH→ARMED→TRIGGERED→ENTRY→TARGET→EXIT); Quality = A/B/C/D grading, "<60% enforced NO TRADE upstream."
- **Priority:** Low (stable, no gaps found).

---

## 2. DIRECTIONAL EVIDENCE ENGINES (the 7 scored layers + the 2 recent additions)

| Module | Purpose | Strength | Weakness / Missing | Priority |
|---|---|---|---|---|
| `technicals.py` (`trend` layer) | EMA/VWAP/ATR/ADX/momentum + `trend_engine` (EMA20/50/200 stack + VWAP + ADX) | Simple, auditable, no black-box math | No Supertrend anywhere in the codebase — you explicitly listed it as a wanted evidence layer; it is **fully absent**, not partial | High if you want it — genuinely missing |
| `structure.py` (`structure` layer) | Swing pivots, HH/HL/LH/LL, **BOS/CHOCH**, liquidity zones/stop-hunt, Auto Fib + Golden Zone (0.618–0.65), Auto Trendline | Already does BOS/CHOCH AND a live Fibonacci Golden Zone — more built here than the audit request assumed was missing | Auto Fib here is a **different, already-live** implementation from ORFE's research-only Fib (built last session) — the two are not reconciled or cross-validated against each other yet | Medium — reconcile, don't rebuild |
| `index_analytics.py` (`oi` layer, PCR/max-pain) | PCR, Max Pain, OI structure, ATM Greeks from the raw chain | Correct, live, mandatory layer | No OI-velocity/acceleration tracking (only level + change, not rate-of-change) | Low-medium |
| `smart_money.py` (mandatory-adjacent) | LONG/SHORT buildup, covering/unwinding classification from price+OI deltas; also does liquidity-sweep/false-breakout tape reading | This IS your "Buyer/Seller Analysis" + part of "Institutional Buying/Selling" — already live | No dedicated large-order/block-trade detection (Dhan doesn't expose that data at all — an honest external limit, not a code gap) | Low (limited by data availability) |
| `greeks.py` | Black-Scholes Greeks + IV, no scipy dependency | Self-contained, no external math library risk | Doesn't do Greeks *rate-of-change* (Gamma/Vega changing across ticks) — only a point-in-time snapshot | Low-medium |
| `volume_profile.py` | POC/VAH/VAL, acceptance/rejection | Standard, working | 5-min candle resolution only; no session-anchored VWAP bands beyond the base VWAP | Low |
| `mtf.py` (mandatory) | 1/3/5/15/30/60m resample + trend agreement | Mandatory layer, working | `mtf_confluence.py` (a second, richer 7-TF engine) exists in parallel and is explicitly display-only, never touching this gate — two MTF engines, one authoritative, one cosmetic; worth being deliberate that this stays that way | Low — already correctly separated |
| `candles.py` | Engulfing/pin/inside-bar/exhaustion pattern detection | Built this session with `THRESHOLD_REGISTRY`, explicitly non-rankable (can't become PRIMARY evidence, only supporting/contradicting) | Observational only by design — never in `WEIGHTS`, never a veto. This is correct given it has no comparable 0-100 score, not a gap | None — working as designed |
| `orderflow.py` | Order-flow proxies from candle anatomy | Works without true tick-by-tick order book data (Dhan doesn't provide it) | Explicitly a **proxy**, not real order flow — an honest, declared limitation, not a hidden one | Low (data-limited) |

**Missing from this category:** **Supertrend** — you named it explicitly; it does not exist anywhere in this codebase. It would be a straightforward, self-contained addition (ATR-based, same shape as `regime.py`'s ATR usage) if wanted.

---

## 3. INSTITUTIONAL / OPTIONS-SPECIFIC ENGINES

| Module | Status | Purpose | Wiring | Note |
|---|---|---|---|---|
| `expiry.py` | Live | Gamma Wall (OI-concentration proxy), max-pain shift, OI migration, pinning, squeeze | `confluence.py` layer (chain-gated) | This IS your "Gamma" evidence layer |
| `gamma_shield.py` | Live | Reads `expiry.py`'s gamma wall + DTE + squeeze phases, recommends WAIT near gamma spikes | Called directly from `_ai_cycle`, **not through `confluence.py`** | Structural note: since it's outside the `layers{}` dict, `evidence_rank.py` never sees or ranks this evidence — it acts as an independent side-channel veto. Worth a deliberate decision on whether it should be visible to evidence ranking too |
| `institutional_scores.py` | Live | `institutional_activity` (own docstring: "DERIVED proxy from smart-money OI flow + order flow, labeled as such"), plus `market_strength`, `entry_probability`, `trade_quality` | `confluence.py` layers | Honestly labeled derived/proxy — good practice already followed |
| `strike_selector.py` | Live | Scores every visible strike on delta band/OI/volume/spread/ATM distance | `confluence.py` | Working, no gaps found |
| `premium_radar.py` | Live | ATM±N live premium tracking, Runner Score, lifecycle stage | `_option_tick` | The engine behind this session's late-catch investigation; Step 1 diagnostic instrumentation shipped, Step 2 (behavior change) still pending real-data evidence |
| `premium_forecast.py` | Live | Projects premium 15/30/60/90 min out | `_ai_cycle` | No accuracy-tracking cross-check against `premium_accuracy.py` documented in one place — two related measurement modules, worth a single combined view |

**Missing:** No **dedicated Buyer/Seller Strength module** distinct from `smart_money.py`+`institutional_scores.py` — but per the audit, those two together already cover it. This is a naming/consolidation question, not a functional gap.

---

## 4. RISK / SAFETY / GOVERNANCE

| Module | Status | What it actually gates (code-proven) |
|---|---|---|
| `kill_switch.py` | Live | Execution/signal ONLY — see §0 proof. Never blocks data, analysis, or dashboard. |
| `capital_protection.py` | Live | Theta bleed/IV-crush/premium-decay → hard veto at CRITICAL, inside `confluence.py` |
| `guards.py` | Live | No-Trade-Zone + Trap Detection; trap ≥55% confidence is a hard veto |
| `safe_mode.py` | Live | Infrastructure disaster recovery (broker/API/feed/websocket collapse) — can force `is_trade=False` |
| `risk.py` | Live | Qualifies signal, warns on hostile conditions |
| `risk_approval.py` | Live (read path) | Read-only approval checklist computed fresh on every `GET /api/decision-contract`; explicitly marks News as `UNKNOWN — no news feed connected` rather than faking a value |
| `data_quality.py` | Live | Per-stream freshness — feeds the safety gate |
| `state_consistency.py` | On-demand | Read-only A-vs-B data-quality disagreement detector (this session's OBS-12 subject) |

**Assessment:** this category is genuinely mature — every module here is explicit about what it does and doesn't cover, and the "never faked, marked UNKNOWN instead" pattern (`risk_approval.py`'s News check) is exactly the discipline your rules ask for. No urgent gaps found here; the only real gap is the News feed itself (§6).

---

## 5. EVIDENCE SYNTHESIS / EXPLANATION LAYER (this is what Trade Explorer reads)

| Module | Role |
|---|---|
| `evidence_rank.py` | PRIMARY/CONFIRMING/CONTRADICTORY/INSUFFICIENT classification over the same layer scores confluence already computed — **this IS your "Contradiction Engine."** Confirmed via grep: no second, separate contradiction module exists anywhere. |
| `future.py` | Scenario simulation, next-move probability, time-to-event, Buyer-vs-Seller War Room |
| `futures.py` | Futures confirmation-only read, never overrides |
| `narrator.py` | Tamil+English commentary |
| `intelligence.py` | Market Animal, Expansion/Runner state, Decision Clarity, Data Confidence, Failure Patterns |
| `confidence_explainer.py` | Decomposes composite confidence into per-engine contribution — this is the closest existing thing to "which evidence supports/contradicts, and how much" |
| `entry_checklist.py`, `entry_zone.py`, `entry_score_timeline.py`, `signal_maturity.py` | Confirmation checklist, entry-timing classification (BEST/GOOD/LATE/AVOID), fire-score trend, setup maturity |
| `execution_card.py` | One composed actionable instruction |
| `probability.py`, `probability_ladder.py` | POS from edge+IV/ATR (declared, explicitly not backtested — that's `analytics.py`'s separate job), P(reach T1/T2/T3) |
| `options_professor.py` | Plain-language trade explanations |

**Assessment against your "Trade Explorer must explain" list:** Why BUY CALL/PUT — covered (`narrator.py`, `options_professor.py`). Supporting/contradicting evidence — covered (`evidence_rank.py`). Confidence — covered. Probability — covered (`probability.py`, `probability_ladder.py`, all explicitly declared-not-backtested). Historical Match — covered (`market_dna.py`, §6). Risk — covered. Invalidation — covered (`decision_contract.py`'s `invalidations` field). Targets — covered (ATR-based; `structural_targets` from S/R exists as a parallel *observational* comparison, not yet feeding the actual target). Expected Drawdown — **partially covered**: `opportunity_metrics.py` measures MAE/MFE historically, but no live per-signal "expected drawdown" projection exists yet the way `premium_forecast.py` projects premium. Expected Holding Time — **not found as a distinct field** anywhere; closest is `market_clock.py`'s session-phase map, which is context, not a holding-time estimate.

---

## 6. MISSING EVIDENCE LAYERS — your exact checklist, verdict per item

| Item | Verdict | Where (if present) |
|---|---|---|
| Opening Range | ⚠ Research-only | `orfe_research.py` (isolated, Phase 0, not live) |
| VWAP | ✅ Live | `technicals.py`, `market_context.py` |
| EMA Alignment | ✅ Live | `technicals.py` trend_engine |
| **Supertrend** | ❌ **Missing entirely** | Not found anywhere in the codebase |
| Price Action | ✅ Live | `candles.py`, `orderflow.py` |
| Swing Structure | ✅ Live | `structure.py` |
| Break of Structure | ✅ Live | `structure.py` |
| CHOCH | ✅ Live | `structure.py` |
| Liquidity Sweep | ✅ Live | `structure.py`, `smart_money.py` |
| Support/Resistance | ✅ Live | `support_resistance.py` |
| Fibonacci | ✅ Live (structure.py) + ⚠ Research (ORFE) — **two separate implementations, not reconciled** | `structure.py` Auto Fib/Golden Zone; `orfe_research.py` |
| Institutional Buying/Selling | ✅ Live | `smart_money.py`, `institutional_scores.py` |
| Gamma | ✅ Live | `expiry.py`, `gamma_shield.py` |
| OI | ✅ Live | `index_analytics.py` |
| PCR | ✅ Live | `index_analytics.py` |
| Delta | ✅ Live | `greeks.py`, `strike_selector.py` |
| Volume | ✅ Live | `volume_profile.py`, `orderflow.py` |
| **News** | ❌ **Missing entirely** | Zero ingestion anywhere; `risk_approval.py` explicitly marks it `UNKNOWN` rather than faking it |
| Macro Events | ⚠ Partial | `global_context.py`/`global_feed.py` cover VIX/GIFT only (±3 confidence, by design never a hard gate) — no economic calendar (RBI policy, Budget Day, US Fed) beyond a manually-declared `session_calendar.json` |
| Gap Analysis | ⚠ Scattered, no dedicated engine | Logic spread across `global_context.py`, `global_feed.py`, `historical_learning.py` |
| Trend Strength | ✅ Live | `regime.py`, `technicals.py` ADX |
| Volatility Regime | ✅ Live | `regime.py` |
| Market Regime | ✅ Live | `regime.py` (single source of truth, fan-out reads by many others) |
| Expiry Behaviour | ✅ Live | `expiry.py` |
| **Auction Behaviour** | ❌ **Missing** — directly relevant to last conversation's NSE Closing Auction Session (CAS) finding | `market_profile.py` covers Initial Balance/day-type, not the closing auction specifically |
| **Closing Session Behaviour** | ⚠ Label only, no logic | `market_context.py` tags the session phase as `CLOSING_SESSION` — no CAS-specific reference-price/band modeling |
| Market Psychology | ⚠ Descriptive only | `narrator.py`/`intelligence.py` (Market Animal) describe mood, don't model it as a distinct scored layer |
| Historical Similarity | ✅ Live | `market_dna.py` |

**Net new evidence layers genuinely absent:** Supertrend, News, a dedicated Gap Analysis engine, Auction/Closing-Session Behaviour (the CAS engine from last conversation), and a real Macro Events calendar. Everything else on your list already exists in some form — the gap is narrower than the full checklist suggests.

---

## 7. MEASUREMENT / LEARNING LAYER (never gates — confirmed)

`memory.py`, `analytics.py`, `audit.py`, `opportunity_metrics.py`, `calibration_watch.py`, `market_dna.py`, `verdicts.py`, `missed_winner.py`, `weight_approval.py`, `evolution.py`, `research_lab.py`, `confidence_evolution.py`, `premium_accuracy.py`, `validation.py`.

All confirmed read-only/advisory over real recorded outcomes; none can modify a live gate without the explicit human `weight_approval.py` pipeline (§0 proof). This category is the system's actual "self-learning," and it is correctly fenced off from "self-modifying" — exactly your Rule 4's distinction.

**Gap:** these ~14 modules each maintain their own measurement slice (calibration, capture rate, engine reliability, Brier score, MFE/MAE, verdicts). There is no single "Measurement Registry" that lists what's measured where — `health_center.py` and `research_lab.py` partially serve this but weren't built as a measurement index. Low priority, but would help avoid a 15th measurement module duplicating what one of these 14 already does.

---

## 8. RESEARCH MODULES (isolated from the live path by design)

| Module | Scope | Status |
|---|---|---|
| `backtest.py` | 2022-2026 daily-timeframe backtest of confluence's DNA | Isolated, on-demand |
| `historical_learning.py` | 5yr daily-OHLC "KNOWLEDGE" (underlying only, no option chain) | **Mixed** — `run()` is on-demand, but cached output (`similar_days()`) IS read live in `_ai_cycle` to populate `decision["market_memory"]`. Worth knowing this one isn't fully isolated the way the other three are. |
| `orfe_research.py` | Opening Range + Fibonacci hypothesis (this session) | Fully isolated — confirmed zero live callers |
| `replay.py` | Historical session step-through with AI decision markers | On-demand |

**ORFE Phase 0 current result** (6mo NIFTY, 83 qualifying days, 288 rows): win rate rises with retracement depth (0.382→28.8%, 0.786→63.5%), Target-2 rule needs a fix (0% hit rate across the board — a rule-definition problem, not a market-behavior finding), MAE tends to exceed MFE. Below your own 100-day/500-signal bar — directionally informative, not yet conclusive.

---

## 9. DASHBOARD / DISPLAY / SUPPORT (lighter treatment, per scoping note)

`journal.py`, `alerts.py`, `ai_timeline.py`, `health_center.py`, `system_verify.py`, `brain.py`, `weekend_ai.py`, `portfolio_risk.py`, `paper.py`, `scanner.py`, `opportunity.py`, `dom.py`, `mtf_confluence.py`, `market_session_manager.py`, `mtf_1h_cache.py`, `mtf_4h_cache.py`, `period_pivot_cache.py`, `persistence.py`, `cortex/` (LLM prompts — explicitly instructed "never override or contradict the execution gate").

All confirmed live/working, all correctly display-only or cache/infrastructure. No gaps found that affect the PRIMARY OBJECTIVE.

---

## 10. FLAGGED FOR CLEANUP (not urgent, not a rule violation — just found during the audit)

1. **`market_event.py`'s own docstring says "NOT WIRED"** — it is actually wired (`market_service.py:392-403`, since 2026-08-05). Stale comment, zero functional impact. One-line fix whenever convenient.
2. **`signal_engine.py` appears to be dead code** — a standalone weighted scoring engine with its own separate `WEIGHTS` dict, referenced nowhere outside its own file. Per your Rule 1 ("never remove existing working modules") this is flagged, not removed — it isn't "working" in the sense of being called by anything, so it's a candidate for either (a) deliberate removal after you confirm it's truly unused, or (b) documentation explaining why it's kept.
3. **Confluence's docstring says "ten layers," literal weighted count is 7** — cosmetic, but worth correcting so nobody designs against the wrong number later.

---

## 11. ARCHITECTURE DIAGRAM (as it exists today)

```
Broker (Dhan) ──┬─► _spot_tick (3s)   ──► lifecycle, market_event, memory, paper, audit
                ├─► _option_tick (15s)──► index_analytics(PCR/OI/maxpain) ──► smart_money
                │                     ──► move_detector, premium_radar, anomaly
                └─► _ai_cycle (180s)  ──► candles(1m) ──► confluence.run()
                                                            │
                              ┌─────────────────────────────┴─────────────────────────────┐
                              │  MANDATORY: trend · structure · mtf · oi                    │
                              │  SCORED:    + smart_money · greeks · volume_profile         │
                              │  VETOES:    capital_protection · guards(traps/no-trade)     │
                              │             · kill_switch (execution-only)                  │
                              │  OBSERVED:  candles · evidence_rank · structural_targets ·   │
                              │             expiry · market_profile · regime · global_*      │
                              └─────────────────────────────┬─────────────────────────────┘
                                                             ▼
                              decision.py ──► execution_gate.py ──► state.decision
                                                             │
                              ~30 more engines (alpha, exit_intel, market_path, ...) │
                                                             ▼
                                              websocket broadcast → dashboard
                                                             │
                              GET /api/decision-contract ◄───┘ (rebuilds fresh, re-checks gate #3)
                                                             ▼
                                                       Trade Explorer UI
```

Isolated research (never touches the diagram above): `backtest.py`, `orfe_research.py`, `replay.py` — reachable only via explicit `POST` routes.

---

## 12. DEPENDENCY GRAPH (key chains)

- `regime.py` → single producer, read (not recomputed) by `guards.py`, `capital_protection.py`, `intelligence.py`, `gamma_shield.py`, `future.py`.
- `index_analytics.py` (PCR/OI) → `confluence.py`'s oi layer, `expiry.py`, `market_dna.py`.
- `confluence.py` layers → `evidence_rank.py` (ranks them) → `decision_contract.py` (displays them).
- `memory._outcomes` → `market_dna.py` (similarity match) → `alpha_engine.py`, `decision_intelligence.py`, `signal_maturity.py`.
- `weight_approval.py` → read by `confluence.py` only after a completed human APPROVE→SIMULATE→APPLY cycle.
- `kill_switch.py` → read by `confluence.py` (veto string) and `execution_gate.py` (blocking reason) — never by any data-collection loop.

---

## 13. PRIORITY ORDER (evidence-driven, not guessed)

1. **Fix ORFE's Target-2 rule** (0% hit rate is a rule bug, not a market fact) — cheap, unblocks trustworthy Phase 0 numbers.
2. **Let ORFE accumulate to 100 days/500 signals** before any live-layer decision — your own bar, already in progress.
3. **CAS data-availability check** (does Dhan expose Closing-Auction-Session ticks/reference-price at all) — prerequisite fact-check before any Auction/Closing-Session engine can even be scoped.
4. **News Layer** — the single fully-absent item you asked about most explicitly; requires an external provider decision from you (Dhan cannot supply it — confirmed, not assumed).
5. **Supertrend** — cheap, self-contained, no data dependency; lowest-effort real gap-fill on your list.
6. **Gap Analysis consolidation** — combine the three scattered gap-related pieces (`global_context.py`, `global_feed.py`, `historical_learning.py`) into one place, or explicitly decide they should stay separate.
7. **Triple-gate consolidation** (`decision.py`/`execution_gate.py`/`decision_contract.py`) — architectural health, not urgent, but the longer it's deferred the more places a future gate-logic fix has to be applied three times.
8. **Cleanup items** (§10) — trivial, any time.

Everything else audited is either already live and working, or explicitly and correctly isolated as research.

---

## 14. FINAL ROADMAP (sequenced, evidence-gated — nothing here is authorized to build yet)

**Phase A — Fact-finding (no code):** CAS data-availability check; News provider decision (which API, whose cost); confirm whether Supertrend is actually wanted alongside the existing EMA/regime stack or would be redundant with it.

**Phase B — Cheap, self-contained additions (isolated, testable in hours):** Supertrend as a new observational layer (same pattern as `candles.py` — declared thresholds, non-rankable until proven, byte-identical-packet test before wiring). ORFE Target-2 rule fix + continued accumulation.

**Phase C — Data-dependent additions (blocked on Phase A answers):** News Layer (needs a provider); CAS/Auction Behaviour engine (needs Phase A's data-availability answer); Macro Events calendar (needs a source beyond the current manual `session_calendar.json`).

**Phase D — Consolidation (architectural health, not new evidence):** Reconcile the two Fibonacci implementations (`structure.py` live vs `orfe_research.py` research); triple-gate consolidation; Measurement Registry; docstring/dead-code cleanup from §10.

**Phase E — Only after B/C produce evidence:** Any new evidence layer moves from observational → evidence_rank.py-ranked only once it has its own THRESHOLD_REGISTRY and a real sample size, exactly the pattern already used for `candles.py` and now `orfe_research.py`. No new layer skips this queue.

Per your explicit instruction, none of Phases A–E are authorized to start from this report alone — this is the blueprint; each phase still needs its own scoped go-ahead when you're ready, same as every engine built this session.

---

## 15. RISK / MEMORY / API / PERFORMANCE — brief notes (no new items beyond what's already threaded above)

- **Risk:** already mature (§4) — the one real risk gap is the *absence* of News, not a flaw in what exists.
- **Memory:** already correctly fenced (§7) — the only improvement worth naming is a Measurement Registry, not new persistence.
- **API:** DhanHQ historical intraday now confirmed usable to 5yr/90-day-chunks (this session's `get_intraday_range()`); no other broker API gap surfaced in this audit.
- **Performance:** `_ai_cycle`'s ~30 sequential engines with no per-engine timing budget (§1) is the one performance-shaped item found; not currently causing a known problem, flagged for awareness.

---

*This document is a read-only audit. No thresholds were changed, no code was written to the trading system, and no module was removed. All findings trace to code read on 2026-08-07.*
