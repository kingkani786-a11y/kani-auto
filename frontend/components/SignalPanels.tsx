"use client";
// AI Signal panel, AI Explanation panel, and Risk dashboard.

import { useMarket } from "@/lib/store";

const fmt = (n?: number | null, d = 2) =>
  n === undefined || n === null ? "—" : n.toLocaleString("en-IN", { maximumFractionDigits: d });

const SIGNAL_TONE: Record<string, string> = {
  "BUY CE": "text-terminal-bull border-terminal-bull/50 bg-terminal-bull/10",
  "BUY FUTURES": "text-terminal-bull border-terminal-bull/50 bg-terminal-bull/10",
  "BUY PE": "text-terminal-bear border-terminal-bear/50 bg-terminal-bear/10",
  "SELL FUTURES": "text-terminal-bear border-terminal-bear/50 bg-terminal-bear/10",
  "NO TRADE": "text-terminal-muted border-terminal-border bg-terminal-bg",
};

const GRADE_TONE: Record<string, string> = {
  A: "bg-terminal-bull text-black",
  B: "bg-terminal-accent text-black",
  C: "bg-terminal-warn text-black",
};

const LIFECYCLE_ORDER = ["SETUP", "WATCH", "ARMED", "TRIGGERED", "ENTRY", "TARGET", "EXIT"];

export function SignalPanel() {
  const { signal, lifecycle } = useMarket();
  const tone = SIGNAL_TONE[signal?.signal ?? "NO TRADE"] ?? SIGNAL_TONE["NO TRADE"];
  return (
    <section className="panel">
      <div className="panel-title">AI Signal</div>
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <div className={`inline-block px-4 py-2 rounded-lg border text-lg font-bold font-mono ${tone}`}>
          {signal?.signal ?? "AWAITING DATA"}
        </div>
        {signal?.grade && signal.grade !== "NO TRADE" && (
          <span className={`px-2.5 py-1.5 rounded-lg text-sm font-bold ${GRADE_TONE[signal.grade] ?? "bg-terminal-border"}`}
            title={signal.grade_notes?.[0] ?? ""}>
            {signal.grade} GRADE
          </span>
        )}
      </div>
      {/* lifecycle strip */}
      <div className="flex items-center gap-1 mb-4 overflow-x-auto">
        {LIFECYCLE_ORDER.map((s) => (
          <span key={s}
            className={`px-1.5 py-0.5 rounded text-[9px] font-mono tracking-wide ${
              lifecycle?.state === s
                ? "bg-terminal-accent text-black font-bold"
                : "text-terminal-muted border border-terminal-border/60"
            }`}>
            {s}
          </span>
        ))}
      </div>
      {lifecycle && (lifecycle.trigger_price || lifecycle.invalidation_price) && (
        <div className="grid grid-cols-2 gap-x-4 gap-y-2 mb-4 text-sm">
          <div><div className="stat-label">{lifecycle.direction === "BEAR" ? "Breakdown Trigger" : "Breakout Trigger"}</div>
            <div className="stat-value text-terminal-accent">{fmt(lifecycle.trigger_price)}</div></div>
          <div><div className="stat-label">Invalidation</div>
            <div className="stat-value text-terminal-bear">{fmt(lifecycle.invalidation_price)}</div></div>
        </div>
      )}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-3 text-sm">
        <div><div className="stat-label">Entry</div><div className="stat-value">{fmt(signal?.entry)}</div></div>
        <div><div className="stat-label">Stop Loss</div><div className="stat-value text-terminal-bear">{fmt(signal?.stop_loss)}</div></div>
        <div><div className="stat-label">Target 1</div><div className="stat-value text-terminal-bull">{fmt(signal?.target1)}</div></div>
        <div><div className="stat-label">Target 2</div><div className="stat-value text-terminal-bull">{fmt(signal?.target2)}</div></div>
        <div><div className="stat-label">Target 3</div><div className="stat-value text-terminal-bull">{fmt(signal?.target3)}</div></div>
        <div><div className="stat-label">Confidence</div><div className="stat-value">{signal ? `${signal.confidence}%` : "—"}</div></div>
        <div><div className="stat-label">Reward : Risk</div><div className="stat-value">{signal?.reward_risk ? `${signal.reward_risk} : 1` : "—"}</div></div>
        <div><div className="stat-label">Bull / Bear Score</div>
          <div className="stat-value">
            <span className="text-terminal-bull">{fmt(signal?.bull_score, 0)}</span>
            {" / "}
            <span className="text-terminal-bear">{fmt(signal?.bear_score, 0)}</span>
          </div>
        </div>
      </div>
      {/* Dynamic Confidence Engine — composed, components shown separately */}
      {signal?.confidence_components && (
        <div className="mt-4 pt-3 border-t border-terminal-border/50">
          <div className="flex items-baseline justify-between mb-2">
            <span className="stat-label">Dynamic Confidence</span>
            <span className="font-mono text-sm font-bold">{signal.dynamic_confidence ?? "—"}%</span>
          </div>
          <div className="space-y-1.5">
            {Object.entries(signal.confidence_components).map(([k, v]) => (
              <div key={k} className="flex items-center gap-2 text-[10px]">
                <span className="w-32 text-terminal-muted capitalize">{k.replace(/_/g, " ")}</span>
                <div className="flex-1 h-1.5 rounded bg-terminal-bg overflow-hidden">
                  <div className="h-full bg-terminal-accent/70" style={{ width: `${v ?? 0}%` }} />
                </div>
                <span className="w-9 text-right font-mono">{v ?? "—"}</span>
              </div>
            ))}
          </div>
          {signal.effective_threshold != null && (
            <div className="text-[10px] text-terminal-muted mt-2">
              Adaptive bar: <span className="text-terminal-warn font-bold">{signal.effective_threshold}%</span> — {signal.threshold_reason}
            </div>
          )}
        </div>
      )}
      {signal?.factors && (
        <div className="mt-4 space-y-1.5">
          {Object.entries(signal.factors.bull).map(([k, bullV]) => {
            const bearV = signal.factors!.bear[k] ?? 0;
            return (
              <div key={k} className="flex items-center gap-2 text-[10px]">
                <span className="w-14 uppercase text-terminal-muted">{k}</span>
                <div className="flex-1 h-1.5 rounded bg-terminal-bg overflow-hidden flex">
                  <div className="bg-terminal-bull" style={{ width: `${bullV / 2}%` }} />
                  <div className="flex-1" />
                  <div className="bg-terminal-bear" style={{ width: `${bearV / 2}%` }} />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </section>
  );
}

export function ExplanationPanel() {
  const { signal } = useMarket();
  return (
    <section className="panel">
      <div className="panel-title">AI Explanation</div>
      {!signal?.reasons?.length ? (
        <p className="text-sm text-terminal-muted">The engine explains every signal here once analysis runs.</p>
      ) : (
        <ul className="space-y-2 text-sm">
          {signal.reasons.map((r, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-terminal-accent">▸</span>
              <span>{r}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}

const RISK_TONE: Record<string, string> = {
  LOW: "text-terminal-bull",
  MEDIUM: "text-terminal-warn",
  HIGH: "text-terminal-bear",
  NONE: "text-terminal-muted",
};

export function RiskPanel() {
  const { risk } = useMarket();
  return (
    <section className="panel">
      <div className="panel-title">Risk Dashboard</div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-3 text-sm">
        <div>
          <div className="stat-label">Risk Level</div>
          <div className={`stat-value font-bold ${RISK_TONE[risk?.risk_level ?? "NONE"]}`}>{risk?.risk_level ?? "—"}</div>
        </div>
        <div><div className="stat-label">Confidence</div><div className="stat-value">{risk ? `${risk.confidence}%` : "—"}</div></div>
        <div><div className="stat-label">Trend Strength</div><div className="stat-value">{risk?.trend_strength ?? "—"} {risk ? `(ADX ${risk.adx})` : ""}</div></div>
        <div><div className="stat-label">Volatility</div><div className="stat-value">{risk?.volatility ?? "—"} {risk ? `(${risk.atr_pct}% ATR)` : ""}</div></div>
      </div>
      {!!risk?.warnings?.length && (
        <div className="mt-4 space-y-1.5">
          {risk.warnings.map((w, i) => (
            <div key={i} className="text-xs text-terminal-warn flex gap-1.5">
              <span>⚠</span><span>{w}</span>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
