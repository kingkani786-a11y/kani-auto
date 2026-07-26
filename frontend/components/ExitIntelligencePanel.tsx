"use client";
// Exit Intelligence + Trade Management (display only). Shows the locked plan,
// partial-booking steps, exit decision, reversal-probability curve, profit-
// booking zone, S/R strength, re-entry and probability-weighted targets.
// Probabilities only — never predicts exact tops/bottoms.
//
// Includes the action-layer merged from TradeManagement.tsx (2026-07-26
// Dashboard Cleanup Audit — both panels read store.exitIntel directly; the
// only content TradeManagement wasn't duplicating here was live P/L, the
// trailing stop, the re-entry safety-rule status, the cycle forecast, and the
// trade-cycle stage timeline — all folded in below).

import { useMarket } from "@/lib/store";

const fmt = (n?: number | null, d = 1) =>
  n === undefined || n === null ? "—" : n.toLocaleString("en-IN", { maximumFractionDigits: d });

const ACTION_TONE: Record<string, string> = {
  "EARLY EXIT": "text-terminal-bear border-terminal-bear/60 bg-terminal-bear/15",
  "FINAL EXIT": "text-terminal-bear border-terminal-bear/60 bg-terminal-bear/15",
  TRAIL: "text-terminal-accent border-terminal-accent/50 bg-terminal-accent/10",
  HOLD: "text-terminal-bull border-terminal-bull/50 bg-terminal-bull/10",
};

const CYCLE = ["BUY", "RUNNING", "PARTIAL EXIT", "PULLBACK", "RE-ENTRY", "FINAL EXIT"];

function revTone(p?: number) {
  if (p == null) return "text-terminal-muted";
  return p >= 70 ? "text-terminal-bear" : p >= 45 ? "text-terminal-warn" : "text-terminal-bull";
}
const revLabel = (p?: number) => (p == null ? "—" : p >= 80 ? "Very High" : p >= 60 ? "High" : p >= 40 ? "Moderate" : "Low");

export function ExitIntelligencePanel() {
  const { exitIntel: e, spot, signal } = useMarket();
  if (!e || !e.active) return null;     // only while a trade is live

  const L = e.locked_levels || {};
  const rev = e.reversal_probability || {};
  const z = e.profit_booking_zone || {};
  const sr = e.support_resistance || {};
  const tm = e.trade_management || {};

  const ltp = (spot as any)?.ltp;
  // RC1.5 fix — P/L sign comes from the TRADE's locked direction, never from
  // the live signal (which reads NONE/WATCH mid-trade and flipped the sign).
  const dir = ((e as any).direction || (tm.position || "").split(" ")[0] || (signal as any)?.direction || "").toUpperCase();
  const pnl = ltp != null && L.entry != null ? (dir === "BEAR" ? L.entry - ltp : ltp - L.entry) : null;

  const stage =
    e.recommended_action === "FINAL EXIT" ? "FINAL EXIT"
    : e.re_entry?.status === "READY" ? "RE-ENTRY"
    : e.re_entry ? "PULLBACK"
    : (tm.targets_hit ?? 0) >= 1 ? "PARTIAL EXIT"
    : "RUNNING";

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
        <span><span className="stat-label mr-1">Exit Score</span><span className="font-mono font-bold">{fmt(e.exit_score, 0)}%</span>{e.exit_band ? <span className="text-[11px] text-terminal-muted ml-1">{e.exit_band}</span> : null}</span>
        <span><span className="stat-label mr-1">Confidence</span><span className="font-mono">{fmt(e.exit_confidence, 0)}%</span></span>
        <span><span className="stat-label mr-1">Momentum</span><span className="font-mono">{fmt(e.momentum_strength, 0)}</span></span>
        <span><span className="stat-label mr-1">P/L (pts)</span>
          <span className={`font-mono font-bold ${pnl != null && pnl >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>
            {pnl != null ? `${pnl >= 0 ? "+" : ""}${pnl.toFixed(1)}` : "—"}</span></span>
        <span className="text-xs text-terminal-muted ml-auto">{e.reason}</span>
      </div>

      <div className="grid sm:grid-cols-2 gap-4">
        {/* locked plan + partial booking */}
        <div>
          <div className="stat-label mb-1">Locked Plan (never changes)</div>
          <div className="grid grid-cols-5 gap-1 text-[11px] font-mono">
            <Lvl k="Entry" v={L.entry} tone="text-terminal-accent" />
            <Lvl k="SL" v={tm.trailing_stop ?? L.stop} tone="text-terminal-bear" />
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

      {/* re-entry engine — safety rule visible (merged from TradeManagement) */}
      {e.re_entry && (
        <div className={`mt-2 rounded-md border px-2 py-1.5 text-[12px] ${
          e.re_entry.status === "NO RE-ENTRY" ? "border-terminal-bear/50"
          : e.re_entry.status === "READY" ? "border-terminal-bull/60" : "border-terminal-warn/40"}`}>
          <span className={`font-bold ${
            e.re_entry.status === "NO RE-ENTRY" ? "text-terminal-bear"
            : e.re_entry.status === "READY" ? "text-terminal-bull" : "text-terminal-warn"}`}>
            {e.re_entry.status === "READY" ? "🟢 RE-ENTRY READY" : e.re_entry.status ?? "Re-entry"}
          </span>
          {e.re_entry.reason ? <span className="text-terminal-muted"> — {e.re_entry.reason}</span> : null}
          {e.re_entry.pullback_zone ? (
            <span className="font-mono"> · zone {fmt(e.re_entry.pullback_zone[0])}–{fmt(e.re_entry.pullback_zone[1])}</span>
          ) : null}
          {e.re_entry.confidence != null || e.re_entry.reentry_score != null ? (
            <span className="text-terminal-muted"> · {e.re_entry.confidence != null ? `conf ${fmt(e.re_entry.confidence, 0)}%` : `score ${e.re_entry.reentry_score}`} · risk {e.re_entry.risk}</span>
          ) : null}
        </div>
      )}

      {/* cycle forecast — what the AI expects next (merged from TradeManagement) */}
      {e.cycle_forecast && (
        <div className="mt-2 rounded-md border border-terminal-accent/30 px-2 py-1.5 text-[12px]">
          <span className="stat-label mr-2">Next expected</span>
          <span className="font-bold text-terminal-accent">{e.cycle_forecast.next_action}</span>
          <span className="font-mono"> · {e.cycle_forecast.probability}%</span>
          <span className="text-terminal-muted"> · ~{e.cycle_forecast.time_band} (indicative)</span>
          {e.cycle_forecast.reentry_outlook && (
            <span className={`ml-2 font-bold ${
              e.cycle_forecast.reentry_outlook.state === "GREEN" ? "text-terminal-bull"
              : e.cycle_forecast.reentry_outlook.state === "RED" ? "text-terminal-bear" : "text-terminal-warn"}`}>
              {e.cycle_forecast.reentry_outlook.state === "GREEN" ? "🟢" : e.cycle_forecast.reentry_outlook.state === "RED" ? "🔴" : "🟡"} {e.cycle_forecast.reentry_outlook.label}
            </span>
          )}
          {(e.cycle_forecast.reasons || []).length > 0 && (
            <div className="text-[11px] text-terminal-muted mt-0.5">{e.cycle_forecast.reasons.join(" · ")}</div>
          )}
          {(e.cycle_forecast.chain || []).length > 0 && (
            <div className="text-[11px] mt-1">
              {e.cycle_forecast.chain.map((s: any, i: number) => (
                <span key={i}>
                  <span className="text-gray-200">{s.step}</span>
                  {s.probability != null ? <span className="font-mono text-terminal-muted"> {s.probability}%</span> : null}
                  {i < e.cycle_forecast.chain.length - 1 ? <span className="text-terminal-muted/50"> → </span> : null}
                </span>
              ))}
            </div>
          )}
          <div className="text-[10px] text-terminal-muted/70 italic mt-0.5">{e.cycle_forecast.note}</div>
        </div>
      )}

      {/* trade cycle timeline (merged from TradeManagement) */}
      <div className="mt-2 pt-2 border-t border-terminal-border/30 text-[11px]">
        {CYCLE.map((s, i) => (
          <span key={s}>
            <span className={s === stage ? "font-bold text-terminal-accent" : "text-terminal-muted/60"}>{s}</span>
            {i < CYCLE.length - 1 ? <span className="text-terminal-muted/40"> → </span> : null}
          </span>
        ))}
      </div>
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
