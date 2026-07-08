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

## DOCTRINE ADDITION — Global Context is never a hard gate

**Status: ✅ LOCKED (owner, 2026-07-08)**

If/when external global feeds (US futures, DXY, yields…) are connected:
Global Context may only ever be **context** — e.g. Risk-ON +3 / Risk-OFF −3
score adjustment. It must never hard-block and never override Trend.
