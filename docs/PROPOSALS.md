# TRADING-DOCTRINE PROPOSALS LEDGER

*Every Trading-Doctrine parameter change lives here, in pipeline order:
RESEARCH → COLLECTING DATA → READY FOR REVIEW → APPROVED → DEPLOYED → MONITORING.
Nothing skips a stage. Owner approval is the only path to DEPLOYED.*

---

## PROPOSAL #001 — Greeks Gate Softening (Regime-Conditional)

**Status: 🔬 COLLECTING DATA** *(owner decision 2026-07-08 — neither approved nor rejected)*

### Evidence so far
122 settled verdicts · Greeks blocked 115 · Missed 87% / Saved 13%.

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
targets from the active swing. Measure per method: T1-touch rate within the
tracked window, median MFE capture, SL-first rate. Fib wins only if it
touch-rates ≥ ATR across ≥3 regimes (trend/range/expiry) with n ≥ 30 each.

### Approval path
RESEARCH (this entry) → backtest table presented → owner approval → deploy
behind the existing target fields (no UI change needed — same T1/T2/T3 slots).

---

## DOCTRINE ADDITION — Global Context is never a hard gate

**Status: ✅ LOCKED (owner, 2026-07-08)**

If/when external global feeds (US futures, DXY, yields…) are connected:
Global Context may only ever be **context** — e.g. Risk-ON +3 / Risk-OFF −3
score adjustment. It must never hard-block and never override Trend.
