"use client";
// V28 — 🧠 AI TRADE MANAGEMENT (Trading mode). Appears ONLY while a trade is
// live: exit score band, ONE management action, partial plan, re-entry engine
// with the safety rule ("NO RE-ENTRY — trend weakening"), and the full trade
// cycle timeline. Reads existing exit_intel — display only.

import { useMarket } from "@/lib/store";

const CYCLE = ["BUY", "RUNNING", "PARTIAL EXIT", "PULLBACK", "RE-ENTRY", "FINAL EXIT"];

export function TradeManagement() {
  const { exitIntel, spot, signal } = useMarket();
  const x: any = exitIntel;
  if (!x?.active) return null;

  const lv = x.locked_levels || {};
  const ltp = (spot as any)?.ltp;
  // RC1.5 fix — P/L sign comes from the TRADE's locked direction, never from
  // the live signal (which reads NONE/WATCH mid-trade and flipped the sign)
  const dir = (x.direction || (x.trade_management?.position || "").split(" ")[0] || (signal as any)?.direction || "").toUpperCase();
  const pnl = ltp != null && lv.entry != null
    ? (dir === "BEAR" ? lv.entry - ltp : ltp - lv.entry) : null;

  const stage =
    x.recommended_action === "FINAL EXIT" ? "FINAL EXIT"
    : x.re_entry?.status === "READY" ? "RE-ENTRY"
    : x.re_entry ? "PULLBACK"
    : (x.trade_management?.targets_hit ?? 0) >= 1 ? "PARTIAL EXIT"
    : "RUNNING";

  const actTone = x.recommended_action === "HOLD" ? "text-terminal-bull"
    : x.recommended_action === "FINAL EXIT" ? "text-terminal-bear" : "text-terminal-warn";
  const es = Number(x.exit_score ?? 0);

  return (
    <div className="panel border border-terminal-accent/40 py-3">
      <div className="flex items-center justify-between flex-wrap gap-2 mb-2">
        <span className="font-bold tracking-wider text-terminal-accent">🧠 AI TRADE MANAGEMENT</span>
        <span className="px-2 py-0.5 rounded text-[11px] font-bold bg-terminal-bull text-black">🟢 RUNNING</span>
      </div>

      {/* position + pnl (underlying points — advisory system tracks levels, not fills) */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-2 text-[12px]">
        <div><div className="stat-label">Entry</div><div className="font-mono font-bold">{lv.entry ?? "—"}</div></div>
        <div><div className="stat-label">Now</div><div className="font-mono">{ltp ?? "—"}</div></div>
        <div><div className="stat-label">P/L (pts)</div>
          <div className={`font-mono font-bold ${pnl != null && pnl >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>
            {pnl != null ? `${pnl >= 0 ? "+" : ""}${pnl.toFixed(1)}` : "—"}</div></div>
        <div><div className="stat-label">Stop</div><div className="font-mono text-terminal-bear">{x.trade_management?.trailing_stop ?? lv.stop ?? "—"}</div></div>
      </div>

      {/* ONE management action + exit score band */}
      <div className="flex items-center gap-3 mb-2">
        <span className={`text-xl font-black ${actTone}`}>▶ {x.recommended_action}</span>
        <span className="text-[11px] text-terminal-muted">{x.reason}</span>
      </div>
      <div className="flex items-center gap-3 mb-2">
        <span className="stat-label w-20">Exit Score</span>
        <div className="flex-1 h-2.5 rounded-full bg-terminal-bg overflow-hidden">
          <div className={`h-full ${es >= 85 ? "bg-terminal-bear" : es >= 65 ? "bg-orange-500" : "bg-terminal-bull"}`}
            style={{ width: `${es}%` }} />
        </div>
        <span className="font-mono text-sm">{es}</span>
        <span className="text-[11px] font-bold">{x.exit_band}</span>
      </div>
      {x.partial_plan && (
        <div className="text-[12px] mb-2">
          <span className="stat-label mr-2">Plan</span>{x.partial_plan.action}
          <span className="text-terminal-muted"> · SL: {x.partial_plan.sl}</span>
        </div>
      )}

      {/* V28 re-entry engine — safety rule visible */}
      {x.re_entry && (
        <div className={`rounded-md border px-2 py-1.5 mb-2 text-[12px] ${
          x.re_entry.status === "NO RE-ENTRY" ? "border-terminal-bear/50"
          : x.re_entry.status === "READY" ? "border-terminal-bull/60" : "border-terminal-warn/40"}`}>
          <span className={`font-bold ${
            x.re_entry.status === "NO RE-ENTRY" ? "text-terminal-bear"
            : x.re_entry.status === "READY" ? "text-terminal-bull" : "text-terminal-warn"}`}>
            {x.re_entry.status === "READY" ? "🟢 RE-ENTRY READY" : x.re_entry.status}
          </span>
          {x.re_entry.reason ? <span className="text-terminal-muted"> — {x.re_entry.reason}</span> : null}
          {x.re_entry.pullback_zone ? (
            <span className="font-mono"> · zone {x.re_entry.pullback_zone[0]}–{x.re_entry.pullback_zone[1]}</span>
          ) : null}
          {x.re_entry.reentry_score != null ? (
            <span className="text-terminal-muted"> · score <span className="font-mono text-gray-200">{x.re_entry.reentry_score}</span> · risk {x.re_entry.risk}</span>
          ) : null}
        </div>
      )}

      {/* V29 — cycle forecast: what the AI expects next (forecast, not schedule) */}
      {x.cycle_forecast && (
        <div className="rounded-md border border-terminal-accent/30 px-2 py-1.5 mb-2 text-[12px]">
          <span className="stat-label mr-2">Next expected</span>
          <span className="font-bold text-terminal-accent">{x.cycle_forecast.next_action}</span>
          <span className="font-mono"> · {x.cycle_forecast.probability}%</span>
          <span className="text-terminal-muted"> · ~{x.cycle_forecast.time_band} (indicative)</span>
          {x.cycle_forecast.reentry_outlook && (
            <span className={`ml-2 font-bold ${
              x.cycle_forecast.reentry_outlook.state === "GREEN" ? "text-terminal-bull"
              : x.cycle_forecast.reentry_outlook.state === "RED" ? "text-terminal-bear" : "text-terminal-warn"}`}>
              {x.cycle_forecast.reentry_outlook.state === "GREEN" ? "🟢" : x.cycle_forecast.reentry_outlook.state === "RED" ? "🔴" : "🟡"} {x.cycle_forecast.reentry_outlook.label}
            </span>
          )}
          {(x.cycle_forecast.reasons || []).length > 0 && (
            <div className="text-[11px] text-terminal-muted mt-0.5">{x.cycle_forecast.reasons.join(" · ")}</div>
          )}
          {(x.cycle_forecast.chain || []).length > 0 && (
            <div className="text-[11px] mt-1">
              {x.cycle_forecast.chain.map((s: any, i: number) => (
                <span key={i}>
                  <span className="text-gray-200">{s.step}</span>
                  {s.probability != null ? <span className="font-mono text-terminal-muted"> {s.probability}%</span> : null}
                  {i < x.cycle_forecast.chain.length - 1 ? <span className="text-terminal-muted/50"> → </span> : null}
                </span>
              ))}
            </div>
          )}
          <div className="text-[10px] text-terminal-muted/70 italic mt-0.5">{x.cycle_forecast.note}</div>
        </div>
      )}

      {/* trade cycle timeline */}
      <div className="text-[11px]">
        {CYCLE.map((s, i) => (
          <span key={s}>
            <span className={s === stage ? "font-bold text-terminal-accent" : "text-terminal-muted/60"}>{s}</span>
            {i < CYCLE.length - 1 ? <span className="text-terminal-muted/40"> → </span> : null}
          </span>
        ))}
      </div>
    </div>
  );
}
