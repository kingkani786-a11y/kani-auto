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
  // RC1.11 — market-closed consistency fix: MISSING or DELAYED feeds
  // before/after hours are a PAUSE, not a failure (same doctrine as AI
  // Self-Check's WAIT vs FAIL and the amber MarketStatusBanner — a closed
  // market must never read as a red data-quality alarm). DELAYED is just
  // as expected as MISSING here: a quote/signal that arrived DURING the
  // last session and simply hasn't updated since the market closed ages
  // past its own DELAYED threshold exactly like an ordinary paused feed —
  // it isn't stale in the sense that word implies elsewhere. Previously
  // only MISSING was exempted, so the same closed-market condition showed
  // the calm "PAUSED" message right after a restart (state empty ->
  // MISSING) but flipped to the alarming itemized red view a few minutes
  // later once those same values aged into DELAYED — an inconsistent
  // display of one honestly-unchanged situation.
  const marketClosed = (status as any)?.market_open === false;
  const failing = entries.filter(([, c]) => !["OK", "N/A"].includes(c.status)
    && !(marketClosed && (c.status === "MISSING" || c.status === "DELAYED")));
  // RC1.4 — the authoritative pipeline quality (kill-switch source) overrides:
  // never claim "healthy" while the system itself is running on POOR data.
  //
  // 2026-08-03 fix: this read `status.data_quality`, which is NOT the
  // kill-switch source despite the comment above. There are two unrelated
  // "data quality" values in this system:
  //   A) state.data_quality  — set by market_service._safe()'s try/except,
  //      i.e. "did the last tick raise a BrokerError?". This is what
  //      `status.data_quality` carries.
  //   B) data_quality.report().overall — the 8 per-stream freshness checks.
  //      THIS is what kill_switch.evaluate() and safe_mode.evaluate() are
  //      actually handed (market_service.py `dq = report()["overall"]`).
  // A can be GOOD while B is POOR, and on 2026-08-03 it was: the dashboard
  // showed "All feeds healthy — any WAIT is market-driven, not data" while
  // Execution Lock was blocking every trade *because of* data quality. On a
  // trading surface a contradiction like that is worse than a wrong number —
  // it makes the engine look broken when the engine is behaving correctly.
  //
  // `d` is /api/health/data, which returns report() verbatim, so B was
  // already fetched here and simply never read. Both are ORed: this guard's
  // only job is to never *falsely* claim healthy, so either source saying
  // POOR must suppress the healthy message. It can be conservative; it must
  // not be optimistic.
  //
  // Residual, deliberately not addressed here: B is sampled by the engine
  // every 180s (_ai_cycle) but polled here every 10s, so this panel can turn
  // red up to ~3min before the Kill Switch acts on the same value. That gap
  // is a separate open question (OBS-9, parked — see docs/V7_STATUS.md) and
  // must be proven with a real timeline before any interval is changed.
  // Note the direction of the residual: this panel leads, the gate lags, so
  // the panel can warn early but never falsely reassure — which is the side
  // to err on.
  const pipelinePoor = d.overall === "POOR"
    || (status as any)?.data_quality === "POOR";
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
            ? <>Feeds healthy. <span className="text-terminal-warn">No option chain for this instrument — OI / Greeks / Institutional stay neutral, so the full entry gate cannot arm.</span></>
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
