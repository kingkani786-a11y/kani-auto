"use client";
// AI Analysis card (FAIOS Layer 3 → dashboard). Gemini explains the CURRENT
// engine decision in natural language, right on the dashboard. Cost-safe:
// the backend caches by decision-band, so this 60s poll costs ~nothing until
// the decision changes. The engine decides; Gemini only phrases. Every answer
// shows the authoritative engine decision + a Safety banner if needed.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

function speak(text: string) {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "ta-IN"; u.rate = 1.0;
  window.speechSynthesis.speak(u);
}

export function AIAnalysisCard() {
  const [r, setR] = useState<any>(null);
  const [busy, setBusy] = useState(false);

  const load = (force = false) => {
    setBusy(true);
    api.cortexAnalyze(force).then(setR).catch((e) => setR({ ok: false, error: String(e?.message || e) })).finally(() => setBusy(false));
  };
  useEffect(() => { load(); const t = setInterval(() => load(false), 60000); return () => clearInterval(t); }, []);

  // Hide entirely when the cortex is off (no key) — no broken card.
  if (r?.disabled) return null;

  const flagged = r?.safety?.flagged;
  return (
    <section className="panel space-y-2">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white">🧠 AI Analysis <span className="text-[10px] text-terminal-muted">(Gemini · explains, never decides)</span></h2>
        <div className="flex items-center gap-2">
          {r?.text && <button onClick={() => speak(r.text)} className="text-[11px] px-2 py-0.5 rounded border border-terminal-border hover:border-terminal-accent" title="Speak">🔊</button>}
          <button onClick={() => load(true)} disabled={busy}
            className="text-[11px] px-2 py-0.5 rounded border border-terminal-border hover:border-terminal-accent disabled:opacity-40">
            {busy ? "…" : "↻"}
          </button>
        </div>
      </div>

      {!r ? <div className="text-xs text-terminal-muted">Loading…</div>
        : r.ok === false ? <div className="text-xs text-terminal-warn">{r.capped ? "Budget cap reached — " : "AI unavailable — "}{r.error || r.reason}</div>
        : (
          <>
            {r.blocks && (r.blocks.why || r.blocks.next || r.blocks.watch || r.blocks.change) ? (
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                {([["WHY", "why", "text-terminal-muted"], ["NEXT", "next", "text-terminal-accent"],
                   ["WATCH", "watch", "text-terminal-warn"], ["CHANGE", "change", "text-terminal-bull"]] as const).map(([label, key, tone]) => (
                  <div key={key} className="border border-terminal-border rounded p-2">
                    <div className={`text-[10px] font-semibold ${tone}`}>{label}</div>
                    <div className="text-sm leading-snug">{r.blocks[key] || "—"}</div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-sm whitespace-pre-wrap leading-relaxed">{r.text}</div>
            )}
            {flagged && <div className="text-[11px] text-terminal-bear border border-terminal-bear/40 rounded p-1.5">⚠️ AI text contained a trade directive — ignore it; follow the engine decision.</div>}
            <div className="text-[11px] text-terminal-muted flex flex-wrap gap-2">
              <span>Engine decision: <b className="text-white">{r.authoritative_decision ?? "—"}</b></span>
              {r.cached ? <span>· cached {r.cache_age_sec}s</span> : r.usage && <span>· fresh · ₹{r.usage.cost_inr}</span>}
            </div>
          </>
        )}
    </section>
  );
}
