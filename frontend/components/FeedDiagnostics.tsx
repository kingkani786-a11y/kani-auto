"use client";
// V1.0 P2/P6 — Feed Diagnostics. Per-feed PASS/WAIT/FAIL + completeness %, so
// the trader instantly knows whether WAIT is caused by MARKET or by DATA.
// Reads the existing /api/health/data report; shows compact strip when healthy,
// expands detail when any feed is degraded.

import { useEffect, useState } from "react";
import { useMarket } from "@/lib/store";

const tone = (s: string) =>
  s === "OK" ? "text-terminal-bull" : s === "N/A" ? "text-terminal-muted"
  : s === "DEGRADED" || s === "DELAYED" ? "text-terminal-warn" : "text-terminal-bear";

export function FeedDiagnostics() {
  const [d, setD] = useState<any>(null);
  const { status } = useMarket();

  useEffect(() => {
    const load = () =>
      fetch("/api/health/data", { headers: { "X-Auth-Token": localStorage.getItem("cat_token") || "" } })
        .then((r) => (r.ok ? r.json() : null)).then(setD).catch(() => {});
    load();
    const t = setInterval(load, 10000);
    return () => clearInterval(t);
  }, []);

  if (!d?.checks) return null;
  const entries = Object.entries(d.checks) as [string, any][];
  // RC1.11 — market-closed consistency fix: MISSING feeds before/after hours
  // are a PAUSE, not a failure (same doctrine as AI Self-Check's WAIT vs FAIL
  // and the amber MarketStatusBanner — a closed market must never read as a
  // red data-quality alarm).
  const marketClosed = (status as any)?.market_open === false;
  const failing = entries.filter(([, c]) => !["OK", "N/A"].includes(c.status)
    && !(marketClosed && c.status === "MISSING"));
  // RC1.4 — the authoritative pipeline quality (kill-switch source) overrides:
  // never claim "healthy" while the system itself is running on POOR data
  const pipelinePoor = (status as any)?.data_quality === "POOR";
  const healthy = failing.length === 0 && !pipelinePoor;
  const comp = d.completeness ?? 0;
  // no option chain for this instrument ⇒ OI/Greeks/Institutional stay neutral
  // and the full entry gate can never arm — that WAIT is structural, not market
  const noChain = d.checks.option_chain?.status === "N/A";

  if (marketClosed && failing.length === 0 && !pipelinePoor) {
    return (
      <div className="panel py-2 text-[11px]">
        <span className="font-bold tracking-wider text-terminal-accent">FEED 🟡 PAUSED</span>
        <span className="text-terminal-muted ml-2">Market closed — feeds resume automatically at open. Not a data problem.</span>
      </div>
    );
  }

  return (
    <div className={`panel py-2 ${healthy ? "" : "border-terminal-warn/50"}`}>
      <div className="flex items-center justify-between flex-wrap gap-2 text-[11px]">
        <span className="font-bold tracking-wider text-terminal-accent">
          FEED {comp >= 90 ? "🟢" : comp >= 60 ? "🟡" : "🔴"} {comp}%
        </span>
        <span className="text-terminal-muted">
          {pipelinePoor
            ? <span className="text-terminal-bear">Pipeline data quality POOR (broker cooldown / feed issue) — WAIT is data-driven; kill switch governs.</span>
            : !healthy
            ? <>Top failing: <span className="text-terminal-bear">{failing[0][0]} ({failing[0][1].status})</span> — WAIT may be data-driven</>
            : noChain
            ? <>Feeds healthy. <span className="text-terminal-warn">No option chain for this instrument — OI / Greeks / Institutional stay neutral, so the full entry gate cannot arm. Scalp Radar is the applicable engine here.</span></>
            : "All feeds healthy — any WAIT is market-driven, not data."}
        </span>
      </div>
      {!healthy && (
        <div className="flex flex-wrap gap-x-4 gap-y-1 mt-1.5 text-[11px]">
          {entries.map(([name, c]) => (
            <span key={name}>
              <span className="text-terminal-muted">{name}:</span>{" "}
              <span className={marketClosed && c.status === "MISSING" ? "text-terminal-muted" : tone(c.status)}>{c.status}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
