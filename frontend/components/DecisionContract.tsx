"use client";
// 📜 DECISION CONTRACT — V2.1's unifier. One card, one language: the action,
// its WHY (Rule 11), invalidations and exit plan live together. BUY or WAIT,
// the contract always explains itself. Derived; the user executes manually.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function DecisionContract() {
  const [c, setC] = useState<any>(null);
  const [tick, setTick] = useState(0);          // 1s client tick for the countdown
  useEffect(() => {
    const load = () => { api.decisionContract().then((d) => { setC(d); setTick(0); }).catch(() => {}); };
    load();
    const id = setInterval(load, 5000);
    const t = setInterval(() => setTick((x) => x + 1), 1000);
    return () => { clearInterval(id); clearInterval(t); };
  }, []);
  if (!c) return null;

  const winLeft = c.entry_window_live?.seconds_left != null
    ? Math.max(0, c.entry_window_live.seconds_left - tick) : null;
  const winState = winLeft == null ? null : winLeft === 0 ? "CLOSED" : winLeft <= 30 ? "CLOSING" : "OPEN";

  const buy = c.is_trade;
  const head = buy
    ? { t: `🟢 ${c.action}`, cls: "text-terminal-bull border-terminal-bull/50 bg-terminal-bull/10" }
    : { t: `⏸ ${c.action || "WAIT"}`, cls: "text-terminal-warn border-terminal-warn/40 bg-terminal-warn/5" };

  return (
    <section className="panel space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white">📜 Decision Contract <span className="text-[10px] text-terminal-muted">(entry · hold · exit — one logic)</span></h2>
        <span className={`text-[12px] font-bold px-2 py-0.5 rounded border ${head.cls}`}>{head.t}</span>
      </div>

      {/* Rule 11 — explain before execute (BUY and WAIT alike) */}
      <div>
        <div className="text-[10px] font-semibold text-terminal-muted uppercase tracking-wide mb-0.5">{buy ? "Why buy" : "Why wait"}</div>
        <ul className="text-[11px] text-gray-200 space-y-0.5">
          {(c.why || []).map((w: string, i: number) => (
            <li key={i} className="flex gap-1.5"><span className={buy ? "text-terminal-bull" : "text-terminal-warn"}>▸</span>{w}</li>
          ))}
        </ul>
      </div>

      {/* Unified Entry Grade — ONE grade, not five scores */}
      {c.entry_grade?.score != null && (
        <div className="flex items-center gap-3 border-t border-terminal-border pt-2">
          <div className={`text-3xl font-bold ${
            ["A+","A"].includes(c.entry_grade.grade) ? "text-terminal-bull"
            : c.entry_grade.grade === "B" ? "text-terminal-warn" : "text-terminal-bear"}`}>
            {c.entry_grade.grade}
          </div>
          <div>
            <div className="text-sm font-semibold tabular-nums text-white">{c.entry_grade.score}/100</div>
            <div className="text-[10px] text-terminal-muted">Entry Grade — conviction {c.entry_grade.parts?.conviction ?? "—"} · signal {c.entry_grade.parts?.signal_confidence ?? "—"} · breadth {c.entry_grade.parts?.layer_breadth ?? "—"}</div>
          </div>
        </div>
      )}

      {/* Aging (Rule 9) + live Entry Window countdown (Rule 8) */}
      {(c.aging?.state || winLeft != null) && (
        <div className="flex flex-wrap items-center gap-2 text-[11px] border-t border-terminal-border pt-2">
          {c.aging?.state && (
            <span className={`px-1.5 py-0.5 rounded border ${
              c.aging.state === "Fresh" ? "text-terminal-bull border-terminal-bull/40"
              : c.aging.state === "STALE" ? "text-terminal-bear border-terminal-bear/40"
              : "text-terminal-warn border-terminal-warn/40"}`}>
              {c.aging.state}{c.aging.age_s != null ? ` · ${Math.floor(c.aging.age_s / 60)}m${c.aging.age_s % 60}s` : ""}
            </span>
          )}
          {c.aging?.aged_confidence != null && c.aging?.decay_pct > 0 && (
            <span className="text-terminal-muted">aged confidence <b className="text-white">{c.aging.aged_confidence}%</b> (−{c.aging.decay_pct}%)</span>
          )}
          {winLeft != null && (
            <span className={`ml-auto font-bold tabular-nums px-1.5 py-0.5 rounded border ${
              winState === "OPEN" ? "text-terminal-bull border-terminal-bull/40"
              : winState === "CLOSING" ? "text-terminal-warn border-terminal-warn/40 animate-pulse"
              : "text-terminal-bear border-terminal-bear/40"}`}>
              ⏳ Entry window {winState}{winLeft > 0 ? ` · ${winLeft}s` : ""}
            </span>
          )}
        </div>
      )}

      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 text-center border-t border-terminal-border pt-2">
        <div><div className="text-sm font-semibold tabular-nums text-white">{c.confidence ?? "—"}{typeof c.confidence === "number" ? "%" : ""}</div><div className="text-[9px] text-terminal-muted">Confidence</div></div>
        <div><div className="text-sm font-semibold tabular-nums text-white">{c.reward_risk ? `1:${c.reward_risk}` : "—"}</div><div className="text-[9px] text-terminal-muted">R:R</div></div>
        <div><div className="text-sm font-semibold text-white truncate" title={String(c.expected_move ?? "")}>{c.expected_move ?? "—"}</div><div className="text-[9px] text-terminal-muted">Expected move</div></div>
        <div><div className="text-sm font-semibold tabular-nums text-white">{c.entry ?? "—"}</div><div className="text-[9px] text-terminal-muted">Entry ref</div></div>
      </div>

      {/* Evidence Ledger — confidence decomposed (Rule 3) */}
      {c.ledger_total != null && (
        <div className="border-t border-terminal-border pt-2">
          <div className="text-[10px] font-semibold text-terminal-muted uppercase tracking-wide mb-1">Evidence ledger</div>
          <div className="space-y-0.5">
            {(c.ledger || []).map((e: any, i: number) => (
              <div key={i} className="flex items-center gap-2 text-[11px]">
                <span className="w-28 shrink-0 text-gray-200">{e.pillar}</span>
                <div className="flex-1 h-1.5 bg-terminal-border rounded overflow-hidden">
                  <div className={`h-full ${e.score == null ? "" : e.score >= 14 ? "bg-terminal-bull" : e.score >= 10 ? "bg-terminal-warn" : "bg-terminal-bear"}`}
                    style={{ width: `${e.score == null ? 0 : (e.score / 20) * 100}%` }} />
                </div>
                <span className="w-10 text-right tabular-nums text-terminal-muted">{e.score == null ? "—" : `${e.score}/20`}</span>
              </div>
            ))}
          </div>
          <div className="text-[11px] text-white text-right mt-0.5 tabular-nums">Total <b>{c.ledger_total}/100</b></div>
        </div>
      )}

      {/* Invalidations — the pre-stated contract terms */}
      <div className="border border-terminal-bear/30 rounded p-2">
        <div className="text-[10px] font-semibold text-terminal-bear uppercase tracking-wide mb-0.5">Invalidation — exit IF</div>
        <ul className="text-[11px] text-gray-200 space-y-0.5">
          {(c.invalidations || []).map((v: string, i: number) => (
            <li key={i} className="flex gap-1.5"><span className="text-terminal-bear">✕</span>{v}</li>
          ))}
        </ul>
        <div className="text-[10px] text-terminal-muted mt-1">{c.instruction}</div>
      </div>

      {buy && (
        <div className="text-[11px] text-terminal-muted">
          Exit plan: SL <b className="text-white">{c.exit_plan?.stop_loss ?? "—"}</b>
          {c.exit_plan?.target1 ? <> · T1 <b className="text-white">{c.exit_plan.target1}</b></> : null}
          {c.exit_plan?.trail ? <> · {c.exit_plan.trail}</> : null}
        </div>
      )}

      <div className="text-[10px] text-terminal-muted">{c.note}</div>
    </section>
  );
}
