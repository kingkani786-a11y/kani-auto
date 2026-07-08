"use client";
import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useMarket } from "@/lib/store";
import type { PaperTrade } from "@/lib/types";

const fmt = (n?: number | null) =>
  n === undefined || n === null ? "—" : n.toLocaleString("en-IN", { maximumFractionDigits: 2 });

export default function PaperPage() {
  const { status, spot, signal } = useMarket();
  const [trades, setTrades] = useState<PaperTrade[]>([]);
  const [stats, setStats] = useState<any>({});
  const [pf, setPf] = useState<any>(null);
  const [capital, setCapital] = useState("1000000");
  const [riskPct, setRiskPct] = useState("1");
  const [qty, setQty] = useState("1");
  const [busy, setBusy] = useState(false);
  const [expanded, setExpanded] = useState<string | null>(null);

  const load = useCallback(async () => {
    try {
      const r = await api.paper();
      setTrades(r.trades);
      setStats(r.stats);
      setPf(await api.portfolioRisk().catch(() => null));
    } catch {}
  }, []);

  async function saveRiskConfig() {
    await api.portfolioConfig(Number(capital) || 1000000, Number(riskPct) || 1).catch(() => {});
    await load();
  }

  useEffect(() => {
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, [load]);

  async function open(side: "LONG" | "SHORT") {
    if (!status?.symbol) return;
    setBusy(true);
    try {
      await api.paperOpen({
        symbol: status.symbol, side, qty: Number(qty) || 1,
        stop_loss: signal?.stop_loss ?? null, target: signal?.target2 ?? null,
      });
      await load();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setBusy(false);
    }
  }

  async function close(id: string) {
    setBusy(true);
    try {
      await api.paperClose(id);
      await load();
    } catch (e: any) {
      alert(e.message);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="space-y-4">
      <section className="panel">
        <div className="panel-title">Paper Trading — Virtual Only, No Real Orders</div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4 text-sm">
          <div><div className="stat-label">Virtual P&L</div>
            <div className={`stat-value text-lg ${(stats.total_pnl ?? 0) >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>{fmt(stats.total_pnl)}</div></div>
          <div><div className="stat-label">Win Rate</div><div className="stat-value text-lg">{fmt(stats.win_rate)}%</div></div>
          <div><div className="stat-label">Closed / Open</div><div className="stat-value text-lg">{stats.closed ?? 0} / {stats.open ?? 0}</div></div>
          <div><div className="stat-label">Live {status?.symbol}</div><div className="stat-value text-lg">{fmt(spot?.ltp)}</div></div>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <input
            value={qty} onChange={(e) => setQty(e.target.value)} type="number" min="1"
            className="w-24 bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2 text-sm font-mono"
            placeholder="Qty"
          />
          <button onClick={() => open("LONG")} disabled={busy || !status?.connected}
            className="px-4 py-2 rounded-lg bg-terminal-bull/20 border border-terminal-bull/50 text-terminal-bull text-sm font-bold disabled:opacity-40">
            BUY {status?.symbol} @ {fmt(spot?.ltp)}
          </button>
          <button onClick={() => open("SHORT")} disabled={busy || !status?.connected}
            className="px-4 py-2 rounded-lg bg-terminal-bear/20 border border-terminal-bear/50 text-terminal-bear text-sm font-bold disabled:opacity-40">
            SELL {status?.symbol} @ {fmt(spot?.ltp)}
          </button>
          <span className="text-[11px] text-terminal-muted">SL/target auto-filled from the live signal when available.</span>
        </div>
      </section>

      <section className="panel">
        <div className="panel-title">Portfolio Risk Engine</div>
        <div className="flex flex-wrap items-end gap-2 mb-4">
          <div>
            <div className="stat-label mb-1">Capital</div>
            <input value={capital} onChange={(e) => setCapital(e.target.value)} type="number"
              className="w-32 bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2 text-sm font-mono" />
          </div>
          <div>
            <div className="stat-label mb-1">Risk / Trade %</div>
            <input value={riskPct} onChange={(e) => setRiskPct(e.target.value)} type="number" step="0.25"
              className="w-24 bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2 text-sm font-mono" />
          </div>
          <button onClick={saveRiskConfig}
            className="px-4 py-2 rounded-lg border border-terminal-border text-xs hover:border-terminal-accent">APPLY</button>
        </div>
        {pf && (
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm">
            <div><div className="stat-label">Equity</div><div className="stat-value">{fmt(pf.equity)}</div></div>
            <div><div className="stat-label">Exposure</div><div className="stat-value">{fmt(pf.exposure)} ({pf.exposure_pct}%)</div></div>
            <div><div className="stat-label">Open Risk</div><div className="stat-value">{fmt(pf.open_risk)} ({pf.open_risk_pct}%)</div></div>
            <div><div className="stat-label">Max Drawdown</div><div className="stat-value text-terminal-bear">{fmt(pf.max_drawdown)}</div></div>
            {pf.suggested_position && (
              <div className="col-span-2 sm:col-span-4 text-xs text-terminal-accent">
                Suggested size for live signal: {pf.suggested_position.qty} units
                {pf.suggested_position.lots ? ` (${pf.suggested_position.lots} lots)` : ""} — risking {fmt(pf.suggested_position.risk_amount)}
              </div>
            )}
            {(pf.warnings || []).map((w: string, i: number) => (
              <div key={i} className="col-span-2 sm:col-span-4 text-xs text-terminal-warn">⚠ {w}</div>
            ))}
          </div>
        )}
      </section>

      <section className="panel overflow-x-auto">
        <div className="panel-title">Trade History</div>
        {trades.length === 0 ? (
          <p className="text-sm text-terminal-muted">No paper trades yet.</p>
        ) : (
          <table className="w-full text-xs font-mono whitespace-nowrap">
            <thead>
              <tr className="stat-label text-left">
                {["Opened", "Symbol", "Side", "Qty", "Entry", "Exit", "P&L", "Status", ""].map((h) => (
                  <th key={h} className="pb-2 pr-3 font-normal">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {trades.map((t) => (
                <>
                  <tr key={t.id} className="border-t border-terminal-border/40">
                    <td className="py-1.5 pr-3">{t.opened_at}</td>
                    <td className="pr-3">{t.symbol}</td>
                    <td className={`pr-3 ${t.side === "LONG" ? "text-terminal-bull" : "text-terminal-bear"}`}>{t.side}</td>
                    <td className="pr-3">{t.qty}</td>
                    <td className="pr-3">{fmt(t.entry)}</td>
                    <td className="pr-3">{fmt(t.exit)}</td>
                    <td className={`pr-3 ${((t.pnl ?? t.unrealized) ?? 0) >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>
                      {fmt(t.pnl ?? t.unrealized)}{t.status === "OPEN" && t.unrealized !== undefined ? " (live)" : ""}
                    </td>
                    <td className="pr-3">{t.status}</td>
                    <td>
                      {t.status === "OPEN" ? (
                        <button onClick={() => close(t.id)} disabled={busy}
                          className="px-2 py-1 rounded border border-terminal-border text-[10px] hover:border-terminal-accent">
                          CLOSE
                        </button>
                      ) : t.review ? (
                        <button onClick={() => setExpanded(expanded === t.id ? null : t.id)}
                          className="px-2 py-1 rounded border border-terminal-border text-[10px] hover:border-terminal-accent">
                          REVIEW
                        </button>
                      ) : null}
                    </td>
                  </tr>
                  {expanded === t.id && t.review && (
                    <tr key={`${t.id}-review`} className="border-t border-terminal-border/40 bg-terminal-bg/60">
                      <td colSpan={9} className="py-3 px-2 whitespace-normal">
                        <div className={`font-bold mb-1 ${t.review.outcome === "WIN" ? "text-terminal-bull" : "text-terminal-bear"}`}>
                          {t.review.outcome === "WIN" ? "Why this trade succeeded" : "Why this trade failed"}
                        </div>
                        {t.review.why.map((w, i) => (<div key={i} className="text-gray-300">• {w}</div>))}
                        <div className="font-bold mt-2 mb-1 text-terminal-accent">What could improve</div>
                        {t.review.improve.map((w, i) => (<div key={i} className="text-gray-300">• {w}</div>))}
                        {(t.review as any).mentor && (
                          <div className="mt-3">
                            <div className="font-bold mb-1.5 text-terminal-accent">AI Trade Mentor</div>
                            <div className="flex flex-wrap gap-x-5 gap-y-1.5">
                              {Object.entries((t.review as any).mentor).map(([k, v]) => (
                                <div key={k} className="flex items-center gap-1.5">
                                  <span className="text-terminal-muted capitalize">{k.replace(/_/g, " ")}</span>
                                  <span className={`font-bold ${Number(v) >= 70 ? "text-terminal-bull" : Number(v) >= 45 ? "text-terminal-warn" : "text-terminal-bear"}`}>
                                    {String(v)}
                                  </span>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}
                      </td>
                    </tr>
                  )}
                </>
              ))}
            </tbody>
          </table>
        )}
      </section>
    </div>
  );
}
