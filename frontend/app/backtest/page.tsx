"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { BacktestResult, SymbolInfo } from "@/lib/types";

const YEARS = [2022, 2023, 2024, 2025, 2026];

export default function BacktestPage() {
  const [symbols, setSymbols] = useState<SymbolInfo[]>([]);
  const [symbol, setSymbol] = useState("NIFTY");
  const [year, setYear] = useState(2024);
  const [busy, setBusy] = useState(false);
  const [results, setResults] = useState<BacktestResult[]>([]);
  const [error, setError] = useState("");

  useEffect(() => {
    api.symbols().then(setSymbols).catch(() => {});
  }, []);

  async function run() {
    setBusy(true);
    setError("");
    try {
      const r = await api.backtest(symbol, year);
      setResults((prev) => [r, ...prev.filter((p) => !(p.symbol === r.symbol && p.year === r.year))]);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4 max-w-3xl mx-auto">
      <section className="panel">
        <div className="panel-title">Backtesting Engine (2022–2025)</div>
        <div className="flex flex-wrap items-center gap-2">
          <select value={symbol} onChange={(e) => setSymbol(e.target.value)}
            className="bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2 text-sm font-mono">
            {symbols.map((s) => (<option key={s.symbol} value={s.symbol}>{s.symbol}</option>))}
          </select>
          <div className="flex gap-1">
            {YEARS.map((y) => (
              <button key={y} onClick={() => setYear(y)}
                className={`px-3 py-2 rounded-lg text-sm font-mono border ${
                  year === y ? "bg-terminal-accent text-black border-terminal-accent font-bold" : "border-terminal-border text-terminal-muted"
                }`}>
                {y}
              </button>
            ))}
          </div>
          <button onClick={run} disabled={busy}
            className="px-5 py-2 rounded-lg bg-terminal-accent text-black font-bold text-sm disabled:opacity-50">
            {busy ? "RUNNING…" : "RUN BACKTEST"}
          </button>
        </div>
        {error && <div className="mt-3 text-sm text-terminal-bear">✕ {error}</div>}
        <p className="text-[11px] text-terminal-muted mt-3">
          Daily-timeframe approximation of the live confluence strategy (trend stack + structure breakout +
          regime filter, ATR stops). Requires an active broker connection for historical data. Past results
          do not predict future performance.
        </p>
      </section>

      {results.map((r) => (
        <section key={`${r.symbol}-${r.year}`} className="panel">
          <div className="panel-title">{r.symbol} — {r.year}</div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-3 text-sm">
            <div><div className="stat-label">Trades</div><div className="stat-value text-lg">{r.trades}</div></div>
            <div><div className="stat-label">Win Rate</div><div className="stat-value text-lg">{r.win_rate}%</div></div>
            <div><div className="stat-label">Avg Reward:Risk</div><div className="stat-value text-lg">{r.avg_reward_risk}R</div></div>
            <div><div className="stat-label">Profit Factor</div><div className="stat-value text-lg">{r.profit_factor}</div></div>
            <div><div className="stat-label">Max Drawdown</div><div className="stat-value text-lg text-terminal-bear">{r.max_drawdown_pts} pts</div></div>
            <div><div className="stat-label">Sharpe Ratio</div><div className="stat-value text-lg">{r.sharpe_ratio ?? "—"}</div></div>
            <div><div className="stat-label">Expectancy</div><div className="stat-value text-lg">{r.expectancy_r ?? "—"}R</div></div>
            <div><div className="stat-label">Net Points</div>
              <div className={`stat-value text-lg ${r.net_points >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>{r.net_points}</div></div>
          </div>
        </section>
      ))}
    </div>
  );
}
