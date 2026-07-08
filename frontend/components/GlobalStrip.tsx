"use client";
// Global Market Context strip — OWNER-LOCKED: context only (±3 confidence),
// never a gate, never overrides Trend. Live when the (unofficial) feed
// responds; falls back to the honest "Waiting for Data Source" line.

import { useEffect, useState } from "react";

const ORDER = ["NQ=F", "ES=F", "CL=F", "GC=F", "DX-Y.NYB", "^VIX", "USDINR=X"];

export function GlobalStrip() {
  const [d, setD] = useState<any>(null);
  useEffect(() => {
    const load = () =>
      fetch("/api/global", { headers: { "X-Auth-Token": localStorage.getItem("cat_token") || "" } })
        .then((r) => (r.ok ? r.json() : null)).then(setD).catch(() => {});
    load();
    const t = setInterval(load, 60000);
    return () => clearInterval(t);
  }, []);

  if (!d?.available) {
    return (
      <div className="panel py-2 text-[11px] text-terminal-muted">
        🌐 Global Market Engine: <span className="text-terminal-warn">{d?.note || "Waiting for Data Source"}</span>
        {" · "}📰 News Intelligence: <span className="text-terminal-warn">News Feed Not Connected</span>
        {" — "}nothing is fabricated meanwhile.
      </div>
    );
  }
  return (
    <div className="panel py-2">
      <div className="flex items-center justify-between flex-wrap gap-2 text-[11px] mb-1">
        <span className="font-bold tracking-wider text-terminal-accent">🌐 GLOBAL CONTEXT</span>
        <span className={`font-bold ${d.risk_state === "RISK_ON" ? "text-terminal-bull"
          : d.risk_state === "RISK_OFF" ? "text-terminal-bear" : "text-terminal-muted"}`}>
          {d.risk_state.replace("_", "-")} · confidence {d.adjust > 0 ? "+" : ""}{d.adjust}
        </span>
      </div>
      <div className="flex flex-wrap gap-x-4 gap-y-1 text-[11px] font-mono">
        {ORDER.filter((s) => d.quotes[s]).map((s) => {
          const q = d.quotes[s];
          return (
            <span key={s}>
              <span className="text-terminal-muted">{q.name}</span>{" "}
              <span className={q.chg_pct > 0 ? "text-terminal-bull" : q.chg_pct < 0 ? "text-terminal-bear" : ""}>
                {q.chg_pct > 0 ? "+" : ""}{q.chg_pct}%
              </span>
            </span>
          );
        })}
      </div>
      {(d.reasons || []).length > 0 && (
        <div className="text-[10px] text-terminal-muted mt-1">{d.reasons.join(" · ")}</div>
      )}
      <div className="text-[9px] text-terminal-muted/70 italic mt-0.5">
        {d.doctrine} · source: {d.source} · 📰 News: Not Connected
      </div>
    </div>
  );
}
