"use client";
// Institutional Command Center (V7.5 M10) — one unified intelligence view
// assembled from the platform's existing engines.

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import { useMarket } from "@/lib/store";

const fmt = (n?: number | null, d = 1) =>
  n === undefined || n === null ? "—" : n.toLocaleString("en-IN", { maximumFractionDigits: d });

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="panel">
      <div className="panel-title">{title}</div>
      {children}
    </section>
  );
}

function Kv({ k, v, tone }: { k: string; v: React.ReactNode; tone?: string }) {
  return (
    <div className="flex justify-between items-baseline py-1 border-t border-terminal-border/30 text-sm">
      <span className="text-terminal-muted text-xs">{k}</span>
      <span className={`font-mono ${tone ?? ""}`}>{v}</span>
    </div>
  );
}

const bullBear = (s?: string) =>
  s === "BULLISH" || s === "BULL" ? "text-terminal-bull" :
  s === "BEARISH" || s === "BEAR" ? "text-terminal-bear" : "text-terminal-muted";

export default function CommandCenter() {
  const router = useRouter();
  const { status, signal, layers, risk, smartMoney, scanRows, alerts } = useMarket();
  const [breadth, setBreadth] = useState<any>(null);
  const [learning, setLearning] = useState<any>(null);
  const [health, setHealth] = useState<any>(null);
  const [pf, setPf] = useState<any>(null);

  useEffect(() => {
    const load = () => {
      api.breadth().then(setBreadth).catch(() => {});
      api.learning().then(setLearning).catch(() => {});
      api.systemHealth().then(setHealth).catch(() => {});
      api.portfolioRisk().then(setPf).catch(() => {});
    };
    load();
    const t = setInterval(load, 20000);
    return () => clearInterval(t);
  }, []);

  const prob = layers.probability as any;
  const regime = layers.regime as any;
  const of = (layers as any).order_flow;
  const audit = (signal as any)?.audit;
  const bs = health?.broker_stability;

  return (
    <div className="space-y-4">
      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card title="Market Regime">
          <div className="text-lg font-mono font-bold mb-1">
            {String(regime?.regime ?? "—").replace(/_/g, " ")}
          </div>
          <div className="flex flex-wrap gap-1 mb-2">
            {(regime?.phases ?? []).map((p: string) => (
              <span key={p} className="px-1.5 py-0.5 rounded bg-terminal-bg border border-terminal-border text-[9px] font-mono text-terminal-accent">
                {p.replace(/_/g, " ")}
              </span>
            ))}
          </div>
          <Kv k="Quality Score" v={fmt(regime?.score, 0)} />
          <Kv k="MTF Alignment" v={`${fmt(layers.mtf?.alignment, 0)}%`} />
        </Card>

        <Card title="Probability Lab">
          <Kv k="P(Success)" v={`${fmt(prob?.prob_success)}%`} tone="text-terminal-bull" />
          <Kv k="P(Failure)" v={`${fmt(prob?.prob_failure)}%`} tone="text-terminal-bear" />
          <Kv k="Expected Value" v={`${fmt(prob?.expected_value)} pts`}
            tone={(prob?.expected_value ?? 0) >= 0 ? "text-terminal-bull" : "text-terminal-bear"} />
          <Kv k="Expected Reward" v={`${fmt(prob?.expected_reward)} pts`} />
          <Kv k="Expected Drawdown" v={`${fmt(prob?.expected_drawdown)} pts`} />
          <Kv k="Hist. / Regime Acc." v={prob?.historical_accuracy != null ? `${prob.historical_accuracy}%` : "learning…"} />
        </Card>

        <Card title="Smart Money & Order Flow">
          <Kv k="Bias" v={smartMoney?.bias ?? "—"} tone={bullBear(smartMoney?.bias)} />
          <Kv k="Order Flow Score" v={fmt(of?.score, 0)}
            tone={(of?.score ?? 50) > 55 ? "text-terminal-bull" : (of?.score ?? 50) < 45 ? "text-terminal-bear" : ""} />
          <Kv k="Delta Imbalance" v={fmt(of?.delta_imbalance, 2)} />
          <div className="flex flex-wrap gap-1 mt-2">
            {[...(smartMoney?.activities ?? []), ...((of?.events ?? []) as string[])].slice(0, 4).map((a) => (
              <span key={a} className="px-1.5 py-0.5 rounded bg-terminal-bg border border-terminal-border text-[9px] font-mono">
                {a.replace(/_/g, " ")}
              </span>
            ))}
          </div>
        </Card>

        <Card title="Risk & Portfolio Heat">
          <Kv k="Risk Level" v={risk?.risk_level ?? "—"}
            tone={risk?.risk_level === "LOW" ? "text-terminal-bull" : risk?.risk_level === "HIGH" ? "text-terminal-bear" : "text-terminal-warn"} />
          <Kv k="Portfolio Heat" v={`${fmt(pf?.portfolio_heat_pct, 0)}%`}
            tone={(pf?.portfolio_heat_pct ?? 0) > 70 ? "text-terminal-bear" : ""} />
          <Kv k="Correlation Risk" v={`${fmt(pf?.correlation_risk_pct, 0)}%`} />
          <Kv k="Concentration" v={`${fmt(pf?.concentration_pct, 0)}%`} />
          <Kv k="Capital Efficiency" v={`${fmt(pf?.capital_efficiency_pct, 2)}%`} />
        </Card>
      </div>

      <div className="grid sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <Card title="Market Breadth">
          {breadth ? (
            <>
              <Kv k="Advances / Declines" v={`${breadth.advances} / ${breadth.declines}`} />
              <Kv k="A/D Ratio" v={breadth.ratio ?? "—"} />
              <Kv k="New Highs / Lows" v={`${breadth.new_highs} / ${breadth.new_lows}`} />
              <Kv k="Bias" v={breadth.bias ?? "—"} tone={bullBear(breadth.bias)} />
            </>
          ) : <p className="text-xs text-terminal-muted">Loading…</p>}
        </Card>

        <Card title="Self-Learning Memory">
          {learning ? (
            <>
              <Kv k="Outcomes Tracked" v={learning.samples} />
              <Kv k="Overall Accuracy" v={learning.overall_accuracy != null ? `${learning.overall_accuracy}%` : "—"} />
              {Object.entries(learning.by_regime || {}).slice(0, 3).map(([r, v]: [string, any]) => (
                <Kv key={r} k={r.replace(/_/g, " ")} v={`${v.accuracy}% (${v.n})`}
                  tone={v.accuracy >= 60 ? "text-terminal-bull" : "text-terminal-bear"} />
              ))}
            </>
          ) : <p className="text-xs text-terminal-muted">Loading…</p>}
        </Card>

        <Card title="Broker Stability">
          {bs ? (
            <>
              <Kv k="Health Score" v={fmt(bs.health_score, 0)}
                tone={bs.health_score >= 80 ? "text-terminal-bull" : bs.health_score >= 50 ? "text-terminal-warn" : "text-terminal-bear"} />
              <Kv k="Req / Min" v={`${bs.requests_per_min} / ${bs.budget_per_min}`} />
              <Kv k="API Utilization" v={`${bs.utilization_pct}%`} />
              <Kv k="Avg Latency" v={bs.avg_latency_ms != null ? `${bs.avg_latency_ms}ms` : "—"} />
              <Kv k="429 Events" v={bs.rate_limit_events} tone={bs.rate_limit_events ? "text-terminal-warn" : ""} />
              <Kv k="Cooldown" v={bs.cooldown_active ? `${bs.cooldown_remaining_sec}s` : "inactive"}
                tone={bs.cooldown_active ? "text-terminal-bear" : "text-terminal-bull"} />
            </>
          ) : <p className="text-xs text-terminal-muted">Loading…</p>}
        </Card>

        <Card title="AI Decision Audit">
          {audit ? (
            <>
              <Kv k="Signal Generated" v={audit.generated ? "YES" : "NO TRADE"}
                tone={audit.generated ? "text-terminal-bull" : "text-terminal-muted"} />
              <Kv k="Confirmed" v={(audit.confirmed_layers || []).length ? audit.confirmed_layers.join(", ") : "—"} />
              <Kv k="Failed" v={(audit.failed_layers || []).length ? audit.failed_layers.join(", ") : "none"}
                tone={(audit.failed_layers || []).length ? "text-terminal-warn" : "text-terminal-bull"} />
              <Kv k="Probability" v={`${fmt(audit.probability_score)}%`} />
              <Kv k="Threshold" v={`${fmt(audit.effective_threshold)}%`} />
            </>
          ) : <p className="text-xs text-terminal-muted">Audit arrives with the first AI cycle.</p>}
        </Card>
      </div>

      <div className="grid lg:grid-cols-2 gap-4">
        <Card title="Top Opportunities (Scanner)">
          {scanRows.length === 0 ? (
            <p className="text-xs text-terminal-muted">{status?.connected ? "First scan lands within a minute." : "Connect to start scanning."}</p>
          ) : (
            <table className="w-full text-xs font-mono whitespace-nowrap">
              <thead><tr className="stat-label text-left">
                {["Symbol", "Chg%", "Prob", "Risk", "Score", ""].map((h) => (
                  <th key={h} className="pb-1.5 pr-3 font-normal">{h}</th>))}
              </tr></thead>
              <tbody>
                {scanRows.slice(0, 6).map((r) => (
                  <tr key={r.symbol} className="border-t border-terminal-border/40">
                    <td className="py-1 pr-3 font-bold">{r.symbol}</td>
                    <td className={`pr-3 ${r.change_pct >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>
                      {r.change_pct >= 0 ? "+" : ""}{r.change_pct}%</td>
                    <td className="pr-3">{(r as any).probability_pct ?? "—"}%</td>
                    <td className="pr-3">{(r as any).risk_score ?? "—"}</td>
                    <td className="pr-3">{r.score}</td>
                    <td><button onClick={() => api.setSymbol(r.symbol).then(() => router.push("/")).catch(() => {})}
                      className="px-2 py-0.5 rounded border border-terminal-border text-[10px] hover:border-terminal-accent">GO</button></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>

        <Card title="Latest Alerts">
          {alerts.length === 0 ? (
            <p className="text-xs text-terminal-muted">Lifecycle, scanner and anomaly alerts stream here.</p>
          ) : (
            <div className="space-y-1.5 max-h-56 overflow-y-auto">
              {alerts.slice(0, 8).map((a) => (
                <div key={a.id} className="flex gap-2 text-xs border-t border-terminal-border/30 pt-1.5">
                  <span className="font-bold text-terminal-accent shrink-0 w-14">{a.kind}</span>
                  <span className="truncate">{a.title}</span>
                  <span className="ml-auto text-terminal-muted shrink-0">{a.ts.slice(11, 16)}</span>
                </div>
              ))}
            </div>
          )}
        </Card>
      </div>
    </div>
  );
}
