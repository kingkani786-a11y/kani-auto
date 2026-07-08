"use client";
import { useState } from "react";
import { useMarket } from "@/lib/store";

const fmtL = (n: number) =>
  Math.abs(n) >= 1e7 ? `${(n / 1e7).toFixed(1)}Cr` : Math.abs(n) >= 1e5 ? `${(n / 1e5).toFixed(1)}L` : Math.abs(n) >= 1e3 ? `${(n / 1e3).toFixed(0)}K` : `${Math.round(n)}`;

export function OptionChainTable() {
  const { chain, atm, status } = useMarket();
  const [expanded, setExpanded] = useState(false);  // default ATM±3, expand to ±10
  if (status?.market_type === "COMMODITY") return null;

  const atmIdx = atm != null ? chain.findIndex((x) => x.strike === atm) : -1;
  const view = !expanded && atmIdx >= 0
    ? chain.filter((_, i) => Math.abs(i - atmIdx) <= 3)
    : chain;
  const maxOI = Math.max(1, ...view.map((r) => Math.max(r.ce_oi, r.pe_oi)));

  return (
    <section className="panel overflow-x-auto">
      <div className="panel-title flex items-center justify-between">
        <span>Option Chain (ATM ± {expanded ? 10 : 3})</span>
        {chain.length > 0 && (
          <button onClick={() => setExpanded((e) => !e)}
            className="text-[10px] normal-case tracking-normal text-terminal-accent border border-terminal-border rounded px-2 py-0.5 hover:border-terminal-accent">
            {expanded ? "Show ATM ±3" : "Expand ATM ±10"}
          </button>
        )}
      </div>
      {chain.length === 0 ? (
        <p className="text-sm text-terminal-muted">Chain loads 15s after connect.</p>
      ) : (
        <table className="w-full text-[11px] sm:text-xs font-mono whitespace-nowrap">
          <thead>
            <tr className="stat-label">
              <th className="text-right pr-2 font-normal">OI</th>
              <th className="text-right pr-2 font-normal">OI Δ</th>
              <th className="text-right pr-2 font-normal">IV</th>
              <th className="text-right pr-2 font-normal text-terminal-bull">CE LTP</th>
              <th className="text-center px-3 font-normal">STRIKE</th>
              <th className="text-left pl-2 font-normal text-terminal-bear">PE LTP</th>
              <th className="text-left pl-2 font-normal">IV</th>
              <th className="text-left pl-2 font-normal">OI Δ</th>
              <th className="text-left pl-2 font-normal">OI</th>
            </tr>
          </thead>
          <tbody>
            {view.map((r) => (
              <tr key={r.strike} className={`border-t border-terminal-border/40 ${r.strike === atm ? "bg-terminal-accent/10" : ""}`}>
                <td className="text-right pr-2 relative">
                  <span className="absolute inset-y-0 right-0 bg-terminal-bull/15" style={{ width: `${(r.ce_oi / maxOI) * 100}%` }} />
                  <span className="relative">{fmtL(r.ce_oi)}</span>
                </td>
                <td className={`text-right pr-2 ${r.ce_oi_chg > 0 ? "text-terminal-bear" : "text-terminal-bull"}`}>{fmtL(r.ce_oi_chg)}</td>
                <td className="text-right pr-2 text-terminal-muted">{Number(r.ce_iv).toFixed(1)}</td>
                <td className="text-right pr-2 text-terminal-bull">{Number(r.ce_ltp).toFixed(2)}</td>
                <td className={`text-center px-3 font-bold ${r.strike === atm ? "text-terminal-accent" : ""}`}>{r.strike}</td>
                <td className="text-left pl-2 text-terminal-bear">{Number(r.pe_ltp).toFixed(2)}</td>
                <td className="text-left pl-2 text-terminal-muted">{Number(r.pe_iv).toFixed(1)}</td>
                <td className={`text-left pl-2 ${r.pe_oi_chg > 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>{fmtL(r.pe_oi_chg)}</td>
                <td className="text-left pl-2 relative">
                  <span className="absolute inset-y-0 left-0 bg-terminal-bear/15" style={{ width: `${(r.pe_oi / maxOI) * 100}%` }} />
                  <span className="relative">{fmtL(r.pe_oi)}</span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
