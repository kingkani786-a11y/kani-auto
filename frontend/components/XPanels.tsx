"use client";
// Cloud AI Trader X panels: 10-layer confluence, strike reco, narrator, early warning.

import { useMarket } from "@/lib/store";
import type { LayerScore } from "@/lib/types";

const fmt = (n?: number | null, d = 2) =>
  n === undefined || n === null ? "—" : n.toLocaleString("en-IN", { maximumFractionDigits: d });

const LAYER_LABELS: [string, string][] = [
  ["trend", "Trend"],
  ["structure", "Structure"],
  ["oi", "Option Chain"],
  ["smart_money", "Smart Money"],
  ["greeks", "Greeks"],
  ["volume_profile", "Vol Profile"],
  ["mtf", "Multi-TF"],
];

function dirColor(d?: string) {
  return d === "BULL" ? "text-terminal-bull" : d === "BEAR" ? "text-terminal-bear" : "text-terminal-muted";
}

export function LayersPanel() {
  const { layers, signal } = useMarket();
  const hasData = !!layers.trend;
  return (
    <section className="panel">
      <div className="panel-title">Confluence — 10 Layer Confirmation</div>
      {!hasData ? (
        <p className="text-sm text-terminal-muted">Layer scores arrive with the first AI cycle (~15s after connect).</p>
      ) : (
        <>
          <div className="space-y-2">
            {LAYER_LABELS.map(([key, label]) => {
              const l = (layers as Record<string, LayerScore | undefined>)[key];
              const bull = Number(l?.score_bull ?? 50);
              const bear = Number(l?.score_bear ?? 50);
              const confirmed = signal?.confirmations?.includes(key);
              return (
                <div key={key} className="flex items-center gap-2 text-[11px]">
                  <span className={`w-20 shrink-0 ${confirmed ? "text-white font-semibold" : "text-terminal-muted"}`}>
                    {label}{confirmed ? " ✓" : ""}
                  </span>
                  <div className="flex-1 h-2 rounded bg-terminal-bg overflow-hidden flex">
                    <div className="bg-terminal-bull/80" style={{ width: `${bull / 2}%` }} />
                    <div className="flex-1" />
                    <div className="bg-terminal-bear/80" style={{ width: `${bear / 2}%` }} />
                  </div>
                  <span className={`w-12 text-right font-mono ${dirColor(l?.direction)}`}>
                    {l?.direction ?? "—"}
                  </span>
                </div>
              );
            })}
          </div>
          <div className="grid grid-cols-3 gap-3 mt-4 text-sm">
            <div>
              <div className="stat-label">Regime</div>
              <div className="stat-value">{String(layers.regime?.regime ?? "—").replace(/_/g, " ")}</div>
            </div>
            <div>
              <div className="stat-label">MTF Alignment</div>
              <div className="stat-value">{fmt(layers.mtf?.alignment, 0)}%</div>
            </div>
            <div>
              <div className="stat-label">Prob. of Success</div>
              <div className="stat-value">{fmt(layers.probability?.prob_success, 1)}%</div>
            </div>
            <div className="col-span-3">
              <div className="stat-label">Expected Range</div>
              <div className="stat-value">
                {layers.probability?.expected_range
                  ? `${fmt(layers.probability.expected_range[0], 0)} – ${fmt(layers.probability.expected_range[1], 0)} (±${fmt(layers.probability.expected_move, 0)})`
                  : "—"}
              </div>
            </div>
          </div>
          {layers.mtf?.frames && (
            <div className="flex flex-wrap gap-1.5 mt-3">
              {Object.entries(layers.mtf.frames).map(([tf, t]) => (
                <span key={tf} className={`px-2 py-0.5 rounded text-[10px] font-mono border border-terminal-border ${dirColor(String(t))}`}>
                  {tf} {String(t)}
                </span>
              ))}
            </div>
          )}
          {!!signal?.vetoes?.length && (
            <div className="mt-3 space-y-1">
              {signal.vetoes.slice(0, 4).map((v: string, i: number) => (
                <div key={i} className="text-[11px] text-terminal-warn">✕ {v}</div>
              ))}
            </div>
          )}
        </>
      )}
    </section>
  );
}

export function StrikePanel() {
  const { strike, strikes, status } = useMarket();
  if (status?.market_type === "COMMODITY") return null;
  return (
    <section className="panel">
      <div className="panel-title">Strike Engine — Top {Math.max(strikes.length, 1)} Ranked</div>
      {!strike ? (
        <p className="text-sm text-terminal-muted">Populates when a BUY CE / BUY PE signal fires.</p>
      ) : (
        <>
          <div className={`text-xl font-mono font-bold mb-3 ${strike.type === "CE" ? "text-terminal-bull" : "text-terminal-bear"}`}>
            {fmt(strike.strike, 0)} {strike.type}
          </div>
          <div className="grid grid-cols-2 sm:grid-cols-3 gap-x-4 gap-y-3 text-sm">
            <div><div className="stat-label">Premium Entry</div><div className="stat-value">{fmt(strike.premium_entry)}</div></div>
            <div><div className="stat-label">Premium SL</div><div className="stat-value text-terminal-bear">{fmt(strike.premium_stop_loss)}</div></div>
            <div><div className="stat-label">Target 1</div><div className="stat-value text-terminal-bull">{fmt(strike.premium_target1)}</div></div>
            <div><div className="stat-label">Target 2</div><div className="stat-value text-terminal-bull">{fmt(strike.premium_target2)}</div></div>
            <div><div className="stat-label">Target 3</div><div className="stat-value text-terminal-bull">{fmt(strike.premium_target3)}</div></div>
            <div><div className="stat-label">Delta</div><div className="stat-value">{fmt(strike.delta, 3)}</div></div>
            <div><div className="stat-label">IV</div><div className="stat-value">{fmt(strike.iv, 1)}%</div></div>
            <div><div className="stat-label">Spread</div><div className="stat-value">{fmt(strike.spread_pct, 2)}%</div></div>
            <div><div className="stat-label">Selection Score</div><div className="stat-value">{fmt(strike.selection_score, 0)}/100</div></div>
          </div>
          {strikes.length > 1 && (
            <table className="w-full text-[10px] font-mono mt-4 whitespace-nowrap">
              <thead>
                <tr className="stat-label text-left">
                  <th className="pb-1 pr-2 font-normal">#</th>
                  <th className="pb-1 pr-2 font-normal">Strike</th>
                  <th className="pb-1 pr-2 font-normal">Prem</th>
                  <th className="pb-1 pr-2 font-normal">Δ</th>
                  <th className="pb-1 pr-2 font-normal">P(ITM)</th>
                  <th className="pb-1 font-normal">Score</th>
                </tr>
              </thead>
              <tbody>
                {strikes.map((s, i) => (
                  <tr key={s.strike} className={`border-t border-terminal-border/40 ${i === 0 ? "text-terminal-accent" : ""}`}>
                    <td className="py-1 pr-2">{i + 1}</td>
                    <td className="pr-2">{fmt(s.strike, 0)} {s.type}</td>
                    <td className="pr-2">{fmt(s.premium_entry)}</td>
                    <td className="pr-2">{fmt(s.delta, 2)}</td>
                    <td className="pr-2">{fmt((s as any).prob_itm_pct, 0)}%</td>
                    <td>{fmt(s.selection_score, 0)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </>
      )}
    </section>
  );
}

export function NarratorPanel() {
  const { narrative, coach } = useMarket();
  return (
    <section className="panel">
      <div className="panel-title">AI Market Narrator</div>
      {narrative.length === 0 ? (
        <p className="text-sm text-terminal-muted">The narrator explains the tape in plain language after each AI cycle.</p>
      ) : (
        <div className="space-y-2 text-sm leading-relaxed">
          {narrative.map((line, i) => (
            <p key={i} className={i === narrative.length - 1 ? "text-white font-medium" : "text-gray-300"}>
              {line}
            </p>
          ))}
        </div>
      )}
      {coach.length > 0 && (
        <div className="mt-4 pt-3 border-t border-terminal-border/50">
          <div className="stat-label mb-2">AI Market Coach</div>
          <ul className="space-y-1.5 text-xs text-gray-300">
            {coach.map((c, i) => (
              <li key={i} className="flex gap-2">
                <span className="text-terminal-warn shrink-0">◆</span>
                <span>{c}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </section>
  );
}

export function EarlyWarningPanel() {
  const { warning } = useMarket();
  if (!warning || warning.setup === "NONE") return null;
  const bull = warning.setup === "BULLISH_FORMING";
  return (
    <section className={`panel border ${bull ? "border-terminal-bull/40" : "border-terminal-bear/40"}`}>
      <div className="panel-title">Early Warning</div>
      <div className={`text-lg font-bold font-mono mb-2 ${bull ? "text-terminal-bull" : "text-terminal-bear"}`}>
        {bull ? "BULLISH SETUP FORMING" : "BEARISH SETUP FORMING"}
      </div>
      <div className="grid grid-cols-2 gap-3 text-sm mb-3">
        <div><div className="stat-label">Preparation</div><div className="stat-value">{warning.preparation}%</div></div>
        <div><div className="stat-label">Setup Confidence</div><div className="stat-value">{warning.confidence}%</div></div>
      </div>
      <ul className="text-xs text-terminal-muted space-y-1">
        {warning.notes.map((n, i) => (<li key={i}>▸ {n}</li>))}
      </ul>
    </section>
  );
}
