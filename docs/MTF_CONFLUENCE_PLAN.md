# Multi-Timeframe Confluence Engine — Step 10 Plan (V7.0 Roadmap)

Date: 2026-07-27
Status: **IMPLEMENTED — built, verified, awaiting commit+push approval.**

Owner's spec: 7 real timeframes (1m/3m/5m/15m/1H/4H/Daily), each scored on
Trend/Structure/Momentum/VWAP/EMA/BOS-CHOCH/Volume/CPR into an alignment
score, feeding the Hero card (per-TF BUY/SELL + star rating), a new Evidence
Panel row, a Risk Panel "Higher Timeframe Conflict" flag (which should
reduce trade size), and AI Dealer voice narration.

## What already exists — this is NOT a from-scratch build

- **`backend/app/engines/mtf.py`** is real and heavily wired (into the
  calibration force-WAIT gate, dynamic confidence, trade-quality grade,
  Decision Matrix's "MTF" row, and a Tamil voice line) — but it is a
  **single-indicator field wearing a multi-timeframe name**: it resamples
  ONE 1-minute candle feed into 6 virtual buckets (1/3/5/15/30/60m — no 4H,
  no Daily) and scores only EMA20-vs-EMA50-vs-price per bucket. "Alignment"
  = what % of those 6 buckets agree on that one signal.
- **The compute functions you'd need are already timeframe-agnostic and
  reusable as-is**: `structure.py` (including BOS/CHOCH), `technicals.py`
  (EMA/VWAP/ATR/momentum), and `support_resistance.py`'s CPR math all
  operate on whatever candle array they're given — none are hardcoded to a
  specific bar duration. This is mostly new orchestration, not new algorithms.
- **Real per-timeframe candle *fetching* already exists** (`dhan.py`'s
  `get_tf_candles()`) but is wired only to the price-chart endpoint, never
  to any analysis engine.
- **Daily-timeframe infrastructure already exists and runs today**:
  `period_pivot_cache.py` already fetches daily candles and computes
  weekly/monthly CPR pivots; `historical_learning.py` already fetches ~3
  years of daily OHLC for a different feature. Both are reusable.

## The real risk: broker rate limits

The platform has ONE shared broker rate budget (45 requests/min, ≥1.1s
between any two calls) that spot price, option chain, and the AI cycle's
1-minute candle refresh all already depend on — this budget is directly
tied to keeping the LIVE feed (and therefore every capital-protection
signal on the dashboard) working. Fetching all 7 real timeframes fresh
every 30-second AI cycle would mean dozens of extra broker calls per
cycle — a 5-10x increase in call volume that risks degrading the very
feed the whole platform depends on. This is a "capital protection >
opportunity" collision, not a minor detail.

**Proposed safe design — costs zero or near-zero extra broker calls:**
- **1m**: use the existing `state.candles` feed directly (already fetched).
- **3m / 5m / 15m / 30m / 1H**: resample from that SAME existing 1m feed
  (same technique `mtf.py`/`dhan.py` already use for their virtual/derived
  timeframes) — **zero new broker calls**.
- **Daily**: reuse the existing daily-candle cache (`period_pivot_cache.py`)
  — **zero new broker calls**, already refreshed for a different feature.
- **4H**: the one genuinely new cost. 600 bars of 1m history (~10 hours)
  isn't enough to build a meaningful 4H series by resampling, so this needs
  its own low-frequency fetch — but a 4H candle only closes 6x/day, so this
  can run on a slow cadence (e.g. every 15-30 min, not every 30s), keeping
  the added broker cost small and bounded.

## A boundary this project has already established twice (Steps 8 and 9)

Your spec's "Risk panel: Higher Timeframe Conflict → trade size should
reduce" is a **sizing rule change**, not a display change. This project's
own Trading Doctrine already governs exactly this category: "Confidence
threshold... these are NOT constitution — they are hypotheses. With
repeated evidence they MAY change, but only through the approval pipeline"
(Observation → Evidence → Proposal → Approval → Deployment → Monitoring).
Automatically shrinking position size the moment this step ships — before
any evidence exists on whether HTF conflicts are actually predictive here —
would repeat the exact kind of undisclosed-heuristic-as-gate pattern Step 8
found and refused to touch.

**Proposed**: build the real MTF engine and SHOW the "Higher Timeframe
Conflict: YES/NO" flag on the Risk panel — but don't wire it to actually
change any lot count yet. Whether it should reduce sizing becomes a
separate proposal for your evidence pipeline once there's real data on how
often it fires and whether it would have helped.

**Also proposed, mirroring the same boundary**: build this as a NEW,
additive engine (e.g. `mtf_confluence.py`) feeding only the NEW display
surfaces (Hero table, Evidence row, Risk flag, Voice). Leave the EXISTING
`mtf.py`/`layers["mtf"]` completely untouched — it keeps feeding the
calibration gate, dynamic confidence, and trade-quality grade exactly as
it does today. Swapping what feeds those live gates would itself be a
Trading Doctrine change requiring the evidence pipeline, not something a
"build the MTF panel" step should do as a side effect.

## Sign-off needed (4 decisions)

1. **Fetch design**: resample 3m/5m/15m/30m/1H from the existing 1m feed
   (free), reuse the existing daily cache for Daily (free), and add one new
   low-frequency (~15-30 min) fetch only for 4H — confirm this bounded-cost
   approach rather than fetching all 7 timeframes fresh every cycle?
2. **Additive-only architecture**: build the new real MTF engine as a
   separate, new computation feeding only new display surfaces — leave the
   existing `mtf.py` (and everything it already gates: calibration,
   confidence, trade quality) completely unchanged?
3. **"Reduce trade size on conflict"**: display-only for now (show the
   flag, don't touch position sizing) — treat actually reducing size as a
   separate future proposal once real evidence exists?
4. **All 8 signal types** (Trend/Structure/Momentum/VWAP/EMA/BOS-CHOCH/
   Volume/CPR) per timeframe, using the already-reusable compute functions
   — confirm this full scope rather than a reduced subset?

All 4 confirmed by the owner (Recommended option selected each time).

## What shipped

**Backend:**
- `backend/app/services/period_pivot_cache.py` — extended (zero new broker
  calls) to also retain the raw daily candle list already being fetched,
  so the Daily leg of MTF confluence has a free data source.
- `backend/app/services/mtf_4h_cache.py` (NEW) — the one genuinely new
  broker cost: a 20-min-TTL cache for 4H candles, wired into the existing
  2-min scanner loop in `market_service.py` alongside the pivot cache
  refresh — bounded, low-frequency, doesn't compete with the live feed.
- `backend/app/engines/mtf_confluence.py` (NEW) — the core engine. Scores
  all 8 signal types per timeframe across 1m/3m/5m/15m/1H/4H/Daily, reusing
  `technicals.trend_engine()`, `structure.analyze()`, and
  `support_resistance.pivot_formula()` with zero new algorithms. 1m/3m/5m/
  15m/1H are resampled from the existing 1m feed (`mtf.py`'s own
  `resample()`, imported not reimplemented); 4H and Daily read their own
  caches. Produces `alignment_pct`/`alignment_stars` (weighted by
  timeframe, higher TFs weighted more) and `higher_tf_conflict` (true only
  when a HIGHER timeframe — 1H/4H/Daily — disagrees with the Hero's own
  bias; lower-TF disagreement is not flagged, by design). Verified against
  4 synthetic scenarios (full alignment, HTF conflict, no hero bias, no
  data) — all behaved exactly as designed.
- `backend/app/services/market_service.py` — wired `mtf_confluence.analyze()`
  into the main AI cycle (right after the Alpha Detection block), storing
  the result on `decision["mtf_confluence"]`.
- `backend/app/services/decision_contract.py` — forwards the engine result
  as a new top-level `mtf` field on the contract (same shape the engine
  returns); added a "MTF Alignment" item to `ai_dealer`'s `why_buy` and an
  "MTF Conflict" item to `why_not_buy` (both pure reads, `ok`/`active`
  computed from the already-published `higher_tf_conflict` flag — no new
  scoring). `ai_dealer` also carries a small `mtf` summary (ready/
  higher_tf_conflict/alignment_pct/alignment_stars) for the voice layer.
- `backend/app/services/brain.py` — `_ai_dealer_speech()` now appends one
  more narration line: "Higher timeframes are aligned." when
  `higher_tf_conflict` is false, or "Lower timeframe is bullish, but
  {1H/4H/Daily} timeframe remains bearish." + "Waiting." when true (pure
  restatement of already-computed facts — no new opinion, per the
  Golden Rule). Silent when the engine isn't ready yet.

**Frontend:**
- `TradeNowCard.tsx` (Hero) — new "Multi-Timeframe" block: per-TF verdict
  row for 5m/15m/1H/4H/Daily (color-coded BUY/SELL/neutral) plus either
  "MTF Alignment ★★★★★" or "MTF CONFLICT" with an informational caption
  pointing to the Execution Lock/Risk panel — explicitly states it does
  not change position size.
- `EvidencePanel.tsx` — new "Multi Timeframe" row: `5m ✓ / 15m ✓ / 1H ✓ /
  4H ✓ / Daily ✓` style, ✓ meaning "this timeframe agrees with the Hero's
  own already-decided bias" (✗ if it disagrees, "–" if neutral/no data) —
  never a second opinion, purely a re-presentation of the engine's verdicts
  against the Hero's own call.
- `TradeRiskPanel.tsx` — new "Higher Timeframe Conflict: YES/NO" row,
  display-only as agreed in decision #3 above — does NOT touch position
  sizing. Any future sizing change is a separate Trading Doctrine proposal.

**Scope boundaries held (matching Steps 8/9's precedent):** the existing
`mtf.py` engine and everything it feeds (calibration gate, dynamic
confidence, trade-quality grade) is completely untouched. Nothing here
changes any real gate or gates position size — `higher_tf_conflict` is
informational only everywhere it appears.

**Verification performed:**
- Backend: `compileall` clean across all touched/new files; direct import
  and `decision_contract.contract()` smoke test (idle state produces the
  honest degraded shape with `mtf.ready: false` and `MTF Alignment: ok=None`
  — never a fabricated ✗).
- `mtf_confluence.analyze()`: 4 synthetic scenarios (full alignment → 100%/
  5 stars/no conflict; Daily disagrees → conflict flagged; no hero bias →
  alignment fields honestly None; no candle data → honest `ready: False`).
- `brain._ai_dealer_speech()`: 3 synthetic scenarios (aligned-buy, HTF
  conflict, not-ready) — exact phrasing matched the owner's spec examples.
- Frontend: `tsc --noEmit` clean, full `next build` clean (29/29 static
  pages, including `/`).
- Live browser check on an isolated scratch backend (port 8010) + scratch
  frontend (port 3010, `BACKEND_URL` pointed at the scratch backend) — the
  live production processes (8000/5173/3000) were never touched or
  restarted. A temporary, unrouted preview page mounted the 3 changed
  components directly with a monkey-patched `fetch` feeding two synthetic
  `decision-contract` payloads (aligned-5-star and HTF-conflict). Both
  rendered pixel-correct against the owner's own spec examples; the temp
  preview page and both scratch server processes were deleted/killed after
  verification, leaving no trace in the working tree (`git status` clean
  except the intended Step 10 files).
