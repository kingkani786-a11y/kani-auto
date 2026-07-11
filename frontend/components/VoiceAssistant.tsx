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
// Radio spec: these interrupt EVERYTHING and speak even in Silent mode
// (when Emergency Override is on) — kill switch / broker / SL class events
const EMERGENCY_KINDS = new Set(["SL", "SYSTEM"]);

// Tanglish Professional Radio (owner production standard): Tamil narration +
// English technical terms + English digits, calm RJ tone. Composed from the
// alert's STRUCTURED data — never parsed from display strings, never invented.
function tanglishMove(a: any): string | null {
  const d = a.data;
  if (!d) return null;
  const parts = [
    `Attention. ${a.symbol} ${d.strike} ${d.type} premium ${d.from_low}-லிருந்து ${d.premium} வரை move ஆகியிருக்கிறது.`,
  ];
  if (d.confirmations?.includes("volume")) parts.push("Volume confirmation இருக்கிறது.");
  if (d.confirmations?.includes("oi")) parts.push("OI shift உறுதி ஆகியிருக்கிறது.");
  if (d.stars) parts.push(`Move strength ${d.stars} stars.`);
  if (d.accelerating) parts.push("Acceleration அதிகரிக்கிறது.");
  parts.push("Decision engine தனியாக முடிவு செய்யும்.");
  return parts.join(" ");
}

// priority speech: interrupts anything (alerts, decisions, Q&A answers)
function speak(text: string, lang: string, rate = 0.95) {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang; u.rate = rate;
  window.speechSynthesis.speak(u);
}
// commentary speech: NEVER interrupts — skips its turn if anything is speaking
function speakSoft(text: string, lang: string, rate = 0.95): boolean {
  if (typeof window === "undefined" || !window.speechSynthesis) return false;
  if (window.speechSynthesis.speaking) return false;
  const u = new SpeechSynthesisUtterance(text);
  u.lang = lang; u.rate = rate;
  window.speechSynthesis.speak(u);
  return true;
}

// AI Radio v1.0 (FAIOS Layer 9) — reads the engine's published state and turns
// transitions into a spoken radio stream. Reads ONLY published state; the
// engine decides, the radio narrates. (owner: "Screen பார்க்காமல் Market புரியணும்")
function layerTag(layers: any, ...names: string[]): string | null {
  for (const n of names) {
    const row = layers?.[n];
    if (row && typeof row === "object")
      for (const k of ["label", "state", "status", "verdict"])
        if (row[k]) return String(row[k]);
  }
  return null;
}
function layerScore(layers: any, ...names: string[]): number | null {
  for (const n of names) {
    const row = layers?.[n];
    if (row && typeof row === "object")
      for (const k of ["score", "value", "pct", "strength"])
        if (typeof row[k] === "number") return row[k];
  }
  return null;
}

export function VoiceAssistant() {
  const { alerts, decision, narrative, status, layers, exitIntel } = useMarket();
  const [supported, setSupported] = useState(false);
  const [listening, setListening] = useState(false);
  const [mode, setMode] = useState<Mode>("SILENT");
  const [lang, setLang] = useState<"en-IN" | "ta-IN">("en-IN");
  const [rate, setRate] = useState(1.0);
  const [emergencyOverride, setEmergencyOverride] = useState(true);
  const [last, setLast] = useState<{ q: string; a: string } | null>(null);
  // Safari/Chrome autoplay policy: TTS is silent until a user gesture has
  // triggered speech at least once. Track it and prompt the user honestly.
  const [unlocked, setUnlocked] = useState(false);
  const recRef = useRef<any>(null);
  const spokenIds = useRef<Set<string>>(new Set());
  const spokenLines = useRef<Set<string>>(new Set());
  const prevGate = useRef<string>("");
  const prevConfWhy = useRef<string>("");
  // AI Radio transition memory
  const radio = useRef<{ open?: boolean; trend?: string | null; structure?: string | null;
    liq?: number | null; confBucket?: number | null; targets?: number }>({});
  const greeted = useRef(false);

  async function speakBriefing() {
    try {
      const b = await api.briefing();
      // briefing is Tanglish by design — spoken with the Tamil voice
      speak((b.lines || []).join(" "), "ta-IN", rate);
      setLast({ q: "briefing", a: `${(b.lines || []).length} lines` });
    } catch { speak("Backend not reachable.", lang, rate); }
  }

  useEffect(() => {
    const SR = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
    setSupported(!!SR && !!window.speechSynthesis);
  }, []);

  // Stream: alert narration (priority) — ALERTS mode and above.
  // Radio spec: EMERGENCY class (kill switch / broker / SL) speaks even in
  // Silent mode when Emergency Override is on — nothing else does.
  useEffect(() => {
    if (!alerts?.length) return;
    const a = alerts[0];
    if (!a?.id || spokenIds.current.has(a.id)) return;
    const isEmergency = EMERGENCY_KINDS.has(a.kind);
    const allowed = isEmergency
      ? (mode !== "SILENT" || emergencyOverride)
      : (mode !== "SILENT" && SPEAK_KINDS.has(a.kind));
    if (!allowed) return;
    spokenIds.current.add(a.id);
    // Tanglish mode: compose from structured data (owner language rule —
    // Tamil narration, English technical words, English digits)
    const tang = lang === "ta-IN" && a.kind === "MOVE" ? tanglishMove(a) : null;
    speak(tang ?? `${isEmergency ? "Attention. " : ""}${a.title}. ${String(a.body || "").split("·")[0]}`,
          lang, rate);
  }, [alerts, mode, lang, rate, emergencyOverride]);

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
        const plan = st.premium_entry != null
          ? `Entry ${st.premium_entry}. Stop loss ${st.premium_stop_loss}. Target one ${st.premium_target1}.`
          : "";
        speak(lang === "ta-IN"
          ? `Attention. Setup ready ஆகிவிட்டது. Strike ${st.strike ?? ""} ${st.type ?? ""}. ${plan}`
          : `Attention. Setup ready. ${st.strike ?? ""} ${st.type ?? ""}. ${plan}`, lang, rate);
      } else if (prevGate.current === "READY") {
        speak(lang === "ta-IN"
          ? "Setup இப்போது ready இல்லை. மீண்டும் waiting."
          : "Setup no longer ready. Back to waiting.", lang, rate);
      }
    }
    prevGate.current = state;
  }, [decision, mode, lang, rate]);

  // Stream: analyst delta commentary — the confidence-evolution engine
  // already computes change + responsible layer ("Futures weakened (-20)
  // to 50"); voice simply reads it when it changes. COMMENTARY/FULL modes.
  useEffect(() => {
    if (mode !== "COMMENTARY" && mode !== "FULL") return;
    const why = (decision as any)?.confidence_evolution?.why;
    if (why && why !== prevConfWhy.current) {
      if (prevConfWhy.current) speakSoft(why, lang, rate);
      prevConfWhy.current = why;
    }
  }, [decision, mode, lang, rate]);

  // Stream: market commentary — COMMENTARY/FULL modes. Reads the EXISTING
  // AI Market Narrator lines (the dashboard's own tape explanation); each
  // line spoken once, checked every 15s, never interrupts higher priority.
  useEffect(() => {
    if (mode !== "COMMENTARY" && mode !== "FULL") return;
    const t = setInterval(() => {
      const fresh = (narrative || []).find((l: string) => l && !spokenLines.current.has(l));
      if (fresh && speakSoft(fresh, lang, rate)) {
        spokenLines.current.add(fresh);
        if (spokenLines.current.size > 200) spokenLines.current.clear();
      }
    }, 15000);
    return () => clearInterval(t);
  }, [mode, lang, rate, narrative]);

  // ── AI Radio v1.0 (Layer 9) — spoken transition stream. COMMENTARY/FULL. ──
  // Watches engine-published state and announces the moments a trader would
  // want to hear: market open/close, trend flip, structure/liquidity change,
  // confidence crossing a 10-pt band, target hits. speakSoft = never interrupts
  // alerts/decisions. Good-Morning briefing fires once on open.
  useEffect(() => {
    if (mode !== "COMMENTARY" && mode !== "FULL") return;
    const ta = lang === "ta-IN";
    const isOpen = !!status?.market_open;
    const r = radio.current;

    // Market open / close
    if (r.open !== undefined && isOpen !== r.open) {
      if (isOpen) {
        speak(ta ? "Good morning. Market open ஆகிவிட்டது." : "Good morning. Market is now open.", lang, rate);
        if (!greeted.current) { greeted.current = true; setTimeout(() => speakBriefing(), 3500); }
      } else {
        speak(ta ? "Market close ஆகிவிட்டது. இன்றைக்கு முடிந்தது." : "Market closed. That's a wrap for today.", lang, rate);
      }
    }
    r.open = isOpen;

    // The rest only when open (no chatter on a closed tape)
    if (isOpen) {
      const trend = layerTag(layers, "Trend", "MTF Trend");
      if (trend && r.trend !== undefined && trend !== r.trend)
        speakSoft(ta ? `Trend இப்போது ${trend}.` : `Trend is now ${trend}.`, lang, rate);
      r.trend = trend;

      const structure = layerTag(layers, "Structure", "Market Structure");
      if (structure && r.structure !== undefined && structure !== r.structure &&
          /confirm|break|bos/i.test(structure))
        speakSoft(ta ? `Structure ${structure}.` : `Structure ${structure}.`, lang, rate);
      r.structure = structure;

      const liq = layerScore(layers, "Liquidity", "Order Flow");
      if (liq != null && r.liq != null && liq - r.liq >= 8)
        speakSoft(ta ? "Liquidity improve ஆகுது." : "Liquidity improving.", lang, rate);
      if (liq != null) r.liq = liq;

      const conf = (decision as any)?.conviction ?? (decision as any)?.confidence ?? null;
      if (typeof conf === "number") {
        const bucket = Math.round(conf / 10) * 10;
        if (r.confBucket != null && bucket !== r.confBucket)
          speakSoft(ta ? `Confidence ${bucket} ஆக ${bucket > r.confBucket ? "உயர்ந்தது" : "குறைந்தது"}.`
                       : `Confidence ${bucket > r.confBucket ? "up" : "down"} to ${bucket}.`, lang, rate);
        r.confBucket = bucket;
      }

      const tHit = (exitIntel as any)?.targets_hit ?? (exitIntel as any)?.targets_done ??
                   ((exitIntel as any)?.targets || []).filter((t: any) => t?.hit).length;
      if (typeof tHit === "number") {
        if (r.targets != null && tHit > r.targets)
          speak(ta ? `Target ${tHit} hit ஆகிவிட்டது.` : `Target ${tHit} hit.`, lang, rate);
        r.targets = tHit;
      }
    }
  }, [mode, lang, rate, status, layers, decision, exitIntel]);

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
      // Full Analyst briefing on request
      if (/briefing|market update|full update|rundown|என்ன நடக்குது|நிலவரம்/i.test(q)) {
        speakBriefing(); return;
      }
      // Voice Memory (Radio spec): "what happened…" → replay the timestamped
      // alert timeline — the system's own recorded history, nothing invented
      if (/what happened|timeline|replay|என்ன நடந்தது/i.test(q)) {
        try {
          const feed = await api.alerts();
          const recent = (feed || []).slice(0, 8).reverse();
          if (!recent.length) { speak("No events recorded yet this session.", lang, rate); return; }
          const lines = recent.map((a: any) =>
            `${(a.ts || "").split(" ")[1] || ""}. ${a.title}.`).join(" ");
          setLast({ q, a: `${recent.length} events replayed` });
          speak(`Timeline. ${lines}`, lang, rate);
        } catch { speak("Backend not reachable.", lang, rate); }
        return;
      }
      try {
        const r = await api.brain(q);
        const answer = [r.answer, ...(r.points || []).slice(0, 3)].join(". ");
        setLast({ q, a: r.answer });
        speak(answer, lang, rate);
      } catch {
        speak("Backend not reachable.", lang, rate);
      }
    };
    rec.start();
  }

  if (!supported) return null;   // honest: no fake mic on unsupported browsers

  return (
    <div className="panel py-2">
      <div className="flex flex-wrap items-center gap-3 text-xs">
        <span className="panel-title">🎙 VOICE NARRATOR</span>
        {!unlocked && (
          <button onClick={() => {
              // user gesture → speaking here unlocks TTS for the whole page
              window.speechSynthesis?.getVoices();
              speak(lang === "ta-IN" ? "குரல் இயங்குகிறது. Narrator online."
                                     : "Voice check. Narrator online.", lang, rate);
              setUnlocked(true);
            }}
            className="px-3 py-1 rounded border border-terminal-bull text-terminal-bull text-xs font-bold animate-pulse">
            🔊 ENABLE SOUND (tap once)
          </button>
        )}
        <select value={mode} onChange={(e) => {
            const m = e.target.value as Mode;
            setMode(m);
            window.speechSynthesis?.cancel();
            // mode change is a gesture — confirm aloud (also primes TTS)
            if (m !== "SILENT") { speak(`Voice mode ${m.toLowerCase().replace("_", " ")}.`, lang, rate); setUnlocked(true); }
          }}
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
          <option value="ta-IN">தமிழ் + English (Tanglish)</option>
        </select>
        <select value={rate} onChange={(e) => setRate(parseFloat(e.target.value))}
                className="bg-transparent border border-terminal-border rounded px-1 py-0.5 text-xs">
          {[0.75, 1.0, 1.25, 1.5, 2.0].map((r) => <option key={r} value={r}>{r}×</option>)}
        </select>
        <label className="flex items-center gap-1 text-terminal-muted cursor-pointer text-[10px]">
          <input type="checkbox" checked={emergencyOverride}
                 onChange={(e) => setEmergencyOverride(e.target.checked)} />
          🚨 Emergency override
        </label>
        <button onClick={() => { setUnlocked(true); speakBriefing(); }}
                className="px-2 py-1 rounded border border-terminal-accent/60 text-terminal-accent text-xs">
          📻 BRIEFING
        </button>
        <button onClick={() => window.speechSynthesis?.cancel()}
                className="text-terminal-muted hover:text-terminal-bear">⏹ stop</button>
        <span className="text-[10px] text-terminal-muted">
          {unlocked ? "Dashboard thinks → voice speaks. Never decides."
                    : "⚠ Browser blocks sound until one tap — hit ENABLE SOUND first."}
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
