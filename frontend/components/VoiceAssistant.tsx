"use client";
// Voice Copilot v0 — PROPOSAL #011 first slice (owner order: "add the voice
// recognition"). CONSUMER ONLY, per the owner's FINAL LAW: voice never
// calculates, never decides — it sends your spoken question to the existing
// AI Brain (brain.answer, the same engine behind the chat page) and speaks
// back the dashboard's own answer. Push-to-talk (no always-on mic).
// Optional toggle: speak incoming MOVE/ENTRY/SL alerts aloud (default off).
import { useEffect, useRef, useState } from "react";
import { useMarket } from "@/lib/store";
import { api } from "@/lib/api";

const SPEAK_KINDS = new Set(["MOVE", "ENTRY", "TARGET", "SL", "ARMED"]);

function speak(text: string, lang: string) {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();          // owner rule: new event replaces old speech
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang;
  u.rate = 0.95;
  window.speechSynthesis.speak(u);
}

export function VoiceAssistant() {
  const { alerts } = useMarket();
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [speakAlerts, setSpeakAlerts] = useState(false);
  const [lang, setLang] = useState<"en-IN" | "ta-IN">("en-IN");
  const [last, setLast] = useState<{ q: string; a: string } | null>(null);
  const recRef = useRef<any>(null);
  const spokenIds = useRef<Set<string>>(new Set());

  useEffect(() => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    setSupported(!!SR && !!window.speechSynthesis);
  }, []);

  // optional alert narration — pure consumer of the existing alert feed;
  // each alert spoken at most once (owner: no repetition until state changes)
  useEffect(() => {
    if (!speakAlerts || !alerts?.length) return;
    const a = alerts[0];
    if (!a?.id || spokenIds.current.has(a.id) || !SPEAK_KINDS.has(a.kind)) return;
    spokenIds.current.add(a.id);
    speak(`${a.title}. ${String(a.body || "").split("·")[0]}`, lang);
  }, [alerts, speakAlerts, lang]);

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
        <span className="panel-title">🎙 VOICE</span>
        <button onClick={listen}
          className={`px-3 py-1 rounded border text-xs font-bold ${
            listening ? "border-terminal-bear text-terminal-bear animate-pulse"
                      : "border-terminal-accent text-terminal-accent"}`}>
          {listening ? "● LISTENING — tap to stop" : "🎤 ASK (push-to-talk)"}
        </button>
        <label className="flex items-center gap-1 text-terminal-muted cursor-pointer">
          <input type="checkbox" checked={speakAlerts}
                 onChange={(e) => setSpeakAlerts(e.target.checked)} />
          Speak alerts
        </label>
        <select value={lang} onChange={(e) => setLang(e.target.value as any)}
                className="bg-transparent border border-terminal-border rounded px-1 py-0.5 text-xs">
          <option value="en-IN">English (IN)</option>
          <option value="ta-IN">தமிழ்</option>
        </select>
        <button onClick={() => window.speechSynthesis?.cancel()}
                className="text-terminal-muted hover:text-terminal-bear">🔇 stop</button>
        <span className="text-[10px] text-terminal-muted">
          Consumer only — voice reads the dashboard; it never decides.
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
