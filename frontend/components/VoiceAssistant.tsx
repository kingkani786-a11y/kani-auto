"use client";
// Voice Copilot v0.2 — Live Market Narrator (PROPOSAL #011, owner v2.0 spec).
// FINAL LAW enforced by construction: every spoken word comes from state the
// dashboard ALREADY computed — the AI Market Narrator lines, the alert feed,
// the decision/gate state, and brain.answer() for spoken questions. Voice
// never calculates, never decides. Dashboard thinks → Voice speaks.
import { useEffect, useRef, useState } from "react";
import { useMarket } from "@/lib/store";
import { api } from "@/lib/api";

type Mode = "SILENT" | "ALERTS" | "COMMENTARY" | "FULL";
const SPEAK_KINDS = new Set(["MOVE", "ENTRY", "TARGET", "SL", "ARMED"]);

// priority speech: interrupts anything (alerts, decisions, Q&A answers)
function speak(text: string, lang: string) {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang; u.rate = 0.95;
  window.speechSynthesis.speak(u);
}
// commentary speech: NEVER interrupts — skips its turn if anything is speaking
function speakSoft(text: string, lang: string): boolean {
  if (typeof window === "undefined" || !window.speechSynthesis) return false;
  if (window.speechSynthesis.speaking) return false;
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang; u.rate = 0.95;
  window.speechSynthesis.speak(u);
  return true;
}

export function VoiceAssistant() {
  const { alerts, decision, narrative } = useMarket();
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [mode, setMode] = useState<Mode>("SILENT");
  const [lang, setLang] = useState<"en-IN" | "ta-IN">("en-IN");
  const [last, setLast] = useState<{ q: string; a: string } | null>(null);
  const recRef = useRef<any>(null);
  const spokenIds = useRef<Set<string>>(new Set());
  const spokenLines = useRef<Set<string>>(new Set());
  const prevGate = useRef<string>("");

  useEffect(() => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    setSupported(!!SR && !!window.speechSynthesis);
  }, []);

  // Stream: alert narration (priority) — ALERTS mode and above
  useEffect(() => {
    if (mode === "SILENT" || !alerts?.length) return;
    const a = alerts[0];
    if (!a?.id || spokenIds.current.has(a.id) || !SPEAK_KINDS.has(a.kind)) return;
    spokenIds.current.add(a.id);
    speak(`${a.title}. ${String(a.body || "").split("·")[0]}`, lang);
  }, [alerts, mode, lang]);

  // Stream: decision transitions (priority) — ALERTS mode and above.
  // Owner's no-repeat rule: speak only when the gate STATE changes.
  useEffect(() => {
    if (mode === "SILENT") return;
    const eg = (decision as any)?.execution_gate;
    if (!eg?.ready) return;
    const state = eg.gate_passed ? "READY" : `WAIT:${(eg.waiting_on || []).length}`;
    if (prevGate.current && state !== prevGate.current) {
      if (eg.gate_passed) {
        const st = (decision as any)?.strike || {};
        speak(`Setup ready. ${st.strike ?? ""} ${st.type ?? ""}. ` +
              (st.premium_entry != null
                ? `Premium ${st.premium_entry}. Stop loss ${st.premium_stop_loss}. Target one ${st.premium_target1}.`
                : ""), lang);
      } else if (prevGate.current === "READY") {
        speak("Setup no longer ready. Back to waiting.", lang);
      }
    }
    prevGate.current = state;
  }, [decision, mode, lang]);

  // Stream: market commentary — COMMENTARY/FULL modes. Reads the EXISTING
  // AI Market Narrator lines (the dashboard's own tape explanation); each
  // line spoken once, checked every 15s, never interrupts higher priority.
  useEffect(() => {
    if (mode !== "COMMENTARY" && mode !== "FULL") return;
    const t = setInterval(() => {
      const fresh = (narrative || []).find((l: string) => l && !spokenLines.current.has(l));
      if (fresh && speakSoft(fresh, lang)) {
        spokenLines.current.add(fresh);
        if (spokenLines.current.size > 200) spokenLines.current.clear();
      }
    }, 15000);
    return () => clearInterval(t);
  }, [mode, lang, narrative]);

  function listen() {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    if (!SR) return;
    if (listening) { recRef.current?.stop(); return; }
    const rec = new SR();
    recRef.current = rec;
    rec.lang = lang;
    rec.interimResults = false;
    rec.maxAlternatives = 1;
    rec.onstart = () => setListening(true);
    rec.onend = () => setListening(false);
    rec.onerror = () => setListening(false);
    rec.onresult = async (ev: any) => {
      const q = ev.results?.[0]?.[0]?.transcript || "";
      if (!q) return;
      if (/stop talking|be quiet|mute/i.test(q)) { window.speechSynthesis?.cancel(); return; }
      try {
        const r = await api.brain(q);
        const answer = [r.answer, ...(r.points || []).slice(0, 3)].join(". ");
        setLast({ q, a: r.answer });
        speak(answer, lang);
      } catch {
        speak("Backend not reachable.", lang);
      }
    };
    rec.start();
  }

  if (!supported) return null;   // honest: no fake mic on unsupported browsers

  return (
    <div className="panel py-2">
      <div className="flex flex-wrap items-center gap-3 text-xs">
        <span className="panel-title">🎙 VOICE NARRATOR</span>
        <select value={mode} onChange={(e) => { setMode(e.target.value as Mode); window.speechSynthesis?.cancel(); }}
                className="bg-transparent border border-terminal-border rounded px-1 py-0.5 text-xs">
          <option value="SILENT">🔇 Silent</option>
          <option value="ALERTS">🔔 Alerts + Decisions</option>
          <option value="COMMENTARY">🗣 + Market Commentary</option>
          <option value="FULL">🎧 Full Copilot</option>
        </select>
        <button onClick={listen}
          className={`px-3 py-1 rounded border text-xs font-bold ${
            listening ? "border-terminal-bear text-terminal-bear animate-pulse"
                      : "border-terminal-accent text-terminal-accent"}`}>
          {listening ? "● LISTENING — tap to stop" : "🎤 ASK"}
        </button>
        <select value={lang} onChange={(e) => setLang(e.target.value as any)}
                className="bg-transparent border border-terminal-border rounded px-1 py-0.5 text-xs">
          <option value="en-IN">English (IN)</option>
          <option value="ta-IN">தமிழ்</option>
        </select>
        <button onClick={() => window.speechSynthesis?.cancel()}
                className="text-terminal-muted hover:text-terminal-bear">⏹ stop</button>
        <span className="text-[10px] text-terminal-muted">
          Dashboard thinks → voice speaks. Never decides.
        </span>
      </div>
      {last && (
        <div className="mt-1 text-[11px] text-terminal-muted">
          Q: “{last.q}” → {last.a}
        </div>
      )}
    </div>
  );
}
