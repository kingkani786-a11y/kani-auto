"use client";
// AI MARKET BRAIN (Rule 12) — chat over the platform's existing intelligence.
// Answers in probabilities, never certainty. No external LLM; reuses live state.

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

interface Msg { role: "user" | "ai"; text: string; points?: string[]; confidence?: number }

const SUGGESTIONS = [
  "What is the next likely move?",
  "Is this a runner?",
  "Where are institutions trapped?",
  "Can the resistance break?",
  "Where should I enter?",
  "How far can premium expand?",
];

export default function BrainPage() {
  const [msgs, setMsgs] = useState<Msg[]>([
    { role: "ai", text: "Ask me about direction, a level, runners, premium, institutions, or entry/exit. I answer in probabilities from live data." },
  ]);
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [auto, setAuto] = useState<any[]>([]);
  const endRef = useRef<HTMLDivElement>(null);

  // S14 — the AI answers the key questions automatically, before you ask
  useEffect(() => {
    const load = () => api.brainAuto().then(setAuto).catch(() => {});
    load();
    const t = setInterval(load, 20000);
    return () => clearInterval(t);
  }, []);

  async function ask(question: string) {
    const text = question.trim();
    if (!text || busy) return;
    setMsgs((m) => [...m, { role: "user", text }]);
    setQ("");
    setBusy(true);
    try {
      const r = await api.brain(text);
      setMsgs((m) => [...m, { role: "ai", text: r.answer, points: r.points, confidence: r.confidence }]);
    } catch (e: any) {
      setMsgs((m) => [...m, { role: "ai", text: `Couldn't answer (${e.message}).` }]);
    } finally {
      setBusy(false);
      setTimeout(() => endRef.current?.scrollIntoView({ behavior: "smooth" }), 50);
    }
  }

  return (
    <div className="max-w-2xl mx-auto space-y-4">
      {/* S14 — auto-answered key questions (the AI answers before you ask) */}
      {auto.length > 0 && (
        <div className="panel">
          <div className="panel-title">Auto Brief — answered for you</div>
          <div className="space-y-2">
            {auto.map((a, i) => (
              <div key={i} className="border-t border-terminal-border/40 pt-1.5 first:border-0 first:pt-0">
                <div className="text-[11px] text-terminal-accent">{a.q}</div>
                <div className="text-sm">{a.answer}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="panel">
        <div className="panel-title">AI Market Brain — ask anything</div>
        <div className="space-y-3 max-h-[55vh] overflow-y-auto">
          {msgs.map((m, i) => (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div className={`max-w-[85%] rounded-xl px-3 py-2 text-sm ${
                m.role === "user" ? "bg-terminal-accent/15 border border-terminal-accent/30"
                                  : "bg-terminal-bg border border-terminal-border"}`}>
                <div>{m.text}</div>
                {!!m.points?.length && (
                  <ul className="mt-1.5 space-y-0.5 text-[11px] text-terminal-muted">
                    {m.points.map((p, j) => <li key={j}>▸ {p}</li>)}
                  </ul>
                )}
                {/* Owner Step 8 (Remove Fake Metrics, 2026-07-26): this is
                    the brain's own self-assessed certainty in ITS ANSWER —
                    a mix of real signal-derived values and static per-
                    template estimates, not a validated trading probability.
                    Labeled accordingly so it's never mistaken for a
                    calibrated confidence. */}
                {m.confidence != null && m.role === "ai" && m.confidence > 0 && (
                  <div className="mt-1 text-[10px] text-terminal-muted"
                    title="Self-assessed answer confidence — not a validated trading probability.">
                    answer confidence {m.confidence}%
                  </div>
                )}
              </div>
            </div>
          ))}
          <div ref={endRef} />
        </div>
      </div>

      <div className="flex flex-wrap gap-1.5">
        {SUGGESTIONS.map((s) => (
          <button key={s} onClick={() => ask(s)} disabled={busy}
            className="text-[11px] px-2.5 py-1 rounded-full border border-terminal-border text-terminal-muted hover:border-terminal-accent hover:text-white disabled:opacity-50">
            {s}
          </button>
        ))}
      </div>

      <form onSubmit={(e) => { e.preventDefault(); ask(q); }} className="flex gap-2">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Ask the market brain…"
          className="flex-1 bg-terminal-bg border border-terminal-border rounded-lg px-3 py-2.5 text-sm focus:border-terminal-accent outline-none" />
        <button disabled={busy} className="px-5 py-2.5 rounded-lg bg-terminal-accent text-black font-bold text-sm disabled:opacity-50">
          {busy ? "…" : "Ask"}
        </button>
      </form>
      <p className="text-[10px] text-terminal-muted text-center">
        Probability-based reasoning from live data — not financial advice, never a certainty.
      </p>
    </div>
  );
}
