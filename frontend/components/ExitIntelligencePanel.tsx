"use client";
// Exit Intelligence + Trade Management (display only). Shows the locked plan,
// partial-booking steps, exit decision, reversal-probability curve, profit-
// booking zone, S/R strength, re-entry and probability-weighted targets.
// Probabilities only — never predicts exact tops/bottoms.

import { useMarket } from "@/lib/store";

const fmt = (n?: number | null, d = 1) =>
  n === undefined || n === null ? "—" : n.toLocaleString("en-IN", { maximumFractionDigits: d });

const ACTION_TONE: Record<string, string> = {
  "EARLY EXIT": "text-terminal-bear border-terminal-bear/60 bg-terminal-bear/15",
  "FINAL EXIT": "text-terminal-bear border-terminal-bear/60 bg-terminal-bear/15",
  TRAIL: "text-terminal-accent border-terminal-accent/50 bg-terminal-accent/10",
  HOLD: "text-terminal-bull border-terminal-bull/50 bg-terminal-bull/10",
};

function revTone(p?: number) {
  if (p == null) return "text-terminal-muted";
  return p >= 70 ? "text-terminal-bear" : p >= 45 ? "text-terminal-warn" : "text-terminal-bull";
}
const revLabel = (p?: number) => (p == null ? "—" : p >= 80 ? "Very High" : p >= 60 ? "High" : p >= 40 ? "Moderate" : "Low");

export function ExitIntelligencePanel() {
  const { exitIntel: e } = useMarket();
  if (!e || !e.active) return null;     // only while a trade is live

  const L = e.locked_levels || {};
  const rev = e.reversal_probability || {};
  const z = e.profit_booking_zone || {};
  const sr = e.support_resistance || {};
  const tm = e.trade_management || {};

  return (
    <section className="panel border border-terminal-accent/30">
      <div className="panel-title flex items-center justify-between">
        <span>Exit Intelligence · Trade Management</span>
        <span className={`px-2.5 py-1 rounded-lg border text-sm font-bold ${ACTION_TONE[e.recommended_action] ?? "text-terminal-muted border-terminal-border"}`}>
          {e.recommended_action}
        </span>
      </div>

      {/* final exit decision */}
      <div className="flex flex-wrap items-baseline gap-4 mb-3">
        <span><span className="stat-label mr-1">Exit Score</span><span className="font-mono font-bold">{fmt(e.exit_score, 0)}%</span></span>
        <span><span className="stat-label mr-1">Confidence</span><span className="font-mono">{fmt(e.exit_confidence, 0)}%</span></span>
        <span><span className="stat-label mr-1">Momentum</span><span className="font-mono">{fmt(e.momentum_strength, 0)}</span></span>
        <span className="text-xs text-terminal-muted ml-auto">{e.reason}</span>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        {/* locked plan + partial booking */}
        <div>
          <div className="stat-label mb-1">Locked Plan (never changes)</div>
          <div className="grid grid-cols-5 gap-1 text-[11px] font-mono">
            <Lvl k="Entry" v={L.entry} tone="text-terminal-accent" />
            <Lvl k="SL" v={L.stop} tone="text-terminal-bear" />
            <Lvl k="T1" v={L.t1} tone="text-terminal-bull" />
            <Lvl k="T2" v={L.t2} tone="text-terminal-bull" />
            <Lvl k="T3" v={L.t3} tone="text-terminal-bull" />
          </div>
          <div className="mt-2 text-[11px]">
            <span className="text-terminal-muted">Next step: </span>
            <span className="font-semibold">{e.partial_plan?.action}</span>
            <span className="text-terminal-muted"> · SL: {e.partial_plan?.sl}</span>
          </div>
          <div className="grid grid-cols-3 gap-2 mt-2 text-[11px]">
            <Kv k="Position" v={tm.position} />
            <Kv k="Risk Left" v={tm.risk_remaining != null ? `${fmt(tm.risk_remaining)} pts` : "—"} />
            <Kv k="Profit Locked" v={tm.profit_locked} />
          </div>
        </div>

        {/* reversal curve + booking zone */}
        <div>
          <div className="stat-label mb-1">Reversal Probability</div>
          <div className="grid grid-cols-4 gap-1 text-center text-[11px]">
            <Rev k="Now" v={rev.current} />
            <Rev k="@T1" v={rev.near_t1} />
            <Rev k="@T2" v={rev.near_t2} />
            <Rev k="@T3" v={rev.near_t3} />
          </div>
          <div className="mt-2 text-[11px]">
            <div className="stat-label">Profit-Booking Zone {z.strength ? `· ${z.strength}%` : ""}</div>
            {z.zone ? (
              <div className="font-mono">{fmt(z.zone[0])} – {fmt(z.zone[1])} <span className="text-terminal-muted">({z.reason})</span></div>
            ) : <div className="text-terminal-muted">None ahead</div>}
          </div>
          <div className="grid grid-cols-2 gap-2 mt-2 text-[11px]">
            <Kv k={`Support ${sr.support_strength ?? "—"}%`} v={fmt(sr.support)} />
            <Kv k={`Resist ${sr.resistance_strength ?? "—"}%`} v={fmt(sr.resistance)} />
            <Kv k="Break Prob" v={`${fmt(sr.break_probability, 0)}%`} />
            <Kv k="Reject Prob" v={`${fmt(sr.reject_probability, 0)}%`} />
          </div>
        </div>
      </div>

      {/* probability-weighted target projection */}
      {Array.isArray(e.target_projection) && e.target_projection.length > 0 && (
        <div className="mt-3 pt-2 border-t border-terminal-border/50 flex flex-wrap gap-x-5 gap-y-1 text-[11px]">
          <span className="stat-label">Target Projection</span>
          {e.target_projection.map((t: any, i: number) => (
            <span key={i} className="font-mono">Zone {i + 1}: {fmt(t.zone)} <span className="text-terminal-bull">{fmt(t.probability, 0)}%</span></span>
          ))}
        </div>
      )}

      {/* re-entry (after T1) */}
      {e.re_entry?.pullback_zone && (
        <div className="mt-2 text-[11px]">
          <span className="stat-label mr-1">Re-entry</span>
          <span className="font-mono">{fmt(e.re_entry.pullback_zone[0])} – {fmt(e.re_entry.pullback_zone[1])}</span>
          <span className="text-terminal-muted"> · conf {fmt(e.re_entry.confidence, 0)}% · risk {e.re_entry.risk}</span>
        </div>
      )}
    </section>
  );
}

function Lvl({ k, v, tone }: { k: string; v?: number | null; tone?: string }) {
  return <div className="text-center"><div className="stat-label">{k}</div><div className={tone}>{fmt(v)}</div></div>;
}
function Kv({ k, v }: { k: string; v: React.ReactNode }) {
  return <div className="flex justify-between gap-1"><span className="text-terminal-muted">{k}</span><span className="font-mono">{v}</span></div>;
}
function Rev({ k, v }: { k: string; v?: number }) {
  return <div><div className="stat-label">{k}</div><div className={`font-mono font-bold ${revTone(v)}`}>{v ?? "—"}%</div><div className={`text-[8px] ${revTone(v)}`}>{revLabel(v)}</div></div>;
}
