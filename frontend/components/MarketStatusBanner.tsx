"use client";
// PHASE 4/11 — calm market-status banner. When the market is closed we show an
// amber 🟡 MARKET CLOSED with last close + next-open countdown, NOT a red error.
// AI / Scanner / signals are paused server-side; this just communicates it.

import { useEffect, useState } from "react";
import { useMarket } from "@/lib/store";

function fmtCountdown(secs: number): string {
  if (secs <= 0) return "soon";
  const h = Math.floor(secs / 3600);
  const m = Math.floor((secs % 3600) / 60);
  return h > 0 ? `${h}h ${m}m` : `${m}m`;
}

export function MarketStatusBanner() {
  const { status, spot } = useMarket();
  const ms = (status as any)?.market_status;
  const [, tick] = useState(0);

  // local 1s re-render so the countdown feels live between status polls
  useEffect(() => {
    const t = setInterval(() => tick((n) => n + 1), 1000);
    return () => clearInterval(t);
  }, []);

  if (!status?.connected || !ms || ms.is_open) return null;   // only when closed + connected

  const lastClose = (status as any)?.last_close ?? spot?.ltp;

  return (
    <div className="panel border-terminal-warn/50 bg-terminal-warn/5 py-3">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <span className="text-lg">🟡</span>
          <span className="text-sm font-bold tracking-wider text-terminal-warn">
            MARKET CLOSED {ms.weekend ? "(WEEKEND)" : ""}
          </span>
        </div>
        <div className="text-xs text-terminal-muted">
          IST {ms.ist_time} · opens {ms.next_open_ist ?? "—"}
          {ms.seconds_to_open ? ` · in ${fmtCountdown(ms.seconds_to_open)}` : ""}
        </div>
      </div>
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-2.5 text-xs">
        <div><div className="stat-label">Last Close</div><div className="font-mono">{lastClose ? Number(lastClose).toLocaleString("en-IN") : "—"}</div></div>
        <div><div className="stat-label">Broker</div><div className="text-terminal-bull">CONNECTED</div></div>
        <div><div className="stat-label">AI / Scanner</div><div className="text-terminal-warn">PAUSED</div></div>
        <div><div className="stat-label">Signals</div><div className="text-terminal-warn">WAIT</div></div>
      </div>
      <div className="text-[10px] text-terminal-muted mt-2">
        Live analysis resumes automatically when the market opens — no refresh needed.
      </div>
    </div>
  );
}
