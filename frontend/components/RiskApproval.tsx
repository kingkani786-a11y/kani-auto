"use client";
// 🔒 RISK APPROVAL — V5 layer 5. The capital & market safety gate that sits
// between the Decision Engine and the human. It never decides direction and
// never places an order — it consolidates account/market/trade-quality checks
// into one verdict + a risk-based position size. UNKNOWN checks show honestly.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { displayLabel, displayReasons } from "@/lib/labels";

const mark = (ok: boolean | null) =>
  ok === true ? { s: "✓", c: "text-terminal-bull" }
  : ok === false ? { s: "✕", c: "text-terminal-bear" }
  : { s: "○", c: "text-terminal-muted" };

function Section({ title, rows }: { title: string; rows: any[] }) {
  return (
    <div className="space-y-0.5">
      <div className="text-[10px] font-semibold text-terminal-muted uppercase tracking-wide">{title}</div>
      {rows.map((c, i) => {
        const m = mark(c.ok);
        return (
          <div key={i} className="flex items-baseline gap-2 text-[11px]">
            <span className={`${m.c} w-3`}>{m.s}</span>
            <span className="text-gray-200">{displayLabel(c.name)}</span>
            <span className="ml-auto text-terminal-muted text-right truncate max-w-[55%]" title={c.detail}>{displayLabel(c.detail)}</span>
          </div>
        );
      })}
    </div>
  );
}

export function RiskApproval() {
  const [d, setD] = useState<any>(null);
  useEffect(() => {
    const load = () => api.riskApproval().then(setD).catch(() => {});
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);
  if (!d) return null;

  const ps = d.position_size || {};
  const head =
    d.status === "APPROVED" ? { t: "🟢 RISK APPROVED", c: "text-terminal-bull border-terminal-bull/50 bg-terminal-bull/10" }
    : d.status === "BLOCKED" ? { t: "🔴 RISK BLOCKED", c: "text-terminal-bear border-terminal-bear/50 bg-terminal-bear/10" }
    : { t: "⏸ NO ACTIVE SETUP", c: "text-terminal-muted border-terminal-border" };

  return (
    <section className="panel space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white">🔒 Risk Approval <span className="text-[10px] text-terminal-muted">(capital & market safety gate)</span></h2>
        <span className={`text-[11px] font-bold px-2 py-0.5 rounded border ${head.c}`}>{head.t}</span>
      </div>

      {d.blockers?.length > 0 && (
        <div className="text-[11px] text-terminal-bear border border-terminal-bear/40 rounded p-1.5">
          Blocked by: {displayReasons(d.blockers).join(" · ")}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <Section title="Account" rows={d.sections?.account || []} />
        <Section title="Market" rows={d.sections?.market || []} />
        <Section title="Trade Quality" rows={d.sections?.quality || []} />
      </div>

      {/* Position size — risk-based, informational */}
      <div className="border-t border-terminal-border pt-2 grid grid-cols-2 sm:grid-cols-4 gap-2 text-center">
        <div><div className="text-sm font-semibold tabular-nums text-white">₹{(ps.capital || 0).toLocaleString("en-IN")}</div><div className="text-[9px] text-terminal-muted">Capital</div></div>
        <div><div className="text-sm font-semibold tabular-nums text-white">{ps.recommended_lots ?? "—"}{ps.max_lots ? ` / ${ps.max_lots}` : ""}</div><div className="text-[9px] text-terminal-muted">Rec / Max lots ({ps.risk_pct}%)</div></div>
        <div><div className="text-sm font-semibold tabular-nums text-terminal-bear">{ps.risk_amount ? `₹${ps.risk_amount.toLocaleString("en-IN")}` : "—"}</div><div className="text-[9px] text-terminal-muted">Risk</div></div>
        <div><div className="text-sm font-semibold tabular-nums text-terminal-bull">{ps.reward_amount ? `₹${ps.reward_amount.toLocaleString("en-IN")}` : "—"}</div><div className="text-[9px] text-terminal-muted">Reward{ps.rr ? ` (1:${ps.rr})` : ""}</div></div>
      </div>

      <div className="text-[10px] text-terminal-muted">{d.note}</div>
    </section>
  );
}
