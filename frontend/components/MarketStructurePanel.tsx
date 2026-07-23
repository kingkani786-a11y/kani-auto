"use client";
// MARKET STRUCTURE — Phase 3 (owner, 2026-07-24, item #5 Module 3). Auto
// Structure (HH/HL/LH/LL + BOS/CHOCH), Liquidity Zones (Buy/Sell-side +
// Stop Hunt), Auto Fibonacci + Golden Zone, Auto Trendline — all pure
// renders of structure.py's own output, nothing computed client-side.
//
// Trendline is shown as numbers (two anchor points + current projection),
// not drawn on the chart yet — that needs a deeper ProChart.tsx integration,
// scoped separately.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const BOS_CHOCH_STYLE: Record<string, string> = {
  BOS: "text-terminal-bull border-terminal-bull/50",
  CHOCH: "text-terminal-warn border-terminal-warn/50",
};

export function MarketStructurePanel() {
  const [r, setR] = useState<any>(null);
  useEffect(() => {
    const load = () => api.marketStructure().then(setR).catch(() => {});
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);
  if (!r?.ready) return null;

  const fib = r.fibonacci || {};
  const fibLevels = Object.entries(fib.levels || {}) as [string, number][];
  const golden = fib.golden_zone || [];
  const tl = r.trendline || {};

  return (
    <div className="panel border border-terminal-border/60 space-y-2">
      <div className="flex items-center justify-between">
        <div className="panel-title mb-0">Market Structure <span className="text-[10px] text-terminal-muted font-normal">(auto)</span></div>
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold text-white">{r.swing}</span>
          {r.bos_choch && (
            <span className={`text-[10px] font-bold px-1.5 py-0.5 rounded border ${BOS_CHOCH_STYLE[r.bos_choch] || ""}`}>
              {r.bos_choch}
            </span>
          )}
        </div>
      </div>

      {/* Liquidity zones — ICT framing over the same clustered pivots */}
      <div className="grid grid-cols-2 gap-2 text-[10px]">
        <div>
          <div className="text-terminal-bear font-semibold mb-0.5">BUY-SIDE LIQUIDITY (above)</div>
          {(r.buy_side_liquidity || []).length
            ? r.buy_side_liquidity.map((z: number) => <div key={z} className="tabular-nums text-terminal-muted">{z}</div>)
            : <div className="text-terminal-muted">none clustered</div>}
        </div>
        <div>
          <div className="text-terminal-bull font-semibold mb-0.5">SELL-SIDE LIQUIDITY (below)</div>
          {(r.sell_side_liquidity || []).length
            ? r.sell_side_liquidity.map((z: number) => <div key={z} className="tabular-nums text-terminal-muted">{z}</div>)
            : <div className="text-terminal-muted">none clustered</div>}
        </div>
      </div>

      {(r.stop_hunts || []).length > 0 && (
        <div className="text-[10px] border-t border-terminal-border pt-1">
          <div className="text-terminal-warn font-semibold mb-0.5">STOP HUNT DETECTED</div>
          {r.stop_hunts.map((h: any, i: number) => (
            <div key={i} className="text-terminal-muted">{h.type.replace(/_/g, " ")} @ {h.zone}</div>
          ))}
        </div>
      )}

      {/* Fibonacci + Golden Zone */}
      {fibLevels.length > 0 && (
        <div className="text-[10px] border-t border-terminal-border pt-1">
          <div className="text-terminal-muted font-semibold mb-0.5 uppercase">
            Fibonacci ({fib.direction === "UP_LEG" ? "retracing down" : "retracing up"})
          </div>
          <div className="flex flex-wrap gap-x-2 gap-y-0.5">
            {fibLevels.map(([pct, lvl]) => {
              const inGolden = golden.length === 2 && lvl >= golden[0] && lvl <= golden[1];
              return (
                <span key={pct} className={inGolden ? "text-terminal-accent font-semibold" : "text-terminal-muted"}>
                  {pct}%: {lvl}{inGolden ? " ★" : ""}
                </span>
              );
            })}
          </div>
          {golden.length === 2 && (
            <div className="text-terminal-accent mt-0.5">Golden Zone: {golden[0]} – {golden[1]}</div>
          )}
        </div>
      )}

      {/* Auto Trendline — numeric for now (chart overlay is a separate pass) */}
      {(tl.resistance_trendline || tl.support_trendline) && (
        <div className="text-[10px] border-t border-terminal-border pt-1 space-y-0.5">
          <div className="text-terminal-muted font-semibold uppercase">Trendline (projected to now)</div>
          {tl.resistance_trendline && (
            <div className="text-terminal-bear">Resistance trend → {tl.resistance_trendline.projected_current}</div>
          )}
          {tl.support_trendline && (
            <div className="text-terminal-bull">Support trend → {tl.support_trendline.projected_current}</div>
          )}
        </div>
      )}
    </div>
  );
}
