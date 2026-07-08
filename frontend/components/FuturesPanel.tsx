"use client";
// V13.1 Futures Intelligence Panel — confirmation layer (display only). Same
// visual language as the rest of the terminal. Never affects the decision.

import { useMarket } from "@/lib/store";

const biasTone = (b?: string) =>
  b === "BULLISH" ? "text-terminal-bull" : b === "BEARISH" ? "text-terminal-bear" :
  b === "MIXED" ? "text-terminal-warn" : "text-terminal-muted";

function confTone(s?: number) {
  if (s === undefined) return "text-terminal-muted";
  if (s >= 76) return "text-terminal-bull";
  if (s >= 51) return "text-terminal-accent";
  if (s >= 26) return "text-terminal-warn";
  return "text-terminal-bear";
}

export function FuturesPanel() {
  const { layers } = useMarket();
  const f = (layers as any)?.futures;

  return (
    <section className="panel">
      <div className="panel-title flex items-center justify-between">
        <span>Futures Intelligence</span>
        <span className="text-[9px] text-terminal-muted normal-case tracking-normal">confirmation layer</span>
      </div>
      {!f ? (
        <p className="text-sm text-terminal-muted">Futures confirmation lands with the first analysis cycle.</p>
      ) : (
        <>
          <div className="flex items-baseline gap-3 mb-3">
            <div>
              <div className="stat-label">Futures Bias</div>
              <div className={`text-xl font-bold ${biasTone(f.futures_bias)}`}>{f.futures_bias}</div>
            </div>
            <div className="ml-auto text-right">
              <div className="stat-label">Confirmation</div>
              <div className={`text-2xl font-black font-mono ${confTone(f.confirmation_score)}`}>
                {f.confirmation_score}%
              </div>
              <div className={`text-[10px] font-bold ${confTone(f.confirmation_score)}`}>{f.confirmation_label}</div>
            </div>
          </div>
          {f.relation && (
            <div className={`text-xs font-semibold mb-3 ${
              f.relation === "CONFIRMS" ? "text-terminal-bull" :
              f.relation === "CONTRADICTS" ? "text-terminal-bear" : "text-terminal-muted"}`}>
              Futures {f.relation.toLowerCase()} the current signal
            </div>
          )}
          <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-[11px]">
            <Row k="Futures Trend" v={f.futures_trend} />
            <Row k="OI Trend" v={f.oi_trend} />
            <Row k="Build-Up" v={f.buildup} />
            <Row k="Volume Trend" v={f.volume_trend} />
            <Row k="OI Change" v={`${f.oi_change_pct >= 0 ? "+" : ""}${f.oi_change_pct}%`} />
            <Row k="Cost of Carry" v={f.cost_of_carry_label} />
          </div>
        </>
      )}
    </section>
  );
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex justify-between gap-2">
      <span className="text-terminal-muted">{k}</span>
      <span className="font-mono text-right">{v ?? "—"}</span>
    </div>
  );
}
