# TRADING-DOCTRINE PROPOSALS LEDGER

*Every Trading-Doctrine parameter change lives here, in pipeline order:
RESEARCH → COLLECTING DATA → READY FOR REVIEW → APPROVED → DEPLOYED → MONITORING.
Nothing skips a stage. Owner approval is the only path to DEPLOYED.*

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

## DOCTRINE ADDITION — Global Context is never a hard gate

**Status: ✅ LOCKED (owner, 2026-07-08)**

If/when external global feeds (US futures, DXY, yields…) are connected:
Global Context may only ever be **context** — e.g. Risk-ON +3 / Risk-OFF −3
score adjustment. It must never hard-block and never override Trend.
