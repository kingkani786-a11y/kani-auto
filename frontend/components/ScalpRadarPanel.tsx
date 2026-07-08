"use client";
// SCALP RADAR V3 — Execution Intelligence Suite (independent). Renders strike
// recommendation, premium entry/SL/targets, trade management, explainability,
// rejection / near-miss, quality analytics, and execution score. Display only.

import { useMarket } from "@/lib/store";

const fmt = (n?: number | null) =>
  n === undefined || n === null ? "—" : n.toLocaleString("en-IN", { maximumFractionDigits: 2 });

const STAGES = ["SIGNAL ACTIVE", "ENTRY HIT", "T1 HIT", "T2 HIT", "T3 HIT"];

export function ScalpRadarPanel() {
  const { scalp: s } = useMarket();
  const active = !!s?.active;
  const dir = s?.direction ?? "NONE";
  const score = s?.scalp_score ?? 0;
  const ex = s?.execution;
  const mg = s?.management;
  const an = s?.analytics;
  const tone = !active ? "border-terminal-border"
    : dir === "BULL" ? "border-terminal-bull/50" : "border-terminal-bear/50";

  return (
    <section className={`panel border ${tone}`}>
      <div className="panel-title flex items-center justify-between">
        <span>⚡ Scalp Radar V3 — Execution Suite</span>
        {s?.counter_trend
          ? <span className="text-[9px] text-terminal-warn normal-case tracking-normal font-bold">COUNTER-TREND · reduced confidence</span>
          : <span className="text-[9px] text-terminal-muted normal-case tracking-normal">independent · +5/+10/+15</span>}
      </div>

      {!s ? (
        <p className="text-sm text-terminal-muted">Scanning for fast scalps… (updates ~5s)</p>
      ) : (
        <div className="space-y-3">
          {/* headline: signal + score (Module 6 explainability) */}
          <div className="flex items-center gap-3">
            <div className={`px-3 py-1.5 rounded-lg border text-lg font-black font-mono ${
              !active ? "text-terminal-muted border-terminal-border bg-terminal-bg" :
              dir === "BULL" ? "text-terminal-bull border-terminal-bull/60 bg-terminal-bull/15"
                             : "text-terminal-bear border-terminal-bear/60 bg-terminal-bear/15"}`}>
              {s.signal}
            </div>
            <div className="ml-auto text-right">
              <div className="stat-label">Score / Threshold</div>
              <div className="font-mono text-sm">
                <span className={score >= 70 ? "text-terminal-bull font-bold" : score >= 65 ? "text-terminal-warn font-bold" : "text-terminal-muted"}>
                  {Math.round(score)}
                </span>
                <span className="text-terminal-muted"> / 70 · {s.status}</span>
              </div>
            </div>
          </div>

          {/* Module 1–4 + 10: strike recommendation & execution */}
          {active && ex && (
            <div className="rounded-lg border border-terminal-border/60 p-3 bg-terminal-bg/40">
              <div className="flex items-baseline gap-2 mb-2">
                <span className={`text-lg font-bold font-mono ${dir === "BULL" ? "text-terminal-bull" : "text-terminal-bear"}`}>
                  {fmt(ex.strike)} {ex.type}
                </span>
                <span className="text-xs text-terminal-muted">LTP {fmt(ex.option_ltp)} · Δ {ex.delta}</span>
                <span className="ml-auto text-xs">
                  <span className="text-terminal-muted">Exec </span>
                  <span className={ex.execution_score >= 75 ? "text-terminal-bull font-bold" : "text-terminal-warn font-bold"}>{ex.execution_score}%</span>
                </span>
              </div>
              <div className="grid grid-cols-3 gap-2 text-[11px] mb-2">
                <Kv k="Strike Quality" v={`${ex.strike_quality}%`} />
                <Kv k="Liquidity" v={ex.liquidity} />
                <Kv k="Spread" v={`${ex.spread} (${ex.spread_pct}%)`} />
              </div>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-[11px]">
                <Kv k="Entry (aggr)" v={fmt(ex.entry?.aggressive)} tone="text-terminal-accent" />
                <Kv k="Entry (cons)" v={fmt(ex.entry?.conservative)} />
                <Kv k="Trigger >" v={fmt(ex.entry?.trigger_above)} />
                <Kv k="Recommended SL" v={`${fmt(ex.stop?.recommended)} (-${fmt(ex.stop?.risk_points)})`} tone="text-terminal-bear" />
                <Kv k="T1" v={fmt(ex.targets?.t1)} tone="text-terminal-bull" />
                <Kv k="T2" v={fmt(ex.targets?.t2)} tone="text-terminal-bull" />
                <Kv k="T3" v={fmt(ex.targets?.t3)} tone="text-terminal-bull" />
                <Kv k="R:R · Hold" v={`${ex.reward_risk ?? "—"} · ${ex.targets?.holding ?? ""}`} />
              </div>
            </div>
          )}

          {/* Module 5: trade management progress */}
          {mg?.stage && mg.stage !== "IDLE" && (
            <div>
              <div className="stat-label mb-1">Trade Management — {mg.stage}</div>
              <div className="flex gap-1 flex-wrap">
                {STAGES.map((st) => {
                  const flags = mg.flags || {};
                  const hit = (st === "SIGNAL ACTIVE" && flags.signal_active) ||
                    (st === "ENTRY HIT" && flags.entry_hit) || (st === "T1 HIT" && flags.t1) ||
                    (st === "T2 HIT" && flags.t2) || (st === "T3 HIT" && flags.t3);
                  return (
                    <span key={st} className={`px-1.5 py-0.5 rounded text-[9px] font-mono ${
                      hit ? "bg-terminal-bull/20 text-terminal-bull" : "text-terminal-muted border border-terminal-border/60"}`}>
                      {st}
                    </span>
                  );
                })}
                {mg.flags?.sl_to_cost && <span className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-terminal-accent/20 text-terminal-accent">SL→COST</span>}
                {mg.flags?.trail && <span className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-terminal-accent/20 text-terminal-accent">TRAIL</span>}
                {mg.flags?.sl && <span className="px-1.5 py-0.5 rounded text-[9px] font-mono bg-terminal-bear/20 text-terminal-bear">SL HIT</span>}
              </div>
            </div>
          )}

          {/* Module 7/8: rejection / near-miss */}
          {s.rejection && (
            <div className="text-[11px] text-terminal-bear">
              ✕ Rejected: {s.rejection.primary}{s.rejection.secondary !== "—" ? ` · ${s.rejection.secondary}` : ""}
            </div>
          )}
          {s.near_miss && (
            <div className="text-[11px] text-terminal-warn">
              ◐ Near miss — need +{s.near_miss.need} · missing: {(s.near_miss.missing || []).join(", ")}
            </div>
          )}

          {/* Module 6: component breakdown */}
          {s.explain?.breakdown && (
            <div className="grid grid-cols-3 gap-x-3 gap-y-1 text-[10px]">
              {s.explain.breakdown.map((b: any) => (
                <div key={b.name} className="flex justify-between">
                  <span className="text-terminal-muted">{b.name}</span>
                  <span className={`font-mono ${b.favorable ? "text-terminal-bull" : "text-terminal-muted"}`}>{b.score}</span>
                </div>
              ))}
            </div>
          )}

          {/* Module 9: quality analytics */}
          {an && an.trades > 0 && (
            <div className="flex flex-wrap gap-x-5 gap-y-1 text-[11px] pt-1 border-t border-terminal-border/50">
              <span><span className="text-terminal-muted">Win Rate </span><span className="font-mono text-terminal-bull">{an.win_rate}%</span></span>
              <span><span className="text-terminal-muted">Avg R:R </span><span className="font-mono">1:{an.avg_rr ?? "—"}</span></span>
              <span><span className="text-terminal-muted">Scalps </span><span className="font-mono">{an.trades}</span></span>
            </div>
          )}
          {!active && !s.rejection && !s.near_miss && (
            <p className="text-xs text-terminal-muted">No scalp setup. Direction lean: {dir}.</p>
          )}
        </div>
      )}
    </section>
  );
}

function Kv({ k, v, tone }: { k: string; v: React.ReactNode; tone?: string }) {
  return (
    <div className="flex justify-between gap-1">
      <span className="text-terminal-muted">{k}</span>
      <span className={`font-mono ${tone ?? ""}`}>{v}</span>
    </div>
  );
}
