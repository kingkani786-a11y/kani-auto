"use client";
// 🔥 HOT NOW — action-first, the single top opportunity at the very top of the
// dashboard (owner: "Display first, Decision after"). Pure presentation of the
// premium_radar thinking() output: what's running, why, its lifecycle stage,
// miss-probability (late / early), confidence, and the pre-stated invalidation.
// Radar observes; the engine gate still decides trades.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const stars = (n: number) => "★".repeat(n) + "☆".repeat(5 - n);
const missTone: Record<string, string> = {
  early: "text-terminal-bull", mid: "text-terminal-warn", late: "text-terminal-bear",
};
const phaseTone: Record<string, string> = {
  BUILDING: "text-terminal-bull", RUNNER_BUILDING: "text-terminal-warn", RUNNER_CONFIRMED: "text-terminal-bear",
};

export function HotNow() {
  const [t, setT] = useState<any>(null);
  useEffect(() => {
    const load = () => api.premiumRadar(8).then((d: any) => setT(d?.thinking || null)).catch(() => {});
    load(); const id = setInterval(load, 3000); return () => clearInterval(id);
  }, []);

  if (!t) return null; // nothing running — stay quiet

  return (
    <section className="panel border-terminal-accent/40 space-y-1.5">
      <div className="flex items-center justify-between">
        <div className="flex items-baseline gap-2">
          <span className="text-sm font-bold text-white">🔥 HOT NOW</span>
          <span className="text-base font-bold text-white">{t.watching}</span>
          <span className="text-terminal-warn text-xs">{stars(t.stars)}</span>
        </div>
        <div className="text-right">
          <span className="text-lg font-bold tabular-nums">₹{t.premium}</span>
          <span className={`text-xs ml-1 tabular-nums ${t.rise_pct >= 0 ? "text-terminal-bull" : "text-terminal-bear"}`}>{t.rise_pct >= 0 ? "+" : ""}{t.rise_pct}%</span>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 text-xs">
        <span className={phaseTone[t.phase?.code] || ""}>{t.phase?.dot} {t.phase?.label}{t.phase?.action ? ` (${t.phase.action})` : ""}</span>
        <span className="text-terminal-muted">Runner <b className="text-white">{t.runner_score}</b> {t.runner_tag && <span className="font-semibold">{t.runner_tag.dot} {t.runner_tag.label}</span>}</span>
        <span className={`font-semibold ${missTone[t.miss?.tone] || ""}`}>⏱ {t.miss?.label}</span>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 text-[11px]">
        <div><span className="text-terminal-muted">Why: </span><span className="text-white">{t.cause}</span></div>
        <div><span className="text-terminal-muted">Timing: </span><span className="text-white">{t.miss?.detail}</span></div>
      </div>

      <div className="text-[11px] border border-terminal-bear/30 rounded px-2 py-1">
        <span className="text-terminal-bear font-semibold">Exit / wrong IF: </span>
        <span className="text-white">{t.invalidation?.conditions?.join(" · ")}</span>
      </div>

      <div className="text-[10px] text-terminal-muted">Action view · radar observes, the engine gate decides the trade · not a calibrated probability.</div>
    </section>
  );
}
