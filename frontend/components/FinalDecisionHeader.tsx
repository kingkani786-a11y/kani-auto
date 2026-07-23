"use client";
// Single authoritative Final Decision — one status (🟢 BUY / ⚫ EXIT / 🟡 WAIT)
// + one-line reason, at the very top. Consolidates the many decision messages
// into ONE (reduces decision time). Derives from the execution gate (the
// authoritative verdict) — no new logic.

import { useMarket } from "@/lib/store";
import { displayReason } from "@/lib/labels";

export function FinalDecisionHeader() {
  const { decision, exitIntel } = useMarket();
  const d: any = decision || {};
  const gate = d.execution_gate;
  const ec = d.entry_checklist || {};
  if (!gate?.ready) return null;

  const exiting = (exitIntel as any)?.active &&
    ["FULL EXIT", "EXIT", "PARTIAL EXIT"].includes((exitIntel as any)?.recommended_action);

  let status: string, emoji: string, tone: string, reason: string;
  const fd = gate.final_decision;

  if (exiting) {
    emoji = "⚫"; status = (exitIntel as any).recommended_action; tone = "text-terminal-bear border-terminal-bear/60 bg-terminal-bear/10";
    reason = (exitIntel as any).reason || "Exit conditions met";
  } else if (fd === "BUY CALL" || fd === "BUY PUT") {
    emoji = "🟢"; status = fd; tone = "text-terminal-bull border-terminal-bull/60 bg-terminal-bull/10";
    reason = `All mandatory layers confirmed · ${ec.passed ?? "—"}/${ec.total ?? "—"} · quality gate PASS`;
  } else {
    emoji = "🟡"; status = "WAIT"; tone = "text-terminal-warn border-terminal-warn/50 bg-terminal-warn/5";
    reason = displayReason(gate.blocking_reasons && gate.blocking_reasons[0])
      || `Institutional confirmation pending (${ec.passed ?? 0}/${ec.total ?? 0} layers)`;
  }

  const isBuy = fd === "BUY CALL" || fd === "BUY PUT";
  const conf = d.intelligence_synthesis?.conviction ?? d.confidence;
  const strike = d.execution_card?.card?.strike || d.entry_zone?.strike;
  const fmt = (n?: number | null) => (n == null ? "—" : Number(n).toLocaleString("en-IN"));
  // countdown + top confirmed layers (the "why" in 3 words)
  const winSec = d.signal_maturity?.entry_trigger?.window_remaining_sec;
  const timeLeft = winSec == null ? null : winSec <= 0 ? "EXPIRED" : `${Math.floor(winSec / 60)}m ${winSec % 60}s`;
  const passLayers = (ec.checklist || []).filter((c: any) => c.status === "PASS")
    .slice(0, 3).map((c: any) => c.item).join(" + ");

  return (
    <div className={`panel border-2 ${tone} py-4`}>
      <div className="flex items-baseline gap-4 flex-wrap">
        <span className="text-3xl font-black tracking-wider">{emoji} {status}</span>
        {isBuy && strike && <span className="text-xl font-mono font-bold">{strike}</span>}
        {isBuy && conf != null && <span className="text-base font-mono">Conf {conf}%</span>}
        {isBuy && timeLeft && (
          <span className={`text-base font-mono ${timeLeft === "EXPIRED" ? "text-terminal-bear" : ""}`}>⏱ {timeLeft}</span>
        )}
      </div>
      <div className="text-sm text-gray-200 mt-1">{reason}</div>
      {/* Hero: entry / SL / targets inline when it's an actionable BUY */}
      {isBuy && (d.entry || d.stop_loss) && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3 mt-3 text-base">
          <div><div className="stat-label">Entry</div><div className="font-mono font-bold">{fmt(d.entry)}</div></div>
          <div><div className="stat-label">Stop</div><div className="font-mono font-bold text-terminal-bear">{fmt(d.stop_loss)}</div></div>
          <div><div className="stat-label">T1</div><div className="font-mono text-terminal-bull">{fmt(d.target1)}</div></div>
          <div><div className="stat-label">T2 / T3</div><div className="font-mono text-terminal-bull">{fmt(d.target2)} / {fmt(d.target3)}</div></div>
          <div><div className="stat-label">Reason</div><div className="text-xs pt-1">{passLayers || "—"}</div></div>
        </div>
      )}
    </div>
  );
}
