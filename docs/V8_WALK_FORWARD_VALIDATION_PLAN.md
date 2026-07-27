# V8 Item 1 — Walk-Forward Validation Framework — Plan

Branch: `v8-dev` (isolated worktree at `~/cloud-ai-trader-v8`, never merged
without explicit approval). Feature flag: `CAT_V8_WALK_FORWARD_VALIDATION`
(off by default, see `backend/app/v8_flags.py`).

Date: 2026-07-27
Status: **IMPLEMENTED on `v8-dev` — verified, not yet merged to `main`.**

## What already exists (audit)

`backend/app/services/backtest.py` already does the hard part: fetches
Dhan daily candles, evaluates the current confluence strategy (EMA20/50
stack + structure breakout + ADX>20 regime filter + 1.2/2.5 ATR stop/target)
one full calendar year at a time (`run(client, symbol, year)`), and returns
a solid metric set already: Sharpe, expectancy(R), win rate, profit factor,
max drawdown, net points. 5 years of data are available (2022–2026).

**What's missing is purely the walk-forward *methodology* around this** —
today each year is evaluated in isolation; nothing checks whether the
strategy's edge holds up when tested on data it wasn't "aware of," or
whether performance is consistent across periods vs. concentrated in one
lucky year.

## Scope decision — validate, don't optimize (this is the key design choice)

Two very different things could be called "walk-forward validation":

1. **(Proposed) Validate the existing fixed strategy** — run the SAME
   already-declared parameters (EMA20/50, ADX>20, 1.2/2.5 ATR) across
   rolling out-of-sample windows and check whether performance is
   *consistent*, not whether it can be *improved*. No new parameters are
   searched or tuned. This answers "is the current backtest a real,
   stable edge, or a historical fluke concentrated in one good year?" —
   directly closing the gap this item was proposed to close.
2. **(NOT proposed, flagging explicitly) A parameter-optimizing
   walk-forward loop** — search for the best EMA/ATR/ADX parameters in each
   training window, then test the *found* parameters out-of-sample. This
   is a materially bigger, riskier undertaking: real overfitting risk,
   much more compute, and it would silently start treating the strategy's
   own parameters as tunable — which is itself a Trading Doctrine question
   (these parameters currently ARE the declared strategy, not free
   variables). This is a separate, later item if ever wanted — not part of
   this pass.

**Recommendation: build (1) only.** It's the direct, honest answer to
"can we trust the existing backtest numbers," with no new overfitting
surface and no new tunable-parameter question to resolve.

## Window design

Anchored (expanding-window) walk-forward, since only 5 years of daily
history exist — a sliding fixed-size window would leave too little data per
fold:

| Fold | Train (context only, not fit) | Test (out-of-sample) |
|---|---|---|
| 1 | 2022 | 2023 |
| 2 | 2022–2023 | 2024 |
| 3 | 2022–2024 | 2025 |
| 4 | 2022–2025 | 2026 (partial year, to-date) |

Since no parameters are being fit per (1) above, "train" here isn't a
model-fitting step — it's included in the report only as context (e.g.,
"3 years of prior history existed before this test year"). The real content
of each fold is just `backtest.run(client, symbol, test_year)`, called once
per year, exactly as it already works today — walk-forward here is really
about **aggregating and presenting** the existing per-year results as a
consistency study, not a new computation per fold.

## Aggregate metrics (new, on top of existing per-year output)

- Per-fold: everything `backtest.run()` already returns, unchanged.
- Aggregate: mean/stdev of Sharpe and expectancy_r across folds, % of folds
  net-positive, worst single-fold drawdown, and a plain-language verdict
  (e.g., "Consistent across 4/4 years" vs "Profitable in 2/4 years —
  concentrated, not a stable edge").
- Never a single "pass/fail" score presented as calibrated — matches this
  project's disclosed-formula doctrine throughout.

## Where this surfaces

- New file: `backend/app/services/walk_forward.py` — one function,
  `run(client, symbol) -> dict`, calling `backtest.run()` once per year in
  `backtest.YEARS` and aggregating. Zero changes to `backtest.py` itself.
- New route: `GET /api/v8/walk-forward?symbol=NIFTY` — namespaced under
  `/api/v8/` so it's structurally impossible to confuse with any real
  production endpoint; gated by `v8_flags.walk_forward_validation` (returns
  404/disabled note if the flag is off).
- No frontend panel in this pass (this is a backend research tool first);
  a dashboard view can follow once the numbers are reviewed and judged
  useful enough to look at repeatedly.
- **Touches nothing else.** `backtest.py`, `confluence.py`, `decision.py`,
  the calibration gate, position sizing — all completely unchanged.

## Validation plan for this tool itself

- Unit tests with synthetic fold data (verify fold construction, aggregate
  math) — no real broker call needed for this part.
- Then one real run against live Dhan daily data for NIFTY, inspected
  manually against the numbers the existing single-year `backtest.py`
  already produces, to confirm the aggregation matches expectations.
- No paper-trading step applies to this specific item — it's a
  research/analysis tool, not something that ever produces a live signal.

## Sign-off (3 decisions — all confirmed by owner, Recommended option each time)

1. Scope: validate the fixed strategy only, no parameter search. **Confirmed.**
2. 4-fold anchored/expanding design, test years 2023–2026. **Confirmed.**
3. Backend-only research endpoint, no dashboard panel yet. **Confirmed.**

## What shipped

- `backend/app/v8_flags.py` (NEW) — feature-flag scaffold for all V8 items,
  every flag off by default, env-var controlled
  (`CAT_V8_WALK_FORWARD_VALIDATION=1` to enable this one).
- `backend/app/services/walk_forward.py` (NEW) — `run(client, symbol)`,
  calling `backtest.run()` once per fold's test year (2023/2024/2025/2026)
  with zero changes to `backtest.py` itself, then aggregating into
  mean/stdev Sharpe & expectancy, % folds net-positive, worst-fold drawdown,
  and a plain-language verdict. A failed fold is recorded with its error,
  never silently dropped or estimated (matches this project's own
  no-fabrication doctrine).
- `backend/app/api/routes.py` — new `GET /api/v8/walk-forward?symbol=NIFTY`,
  namespaced under `/api/v8/`, gated by the feature flag (404 if disabled,
  same `_require_connection()` 409 pattern as every other broker-backed
  endpoint if disabled-but-connected... if enabled-but-not-connected).

**Touches nothing else** — `backtest.py`, `confluence.py`, `decision.py`,
the calibration gate, position sizing: all byte-for-byte unchanged on this
branch relative to `main`.

## Verification performed

- Backend compile + import: clean.
- `_aggregate()` unit-tested against 4 synthetic scenarios: all-folds-positive
  (100%, "Consistent" verdict), mixed (50%, "Mixed" verdict), concentrated
  (25%, "Concentrated, not stable" verdict), and empty (0 folds, honest
  "insufficient data" verdict) — all passed exactly as designed.
- `run()`'s error handling unit-tested with a mocked `backtest.run` that
  fails one fold (2025) — confirmed all 4 folds are still reported, the
  failed one carries its error message, and the aggregate correctly
  excludes it from the mean/stdev/percentage math (3/4 folds used).
- End-to-end gating verified live on an isolated scratch instance (port
  8020, `v8-dev` worktree only): flag off → `404` with a clear message;
  flag on, no broker connected → `409 Not connected` (identical to every
  other broker-backed endpoint's behavior) — confirmed both gates work
  before any real broker call is ever attempted.
- **Not yet run against real historical data** — that step needs real Dhan
  credentials, which are never something I hold or enter; whenever the
  owner wants to see the real numbers, they can connect on a scratch
  instance of this branch with `CAT_V8_WALK_FORWARD_VALIDATION=1` set and
  call `GET /api/v8/walk-forward?symbol=NIFTY`.
- Confirmed production (`main`, live processes) completely unaffected
  throughout — live backend still reports `4cd3884` after all of this work.
