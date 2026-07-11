"use client";
// AI-A2 — AI Workspace (Proposal #013 Phase A/B surface).
// The visible face of the live Gemini Cortex. Explanation / research / reports
// ONLY — never a trade instruction; the decision engine stays the sole source
// of BUY/WAIT/NO-TRADE. Every AI answer carries the engine's authoritative
// decision + a Safety banner.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const ROLES = [
  ["explainer", "Explain the decision"],
  ["analyst", "Market summary"],
  ["teacher", "Teach me a concept"],
  ["research", "Research an idea"],
  ["planner", "Plan / prepare"],
  ["reviewer", "Review performance"],
];

function Card({ title, right, children }: { title: string; right?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="panel space-y-2">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white">{title}</h2>
        {right}
      </div>
      {children}
    </section>
  );
}

function AnswerBlock({ res }: { res: any }) {
  if (!res) return null;
  if (res.ok === false) {
    const why = res.error || res.reason || "AI unavailable.";
    return <div className="text-xs text-terminal-warn border border-terminal-border rounded p-2">{res.disabled ? "AI Cortex OFF — " : res.capped ? "Budget cap reached — " : "Error — "}{why}</div>;
  }
  const flagged = res.safety?.flagged;
  return (
    <div className="space-y-2">
      <div className="text-sm whitespace-pre-wrap leading-relaxed">{res.text}</div>
      {flagged && (
        <div className="text-[11px] text-terminal-bear border border-terminal-bear/40 rounded p-1.5">
          ⚠️ AI text contained trade-directive language — ignore it. Follow the engine decision only.
        </div>
      )}
      <div className="text-[11px] text-terminal-muted flex flex-wrap gap-3">
        <span>Engine decision: <b className="text-white">{res.authoritative_decision ?? "—"}</b> (the only source of truth)</span>
        {res.usage && <span>· {res.model} · {res.usage.output_tokens} tok · ₹{res.usage.cost_inr}</span>}
        {res.latency_ms != null && <span>· {(res.latency_ms / 1000).toFixed(1)}s</span>}
      </div>
    </div>
  );
}

export default function AIWorkspacePage() {
  const [status, setStatus] = useState<any>(null);
  const [weekend, setWeekend] = useState<any>(null);
  const [role, setRole] = useState("explainer");
  const [q, setQ] = useState("");
  const [ans, setAns] = useState<any>(null);
  const [asking, setAsking] = useState(false);
  const [report, setReport] = useState<any>(null);
  const [reporting, setReporting] = useState(false);
  const [running, setRunning] = useState(false);

  const load = () => {
    api.cortexStatus().then(setStatus).catch(() => {});
    api.weekendAi().then(setWeekend).catch(() => {});
  };
  useEffect(() => { load(); const t = setInterval(load, 20000); return () => clearInterval(t); }, []);

  const ask = async () => {
    if (!q.trim()) return;
    setAsking(true); setAns(null);
    try { setAns(await api.cortexAsk(role, q.trim())); }
    catch (e: any) { setAns({ ok: false, error: String(e?.message || e) }); }
    finally { setAsking(false); load(); }
  };
  const runReport = async () => {
    setReporting(true);
    try { setReport(await api.cortexEodReport()); }
    catch (e: any) { setReport({ ok: false, error: String(e?.message || e) }); }
    finally { setReporting(false); load(); }
  };
  const runWeekend = async () => {
    setRunning(true);
    try { setWeekend(await api.weekendAiRun()); }
    catch { /* ignore */ }
    finally { setRunning(false); load(); }
  };

  const b = status?.budget;
  const enabled = status?.enabled;

  return (
    <div className="max-w-4xl mx-auto space-y-4">
      {/* Header — live status + budget */}
      <section className="panel flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-base font-bold text-white">🧠 AI Workspace</h1>
          <div className="text-[11px] text-terminal-muted">
            Gemini Cortex — explanation, research &amp; reports only. Trade decisions come from the engine.
          </div>
        </div>
        <div className="text-right text-xs">
          <div className={enabled ? "text-terminal-bull" : "text-terminal-warn"}>
            {enabled ? `● LIVE — ${status?.model}` : "○ AI OFF (no key)"}
          </div>
          {b && <div className="text-terminal-muted">Today: {b.calls}/{b.call_cap} calls · ₹{b.cost_inr_today} / ₹{b.cost_cap_inr} · ₹{b.budget_left_inr} left</div>}
        </div>
      </section>

      {/* AI Chat */}
      <Card title="AI Chat">
        <div className="flex flex-wrap gap-1.5">
          {ROLES.map(([r, label]) => (
            <button key={r} onClick={() => setRole(r)}
              className={`text-[11px] px-2.5 py-1 rounded-full border ${role === r ? "border-terminal-accent text-white" : "border-terminal-border text-terminal-muted"}`}>
              {label}
            </button>
          ))}
        </div>
        <textarea value={q} onChange={(e) => setQ(e.target.value)}
          placeholder="Ask about the market, a decision, or a concept… (Tanglish OK)"
          className="w-full bg-terminal-bg border border-terminal-border rounded p-2 text-sm h-20"
          onKeyDown={(e) => { if (e.key === "Enter" && (e.metaKey || e.ctrlKey)) ask(); }} />
        <div className="flex items-center gap-2">
          <button onClick={ask} disabled={asking || !enabled}
            className="px-4 py-1.5 rounded bg-terminal-accent text-black text-sm font-semibold disabled:opacity-40">
            {asking ? "Thinking…" : "Ask"}
          </button>
          <span className="text-[11px] text-terminal-muted">⌘/Ctrl+Enter</span>
        </div>
        <AnswerBlock res={ans} />
      </Card>

      {/* AI Reports */}
      <Card title="AI Reports"
        right={<button onClick={runReport} disabled={reporting || !enabled}
          className="text-[11px] px-3 py-1 rounded border border-terminal-border hover:border-terminal-accent disabled:opacity-40">
          {reporting ? "Writing…" : "Generate EOD report"}</button>}>
        {report ? <AnswerBlock res={report} /> :
          <div className="text-xs text-terminal-muted">End-of-day review, grounded in measured ledgers. Click to generate.</div>}
      </Card>

      {/* Weekend AI */}
      <Card title="Weekend AI"
        right={<button onClick={runWeekend} disabled={running || !enabled}
          className="text-[11px] px-3 py-1 rounded border border-terminal-border hover:border-terminal-accent disabled:opacity-40">
          {running ? "Running…" : "Run a cycle now"}</button>}>
        {weekend ? (
          <div className="space-y-2">
            <div className="text-xs">
              <span className={weekend.status === "WORKING" ? "text-terminal-bull" : "text-terminal-muted"}>
                {weekend.status}
              </span>
              {" — "}{weekend.activity}
              {weekend.runs_today != null && <span className="text-terminal-muted"> · {weekend.runs_today} runs today · next: {weekend.next_job}</span>}
            </div>
            {weekend.last_error && <div className="text-[11px] text-terminal-warn">{weekend.last_error}</div>}
            {weekend.outputs && Object.entries(weekend.outputs).map(([k, v]: any) => (
              <details key={k} className="border border-terminal-border rounded p-2">
                <summary className="text-xs text-white cursor-pointer capitalize">{k} · ₹{v.cost_inr}</summary>
                <div className="text-sm whitespace-pre-wrap mt-1 leading-relaxed">{v.text}</div>
              </details>
            ))}
          </div>
        ) : <div className="text-xs text-terminal-muted">Loading…</div>}
      </Card>

      {/* Roadmap honesty */}
      <section className="panel text-[11px] text-terminal-muted">
        Live now: AI Chat · Reports · Weekend AI. Coming (roadmap #014/#015):
        AI Council · Architect · News/Calendar/FII-DII feeds. The AI never decides
        trades — the engine does; every answer shows the engine's decision.
      </section>
    </div>
  );
}
