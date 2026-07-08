"use client";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useMarket } from "@/lib/store";

const TONE: Record<string, string> = {
  OK: "text-terminal-bull", CONNECTED: "text-terminal-bull", VALID: "text-terminal-bull", GOOD: "text-terminal-bull",
  STALE: "text-terminal-warn", DEGRADED: "text-terminal-warn", UNVERIFIED: "text-terminal-warn",
  IDLE: "text-terminal-muted", "NOT SET": "text-terminal-muted", UNKNOWN: "text-terminal-muted",
  DISCONNECTED: "text-terminal-bear", POOR: "text-terminal-bear",
};

function Row({ label, value, extra }: { label: string; value?: string | number | null; extra?: string }) {
  const v = String(value ?? "—");
  return (
    <div className="flex items-center justify-between border-t border-terminal-border/40 py-2.5 text-sm">
      <span className="text-terminal-muted">{label}</span>
      <span className={`font-mono ${TONE[v] ?? ""}`}>{v}{extra ? <span className="text-terminal-muted text-xs"> {extra}</span> : null}</span>
    </div>
  );
}

const gradeTone = (g?: string) =>
  g === "A+" || g === "A" ? "text-terminal-bull" : g === "B" ? "text-terminal-warn"
  : g === "BUILDING" ? "text-terminal-muted" : "text-terminal-bear";
const compTone = (s: number) =>
  s >= 80 ? "text-terminal-bull" : s >= 55 ? "text-terminal-warn" : "text-terminal-bear";

export default function HealthPage() {
  const { wsOk } = useMarket();
  const [h, setH] = useState<any>(null);
  const [dq, setDq] = useState<any>(null);
  const [hc, setHc] = useState<any>(null);
  const [pp, setPp] = useState<any>(null);

  useEffect(() => {
    const load = () => {
      api.systemHealth().then(setH).catch(() => setH(null));
      api.healthCenter().then(setHc).catch(() => setHc(null));
      api.healthPersistence().then(setPp).catch(() => setPp(null));
      fetch("/api/health/data", { headers: { "X-Auth-Token": localStorage.getItem("cat_token") || "" } })
        .then((r) => (r.ok ? r.json() : null)).then(setDq).catch(() => setDq(null));
    };
    load();
    const t = setInterval(load, 5000);
    return () => clearInterval(t);
  }, []);

  const eng = h?.engines ?? {};
  const bs = h?.broker_stability;
  return (
    <div className="max-w-lg mx-auto space-y-4">
      {/* System Health Center — composite grade */}
      {hc && (
        <section className="panel">
          <div className="flex items-center justify-between">
            <div className="panel-title mb-0">System Health Center</div>
            <div className={`text-3xl font-bold ${gradeTone(hc.overall_grade)}`}>{hc.overall_grade}</div>
          </div>
          <div className="text-xs text-terminal-muted mb-2">Overall {hc.overall_score}/100</div>
          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5">
            {Object.entries(hc.components || {}).map(([k, v]: [string, any]) => (
              <div key={k} className="flex items-center justify-between text-xs">
                <span className="text-terminal-muted capitalize">{k.replace(/_/g, " ")}</span>
                <span className={`font-mono ${compTone(v.score)}`}>{v.score}</span>
              </div>
            ))}
          </div>
          {hc.production && (
            <div className="mt-3 pt-2 border-t border-terminal-border/40 grid grid-cols-2 gap-x-4 gap-y-1 text-xs">
              <div className="flex justify-between"><span className="text-terminal-muted">Execution Ready</span><span className={hc.production.execution_ready ? "text-terminal-bull" : "text-terminal-bear"}>{hc.production.execution_ready ? "YES" : "NO"}</span></div>
              <div className="flex justify-between"><span className="text-terminal-muted">Production Ready</span><span className={hc.production.production_ready ? "text-terminal-bull" : "text-terminal-warn"}>{hc.production.production_ready ? "YES" : "NO"}</span></div>
              <div className="flex justify-between"><span className="text-terminal-muted">Feed</span><span className="font-mono">{hc.production.feed_pct}%</span></div>
              <div className="flex justify-between"><span className="text-terminal-muted">Latency</span><span className="font-mono">{hc.production.latency_ms != null ? `${hc.production.latency_ms} ms` : "—"}</span></div>
              {hc.production.blockers?.length > 0 && (
                <div className="col-span-2 text-[11px] text-terminal-warn mt-1">Blockers: {hc.production.blockers.join(" · ")}</div>
              )}
            </div>
          )}
          <div className="text-[10px] text-terminal-muted mt-2">{hc.note}</div>
        </section>
      )}

      {/* Persistence status */}
      {pp && (
        <section className="panel">
          <div className="flex items-center justify-between">
            <div className="panel-title mb-0">Persistence</div>
            <span className={`text-sm font-bold ${pp.persistence_status === "ACTIVE" ? "text-terminal-bull" : "text-terminal-warn"}`}>
              {pp.persistence_status} · {pp.database}
            </span>
          </div>
          {pp.tables_active?.length > 0 && (
            <div className="text-[11px] text-terminal-bull mt-1">Tables active: {pp.tables_active.join(", ")}</div>
          )}
          <div className="text-[11px] text-terminal-muted mt-1">
            Outcomes loaded: {pp.rows_loaded?.outcomes_rehydrated ?? pp.rows_loaded?.outcomes_in_memory ?? 0}
            {" · "}learning {pp.learning_active ? "active" : "idle"}
          </div>
          {pp.steps && (
            <ol className="text-[11px] text-terminal-muted mt-2 space-y-0.5 list-decimal list-inside">
              {pp.steps.map((s: string, i: number) => <li key={i}>{s.replace(/^\d+\.\s*/, "")}</li>)}
            </ol>
          )}
        </section>
      )}

      <section className="panel">
        <div className="panel-title">System Health</div>
        <Row label="Broker Status" value={h?.broker} />
        <Row label="WebSocket (this browser)" value={wsOk ? "OK" : "DISCONNECTED"} />
        <Row label="Dashboard Clients" value={h?.websocket_clients} />
        <Row label="Token Status" value={h?.token} />
        <Row label="Data Quality" value={h?.data_quality} />
        <Row label="Database" value={h?.database} />
        <Row label="Data Delay" value={h?.data_delay_sec != null ? `${h.data_delay_sec}s` : "—"} />
      </section>
      <section className="panel">
        <div className="panel-title">Engines</div>
        <Row label="Spot Feed (3s)" value={eng.spot_feed?.status} extra={eng.spot_feed?.last_run_sec != null ? `${eng.spot_feed.last_run_sec}s ago` : ""} />
        <Row label="Option Chain (15s)" value={eng.option_chain?.status} extra={eng.option_chain?.last_run_sec != null ? `${eng.option_chain.last_run_sec}s ago` : ""} />
        <Row label="Greeks Engine (15s)" value={eng.greeks?.status} extra={eng.greeks?.last_run_sec != null ? `${eng.greeks.last_run_sec}s ago` : ""} />
        <Row label="Signal Engine (3m)" value={eng.signal_engine?.status} extra={eng.signal_engine?.last_run_sec != null ? `${eng.signal_engine.last_run_sec}s ago` : ""} />
        <Row label="Trade Scanner (60s)" value={eng.scanner?.status} extra={eng.scanner?.last_run_sec != null ? `${eng.scanner.last_run_sec}s ago` : ""} />
        <Row label="Stock Universe" value={eng.stock_universe?.status} />
        <Row label="Market Memory" value={h?.memory_samples != null ? `${h.memory_samples} snapshots` : "—"} />
        <Row label="Candle Cache" value={h?.cache?.candle_entries != null ? `${h.cache.candle_entries} entries` : "—"} />
      </section>

      {bs && (
        <section className="panel">
          <div className="panel-title">Broker Stability Layer</div>
          <Row label="Health Score" value={`${bs.health_score}/100`} />
          <Row label="Request Rate" value={`${bs.requests_per_min}/${bs.budget_per_min} per min`} />
          <Row label="API Utilization" value={`${bs.utilization_pct}%`} />
          <Row label="Avg Latency" value={bs.avg_latency_ms != null ? `${bs.avg_latency_ms}ms` : "—"} />
          <Row label="Request Gap" value={`${bs.current_gap_ms}ms`} />
          <Row label="429 Events" value={bs.rate_limit_events} />
          <Row label="Cooldown" value={bs.cooldown_active ? `${bs.cooldown_remaining_sec}s remaining` : "OK"} />
          <Row label="Total Requests" value={bs.total_requests} />
        </section>
      )}

      {dq && (
        <section className="panel">
          <div className="panel-title">Data Quality Engine — overall: <span className={TONE[dq.overall] ?? ""}>{dq.overall}</span></div>
          {Object.entries(dq.checks || {}).map(([k, v]: [string, any]) => (
            <Row key={k} label={k.replace(/_/g, " ")} value={v.status} extra={v.detail} />
          ))}
        </section>
      )}
    </div>
  );
}
