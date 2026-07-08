"use client";
// V13.1 Data Quality Monitor — display only. Polls the existing
// /api/health/data report so the trader knows if the data is reliable.

import { useEffect, useState } from "react";
import { getToken } from "@/lib/api";

const TONE: Record<string, string> = {
  OK: "text-terminal-bull", GOOD: "text-terminal-bull",
  FAIR: "text-terminal-warn", DEGRADED: "text-terminal-warn", DELAYED: "text-terminal-warn",
  POOR: "text-terminal-bear", CORRUPT: "text-terminal-bear", MISSING: "text-terminal-bear",
  "N/A": "text-terminal-muted",
};

const LABELS: Record<string, string> = {
  quotes: "Options Feed", option_chain: "Chain Feed", oi: "OI Feed",
  greeks: "Greeks Feed", futures: "Futures Feed", market_feed: "Market Feed",
  candles: "Candle Feed", signals: "Signal Feed",
};

export function DataQualityPanel() {
  const [dq, setDq] = useState<any>(null);

  useEffect(() => {
    const load = () =>
      fetch("/api/health/data", { headers: { "X-Auth-Token": getToken() } })
        .then((r) => (r.ok ? r.json() : null)).then(setDq).catch(() => {});
    load();
    const t = setInterval(load, 8000);
    return () => clearInterval(t);
  }, []);

  const overall = dq?.overall_display ?? "—";
  return (
    <section className="panel">
      <div className="panel-title flex items-center justify-between">
        <span>Data Quality Monitor</span>
        <span className={`text-sm font-bold ${TONE[overall] ?? "text-terminal-muted"}`}>{overall}</span>
      </div>
      {!dq ? (
        <p className="text-sm text-terminal-muted">Checking feeds…</p>
      ) : (
        <>
          <div className="flex items-center gap-2 mb-3">
            <div className="flex-1 h-1.5 rounded bg-terminal-bg overflow-hidden">
              <div className={`h-full ${dq.completeness >= 80 ? "bg-terminal-bull" : dq.completeness >= 50 ? "bg-terminal-warn" : "bg-terminal-bear"}`}
                style={{ width: `${dq.completeness ?? 0}%` }} />
            </div>
            <span className="text-[11px] font-mono text-terminal-muted">{dq.completeness ?? 0}% complete</span>
          </div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1 text-[11px]">
            {Object.entries(dq.checks || {}).map(([k, v]: [string, any]) => (
              <div key={k} className="flex justify-between gap-2">
                <span className="text-terminal-muted">{LABELS[k] ?? k}</span>
                <span className={`font-mono ${TONE[v.status] ?? ""}`}>{v.status}</span>
              </div>
            ))}
          </div>
        </>
      )}
    </section>
  );
}
