"""Walk-Forward Validation — V8 item 1 (owner authorization, 2026-07-27).

Answers one question, honestly: is the existing daily-timeframe backtest
strategy (backtest.py — EMA20/50 stack + structure breakout + ADX>20 regime
filter + 1.2/2.5 ATR stop/target) a consistent, real edge across different
years, or profitable in one lucky year and not the others?

Deliberately NOT a parameter-optimization search (see
docs/V8_WALK_FORWARD_VALIDATION_PLAN.md, decision #1 — owner-approved
scope): no parameter is fit or tuned per fold here. Each fold is just
backtest.run() called on its own already-declared parameters, for a
different out-of-sample year. backtest.py itself is untouched — this
module only aggregates its existing per-year output into a consistency
view across the fold set.

Anchored/expanding folds (owner-approved, decision #2): with only 5 years
of daily history (2022-2026), a sliding fixed window would leave too little
data per fold, so "train" context grows fold over fold while the test year
moves forward. Since no fitting happens, "train" here is descriptive
context only, not a computation.
"""
from __future__ import annotations

from typing import Any

from ..broker.dhan import DhanClient
from . import backtest

# (train_context_years, test_year) — owner-approved 4-fold anchored design.
FOLDS: tuple[tuple[tuple[int, ...], int], ...] = (
    ((2022,), 2023),
    ((2022, 2023), 2024),
    ((2022, 2023, 2024), 2025),
    ((2022, 2023, 2024, 2025), 2026),
)


def _aggregate(fold_results: list[dict[str, Any]]) -> dict[str, Any]:
    sharpes = [f["sharpe_ratio"] for f in fold_results]
    expectancies = [f["expectancy_r"] for f in fold_results]
    net_positive = [f for f in fold_results if f["net_points"] > 0]

    def _mean(xs: list[float]) -> float:
        return round(sum(xs) / len(xs), 2) if xs else 0.0

    def _stdev(xs: list[float]) -> float:
        if len(xs) < 2:
            return 0.0
        m = sum(xs) / len(xs)
        return round((sum((x - m) ** 2 for x in xs) / (len(xs) - 1)) ** 0.5, 2)

    n = len(fold_results)
    pct_positive = round(len(net_positive) / n * 100, 1) if n else 0.0
    worst_dd = max((f["max_drawdown_pts"] for f in fold_results), default=0.0)

    if n == 0:
        verdict = "No folds evaluated — insufficient data."
    elif pct_positive == 100.0:
        verdict = f"Consistent across {n}/{n} test years — profitable in every out-of-sample fold."
    elif pct_positive >= 50.0:
        verdict = f"Mixed — profitable in {len(net_positive)}/{n} test years, not universally consistent."
    else:
        verdict = f"Concentrated, not stable — profitable in only {len(net_positive)}/{n} test years."

    return {
        "folds_evaluated": n,
        "sharpe_mean": _mean(sharpes),
        "sharpe_stdev": _stdev(sharpes),
        "expectancy_r_mean": _mean(expectancies),
        "expectancy_r_stdev": _stdev(expectancies),
        "pct_folds_net_positive": pct_positive,
        "worst_fold_drawdown_pts": round(worst_dd, 1),
        "verdict": verdict,
    }


async def run(client: DhanClient, symbol: str) -> dict[str, Any]:
    """Never fabricates: any fold that fails to fetch/evaluate is recorded
    with its error, not silently dropped or estimated — an honest partial
    result beats a fabricated complete one."""
    fold_results: list[dict[str, Any]] = []
    for train_years, test_year in FOLDS:
        try:
            result = await backtest.run(client, symbol, test_year)
            fold_results.append({
                "train_context_years": list(train_years),
                "test_year": test_year,
                "error": None,
                **result,
            })
        except Exception as e:
            fold_results.append({
                "train_context_years": list(train_years),
                "test_year": test_year,
                "error": str(e)[:200],
            })

    ok_folds = [f for f in fold_results if f.get("error") is None]
    return {
        "symbol": symbol,
        "methodology": ("Anchored walk-forward validation of the EXISTING declared "
                        "strategy (no parameters tuned/optimized per fold) — checks "
                        "consistency across out-of-sample years, not whether the "
                        "strategy can be improved."),
        "folds": fold_results,
        "aggregate": _aggregate(ok_folds) if ok_folds else {
            "folds_evaluated": 0,
            "verdict": "All folds failed — see per-fold errors.",
        },
        "note": ("V8 research tool (not wired to any live gate, decision, or size). "
                 "Historical performance, even if consistent, is not a guarantee of "
                 "future results."),
    }
