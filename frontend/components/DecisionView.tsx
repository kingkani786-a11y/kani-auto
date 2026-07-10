"use client";
// V10 ultra-simple decision terminal. The Golden Rule: a trader understands
// the call in 3 seconds. Big labels, ≤6 cards, no OI/PCR/Greeks/confidence%.

import { useEffect, useState } from "react";
import { useMarket } from "@/lib/store";
import { api } from "@/lib/api";

const fmt = (n?: number | null) =>
  n === undefined || n === null ? "—" : n.toLocaleString("en-IN", { maximumFractionDigits: 2 });

function tone(label: string) {
  if (label.startsWith("🔥")) return "text-terminal-bull border-terminal-bull/40 bg-terminal-bull/10";
  if (label.startsWith("⚡")) return "text-terminal-warn border-terminal-warn/40 bg-terminal-warn/10";
  if (label.startsWith("🔄")) return "text-terminal-accent border-terminal-accent/40 bg-terminal-accent/10";
  return "text-terminal-muted border-terminal-border bg-terminal-bg";
}

const ACTION_TONE: Record<string, string> = {
  "BUY CALL": "text-terminal-bull border-terminal-bull/60 bg-terminal-bull/15",
  "BUY": "text-terminal-bull border-terminal-bull/60 bg-terminal-bull/15",
  "BUY PUT": "text-terminal-bear border-terminal-bear/60 bg-terminal-bear/15",
  "SELL": "text-terminal-bear border-terminal-bear/60 bg-terminal-bear/15",
  "WAIT": "text-terminal-warn border-terminal-warn/50 bg-terminal-warn/10",
  "NO TRADE": "text-terminal-muted border-terminal-border bg-terminal-bg",
};

// V11 score → tone helper
function scoreTone(s?: number) {
  if (s === undefined || s === null) return "text-terminal-muted";
  if (s >= 75) return "text-terminal-bull";
  if (s >= 60) return "text-terminal-accent";
  if (s >= 45) return "text-terminal-warn";
  return "text-terminal-bear";
}
const biasTone = (b?: string) =>
  b === "BULLISH" || b === "FAVORABLE" ? "text-terminal-bull" :
  b === "BEARISH" || b === "RISKY" ? "text-terminal-bear" : "text-terminal-muted";

export function DecisionView() {
  const { decision: d, layers } = useMarket();
  const L = layers as any;
  // display-only: read exposure from the existing portfolio endpoint
  const [exposure, setExposure] = useState<number | null>(null);
  useEffect(() => {
    const load = () => api.portfolioRisk().then((p) => setExposure(p?.exposure_pct ?? null)).catch(() => {});
    load();
    const t = setInterval(load, 20000);
    return () => clearInterval(t);
  }, []);

  if (!d) {
    return (
      <div className="panel text-center py-10">
        <div className="w-8 h-8 mx-auto mb-3 border-2 border-terminal-border border-t-terminal-accent rounded-full animate-spin" />
        <p className="text-sm text-terminal-muted">Reading the market… first decision lands within ~15s of connect.</p>
      </div>
    );
  }

  const actionTone = ACTION_TONE[d.action] ?? ACTION_TONE["NO TRADE"];

  return (
    <div className="space-y-4">
      {/* Row 1: market read — three big status chips */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
        <div className={`rounded-xl border p-4 text-center font-bold text-base ${tone(d.market_state_label)}`}>
          {d.market_state_label}
        </div>
        <div className={`rounded-xl border p-4 text-center font-bold text-base ${tone(d.opportunity)}`}>
          {d.opportunity}
        </div>
        <div className={`rounded-xl border p-4 text-center font-bold text-base ${tone(d.conviction_label)}`}>
          {d.conviction_label}
        </div>
      </div>

      {/* V11 Row: Global Context + Market Strength */}
      {(L?.global_context || L?.market_strength) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="panel py-3">
            {/* RC1.16.10 — this tile is the INTERNAL India engine (VIX/GIFT/
                regime), not the 🌐 external global feed; one label per source */}
            <div className="stat-label">INDIA RISK CONTEXT (VIX · REGIME)</div>
            <div className="flex items-baseline gap-2 mt-1">
              <span className={`text-xl font-bold ${biasTone(L?.global_context?.bias)}`}>{L?.global_context?.bias ?? "—"}</span>
              <span className={`text-sm font-mono ${biasTone(L?.global_context?.condition)}`}>{L?.global_context?.condition ?? ""}</span>
            </div>
            <div className="text-[11px] text-terminal-muted mt-1">
              India VIX {L?.vix_correlation?.vix ?? "—"}
              {L?.vix_correlation?.state ? ` · ${String(L.vix_correlation.state).replace(/_/g, " ").toLowerCase()}` : ""}
              {" · "}{L?.session?.label ?? ""}
            </div>
          </div>
          <div className="panel py-3">
            <div className="stat-label">MARKET STRENGTH</div>
            <div className="flex items-baseline gap-2 mt-1">
              <span className={`text-xl font-bold font-mono ${scoreTone(L?.market_strength?.score)}`}>{L?.market_strength?.score ?? "—"}</span>
              <span className="text-sm text-terminal-muted">/100</span>
              <span className={`text-sm font-bold ${scoreTone(L?.market_strength?.score)}`}>{String(L?.market_strength?.label ?? "").replace(/_/g, " ")}</span>
            </div>
            <div className="h-1.5 rounded bg-terminal-bg overflow-hidden mt-2">
              <div className="h-full bg-terminal-accent" style={{ width: `${L?.market_strength?.score ?? 0}%` }} />
            </div>
          </div>
        </div>
      )}

      {/* V11 Row: Market Phase + Future Path */}
      {(L?.regime || L?.future_path) && (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <div className="panel py-3">
            <div className="stat-label">MARKET PHASE</div>
            <div className="text-base font-bold mt-1">{String(L?.regime?.regime ?? "—").replace(/_/g, " ")}</div>
            <div className="flex flex-wrap gap-1 mt-1.5">
              {(L?.regime?.phases ?? []).map((p: string) => (
                <span key={p} className="px-1.5 py-0.5 rounded bg-terminal-bg border border-terminal-border text-[9px] font-mono text-terminal-accent">{p.replace(/_/g, " ")}</span>
              ))}
            </div>
          </div>
          <div className="panel py-3">
            <div className="stat-label">FUTURE PATH</div>
            <div className="text-sm font-semibold mt-1">{L?.future_path?.primary_path ?? "—"}</div>
            <ul className="text-[11px] text-terminal-muted mt-1 space-y-0.5">
              {(L?.future_path?.scenarios ?? []).slice(0, 2).map((s: string, i: number) => (<li key={i}>▸ {s}</li>))}
            </ul>
          </div>
        </div>
      )}

      {/* V11 Row: Entry Probability + Trade Quality + Institutional Activity */}
      {(L?.entry_probability || L?.trade_quality || L?.institutional_activity) && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="panel py-3 text-center">
            <div className="stat-label">ENTRY PROBABILITY</div>
            <div className={`text-2xl font-black font-mono mt-1 ${scoreTone(L?.entry_probability?.score)}`}>{L?.entry_probability?.score ?? "—"}</div>
            <div className="text-[10px] text-terminal-muted">{L?.entry_probability?.label ?? ""}</div>
          </div>
          <div className="panel py-3 text-center">
            <div className="stat-label">TRADE QUALITY</div>
            <div className={`text-2xl font-black font-mono mt-1 ${
              L?.trade_quality?.grade === "A+" || L?.trade_quality?.grade === "A" ? "text-terminal-bull" :
              L?.trade_quality?.grade === "B" ? "text-terminal-accent" :
              L?.trade_quality?.grade === "C" ? "text-terminal-warn" : "text-terminal-muted"}`}>
              {L?.trade_quality?.grade ?? "—"}
            </div>
            <div className="text-[10px] text-terminal-muted">{(L?.trade_quality?.reasons ?? []).join(" · ")}</div>
          </div>
          <div className="panel py-3 text-center">
            <div className="stat-label">INSTITUTIONAL</div>
            <div className={`text-xl font-bold mt-1 ${biasTone(L?.institutional_activity?.bias)}`}>{L?.institutional_activity?.bias ?? "—"}</div>
            <div className="text-[10px] text-terminal-muted">pressure {L?.institutional_activity?.pressure ?? 0}% · derived</div>
          </div>
        </div>
      )}

      {/* Row 2: the decision — action, lots, entry window */}
      <div className="grid grid-cols-1 lg:grid-cols-[1.2fr_1fr_1fr] gap-3">
        <div className={`rounded-xl border p-5 flex flex-col justify-center ${actionTone}`}>
          <div className="stat-label opacity-70">TRADE ACTION</div>
          <div className="text-4xl font-black font-mono tracking-tight mt-1">{d.action}</div>
          <div className="text-sm mt-1 opacity-90">{d.reason}</div>
        </div>

        <div className="panel flex flex-col justify-center">
          <div className="stat-label">POSITION INTELLIGENCE</div>
          {d.is_trade && d.max_safe_lots > 0 ? (
            <>
              <div className="text-3xl font-bold font-mono mt-1">{d.recommended_lots} <span className="text-base text-terminal-muted">lots</span></div>
              <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 mt-2 text-[11px]">
                <span className="text-terminal-muted">Max safe</span><span className="font-mono text-right">{d.max_safe_lots} lots</span>
                <span className="text-terminal-muted">Exposure</span><span className="font-mono text-right">{exposure != null ? `${exposure}%` : "—"}</span>
                <span className="text-terminal-muted">Strength</span><span className="font-mono text-right">{String(L?.market_strength?.label ?? "—").replace(/_/g, " ")}</span>
                <span className="text-terminal-muted">Risk mode</span>
                <span className={`font-mono text-right ${L?.capital_protection?.action && L.capital_protection.action !== "NORMAL" ? "text-terminal-warn" : ""}`}>
                  {String(L?.capital_protection?.action ?? "NORMAL").replace(/_/g, " ")}
                </span>
              </div>
            </>
          ) : (
            <div className="text-2xl font-bold font-mono mt-1 text-terminal-muted">—</div>
          )}
        </div>

        <div className="panel flex flex-col justify-center text-center">
          <div className="stat-label">ENTRY TIMING</div>
          <div className={`text-lg font-bold mt-2 ${
            d.entry_window.startsWith("🚀") ? "text-terminal-bull" :
            d.entry_window.startsWith("⚠") ? "text-terminal-warn" : "text-terminal-muted"}`}>
            {d.entry_window}
          </div>
          <div className="text-sm mt-2 text-terminal-accent font-mono">{d.action_state}</div>
        </div>
      </div>

      {/* Row 3: levels — only when there's a live trade */}
      {d.is_trade && (
        <div className="grid grid-cols-2 sm:grid-cols-5 gap-3">
          <div className="panel py-3 text-center">
            <div className="stat-label">ENTRY</div>
            <div className="text-lg font-mono font-bold text-terminal-accent">{fmt(d.entry)}</div>
          </div>
          <div className="panel py-3 text-center">
            <div className="stat-label">STOP LOSS</div>
            <div className="text-lg font-mono font-bold text-terminal-bear">{fmt(d.stop_loss)}</div>
          </div>
          {[d.target1, d.target2, d.target3].map((t, i) => (
            <div key={i} className="panel py-3 text-center">
              <div className="stat-label">TARGET {i + 1}</div>
              <div className="text-lg font-mono font-bold text-terminal-bull">{fmt(t)}</div>
            </div>
          ))}
        </div>
      )}

      {/* V13: Capital Protection + No-Trade Zone + Trap Detection */}
      {(L?.capital_protection || L?.no_trade_zone || L?.traps) && (
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
          <div className="panel py-3">
            <div className="stat-label">CAPITAL PROTECTION</div>
            <div className="flex items-baseline gap-2 mt-1">
              <span className={`text-2xl font-black font-mono ${
                L?.capital_protection?.category === "CRITICAL" ? "text-terminal-bear" :
                L?.capital_protection?.category === "ELEVATED" ? "text-terminal-warn" :
                L?.capital_protection?.category === "ACCEPTABLE" ? "text-terminal-accent" : "text-terminal-bull"}`}>
                {L?.capital_protection?.capital_risk ?? "—"}
              </span>
              <span className="text-sm font-bold">{L?.capital_protection?.category ?? ""}</span>
            </div>
            <div className="grid grid-cols-2 gap-x-3 gap-y-0.5 mt-2 text-[10px] text-terminal-muted font-mono">
              <span>Theta {L?.capital_protection?.theta_risk ?? "—"}</span>
              <span>IV-Crush {L?.capital_protection?.iv_crush_risk ?? "—"}</span>
              <span>Decay {L?.capital_protection?.premium_decay_risk ?? "—"}</span>
              <span>Reversal {L?.capital_protection?.reversal_risk ?? "—"}</span>
            </div>
            {L?.capital_protection?.action && L.capital_protection.action !== "NORMAL" && (
              <div className="text-[10px] text-terminal-warn mt-1">{L.capital_protection.action.replace(/_/g, " ")}</div>
            )}
          </div>
          <div className="panel py-3">
            <div className="stat-label">NO-TRADE ZONE</div>
            <div className={`text-xl font-bold mt-1 ${L?.no_trade_zone?.active ? "text-terminal-bear" : "text-terminal-bull"}`}>
              {L?.no_trade_zone?.status ?? "—"}
            </div>
            <div className="text-[11px] text-terminal-muted mt-1">{L?.no_trade_zone?.reason ?? ""}</div>
          </div>
          <div className="panel py-3">
            <div className="stat-label">TRAP DETECTION</div>
            <div className={`text-base font-bold mt-1 ${L?.traps?.detected ? "text-terminal-bear" : "text-terminal-bull"}`}>
              {L?.traps?.detected ? `${L.traps.trap_confidence}% RISK` : "CLEAR"}
            </div>
            <div className="text-[11px] text-terminal-muted mt-1">{L?.traps?.summary ?? ""}</div>
          </div>
        </div>
      )}

      {/* Row 8: Market Roadmap — full-width forward scenarios */}
      {L?.future_path && (
        <div className="panel py-3">
          <div className="stat-label">MARKET ROADMAP</div>
          <div className="text-sm font-semibold mt-1">{L.future_path.primary_path}</div>
          <div className="grid sm:grid-cols-3 gap-2 mt-2">
            {(L.future_path.scenarios ?? []).map((s: string, i: number) => (
              <div key={i} className="text-[11px] text-terminal-muted bg-terminal-bg rounded-lg px-3 py-2 border border-terminal-border/50">{s}</div>
            ))}
          </div>
          {L.future_path.expected_range?.[0] && (
            <div className="text-[11px] text-terminal-muted mt-2">
              Expected range: {fmt(L.future_path.expected_range[0])} – {fmt(L.future_path.expected_range[1])}
              {L.future_path.pivot ? ` · pivot ${fmt(L.future_path.pivot)}` : ""}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
