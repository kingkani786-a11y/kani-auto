"""Backtesting Engine (2022–2025).

Runs a daily-timeframe approximation of the live strategy over Dhan
historical data: trend stack + structure breakout + regime filter,
ATR-based stop and target — the same DNA as the intraday confluence
engine, evaluated end-of-day. Results are indicative, not a promise:
the live system additionally uses option-chain layers that don't exist
in daily history.
"""
from __future__ import annotations

from typing import Any

from ..broker.dhan import DhanClient
from ..broker.instruments import get_instrument
from ..engines import structure as structure_eng
from ..engines.technicals import adx, atr, ema

YEARS = (2022, 2023, 2024, 2025, 2026)


async def run(client: DhanClient, symbol: str, year: int) -> dict[str, Any]:
    if year not in YEARS:
        raise ValueError(f"Supported years: {YEARS}")
    inst = get_instrument(symbol)
    # warm-up tail from the prior year so indicators are ready on Jan 1
    candles = await client.get_daily_candles(inst, f"{year - 1}-09-01", f"{year}-12-31")
    if len(candles) < 80:
        raise ValueError("Not enough historical data returned")

    trades: list[dict] = []
    position: dict | None = None
    equity, peak, max_dd = 0.0, 0.0, 0.0

    for i in range(60, len(candles)):
        window = candles[: i + 1]
        day = candles[i]
        # skip warm-up period — only trade the requested year
        import datetime
        if datetime.datetime.fromtimestamp(day["time"]).year != year:
            continue

        closes = [c["close"] for c in window]
        atr_v = atr(window[-30:])
        adx_v = adx(window[-40:])

        # ---- manage open position ----
        if position:
            hit_sl = day["low"] <= position["sl"] if position["dir"] == 1 else day["high"] >= position["sl"]
            hit_tg = day["high"] >= position["tg"] if position["dir"] == 1 else day["low"] <= position["tg"]
            exit_px = None
            if hit_sl:
                exit_px = position["sl"]          # conservative: stop fills first
            elif hit_tg:
                exit_px = position["tg"]
            elif i == len(candles) - 1:
                exit_px = day["close"]
            if exit_px is not None:
                pnl = (exit_px - position["entry"]) * position["dir"]
                risk = abs(position["entry"] - position["sl"]) or 1.0
                trades.append({"pnl": pnl, "r": pnl / risk})
                equity += pnl
                peak = max(peak, equity)
                max_dd = max(max_dd, peak - equity)
                position = None
            continue

        # ---- entries: trend stack + structure breakout + regime filter ----
        e20 = ema(closes, 20)[-1]
        e50 = ema(closes, 50)[-1]
        st = structure_eng.analyze(window[-60:], atr_v)
        if adx_v < 20:
            continue  # chop filter — the regime engine's daily equivalent
        long_ok = e20 > e50 and day["close"] > e20 and st["event"] == "BREAKOUT" and st["direction"] != "BEAR"
        short_ok = e20 < e50 and day["close"] < e20 and st["event"] == "BREAKDOWN" and st["direction"] != "BULL"
        if long_ok or short_ok:
            d = 1 if long_ok else -1
            entry = day["close"]
            position = {"dir": d, "entry": entry,
                        "sl": entry - d * 1.2 * atr_v, "tg": entry + d * 2.5 * atr_v}

    wins = [t for t in trades if t["pnl"] > 0]
    losses = [t for t in trades if t["pnl"] <= 0]
    gross_win = sum(t["pnl"] for t in wins)
    gross_loss = abs(sum(t["pnl"] for t in losses))

    # Sharpe (per-trade R series, annualized by trade count) + expectancy in R
    rs = [t["r"] for t in trades]
    sharpe = 0.0
    if len(rs) > 2:
        mean_r = sum(rs) / len(rs)
        var = sum((r - mean_r) ** 2 for r in rs) / (len(rs) - 1)
        sd = var ** 0.5
        sharpe = round(mean_r / sd * (len(rs) ** 0.5), 2) if sd else 0.0
    expectancy = round(sum(rs) / len(rs), 2) if rs else 0.0

    return {
        "sharpe_ratio": sharpe,
        "expectancy_r": expectancy,
        "symbol": inst.symbol,
        "year": year,
        "trades": len(trades),
        "win_rate": round(len(wins) / len(trades) * 100, 1) if trades else 0.0,
        "avg_reward_risk": round(sum(t["r"] for t in trades) / len(trades), 2) if trades else 0.0,
        "profit_factor": round(gross_win / gross_loss, 2) if gross_loss else (99.0 if gross_win else 0.0),
        "max_drawdown_pts": round(max_dd, 1),
        "net_points": round(sum(t["pnl"] for t in trades), 1),
        "note": "Daily-timeframe approximation of the live confluence strategy; option-chain layers not simulated.",
    }
