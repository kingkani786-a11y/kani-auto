"use client";
// ⚡ EARLY WARNING — the earliest catch, ABOVE HOT NOW.
// Every other layer sees a move after it starts; this one fires BEFORE:
// COILED = energy loading under a flat premium (loaded spring), IGNITING =
// the spring releasing right now. This is the anti-miss layer — it's what
// lets you be ready at ₹86 instead of chasing at ₹120. Deterministic;
// premium_radar._coil derives it from volume/OI/velocity already captured.

import { useEffect, useRef, useState } from "react";
import { api } from "@/lib/api";

function speak(text: string) {
  if (typeof window === "undefined" || !window.speechSynthesis) return;
  const u = new SpeechSynthesisUtterance(text);
  u.lang = "en-IN"; u.rate = 1.05;
  window.speechSynthesis.speak(u);
}

export function EarlyWarning() {
  const [items, setItems] = useState<any[]>([]);
  const [waves, setWaves] = useState<any[]>([]);
  const spoken = useRef<Set<string>>(new Set());

  useEffect(() => {
    const load = () =>
      api.premiumRadar(8).then((d: any) => {
        const ew: any[] = d?.early_warning || [];
        setItems(ew);
        setWaves(d?.chain_wave || []);
        // Announce each strike's IGNITION once — hands-free "look here NOW".
        for (const r of ew) {
          const key = `${r.strike}${r.type}`;
          if (r.coil?.state === "IGNITING" && !spoken.current.has(key)) {
            spoken.current.add(key);
            speak(`${r.strike} ${r.type} igniting. Earliest entry window.`);
          }
          // let a strike re-announce if it fully resets (no longer early)
        }
        const liveKeys = new Set(ew.map((r) => `${r.strike}${r.type}`));
        spoken.current.forEach((k) => { if (!liveKeys.has(k)) spoken.current.delete(k); });
      }).catch(() => {});
    load();
    const id = setInterval(load, 3000);
    return () => clearInterval(id);
  }, []);

  if (items.length === 0 && waves.length === 0) return null;

  return (
    <section className="panel space-y-2 border border-terminal-warn/40 bg-terminal-warn/[0.03]">
      <h2 className="text-sm font-semibold text-white flex items-center gap-2">
        ⚡ Early Warning
        <span className="text-[10px] text-terminal-muted">(loading / igniting — before it runs)</span>
      </h2>

      {/* 🌊 Chain-Wave — 3+ same-type strikes heating together = real direction.
          A coil inside a wave is corroborated, not a lone twitch. */}
      {waves.map((w, i) => (
        <div key={i}
          className={`flex items-center gap-2 text-[11px] rounded px-2 py-1 border ${
            w.type === "CE" ? "border-terminal-bull/50 bg-terminal-bull/10 text-terminal-bull"
                            : "border-terminal-bear/50 bg-terminal-bear/10 text-terminal-bear"}`}>
          <span className="font-bold">🌊 {w.label}</span>
          <span className="text-gray-200">{w.count} {w.type} strikes together{w.igniting ? ` · ${w.igniting} igniting` : ""}</span>
          <span className="ml-auto text-terminal-muted tabular-nums">{w.strikes?.slice(0, 4).join(" ")}</span>
        </div>
      ))}
      {items.length === 0 && (
        <div className="text-[11px] text-terminal-muted">Wave forming — no single strike coiled yet.</div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
        {items.map((r, i) => {
          const igniting = r.coil?.state === "IGNITING";
          return (
            <div key={i}
              className={`rounded border p-2 ${igniting
                ? "border-terminal-bull/60 bg-terminal-bull/10"
                : "border-terminal-border bg-terminal-bg/40"}`}>
              <div className="flex items-center justify-between">
                <span className="font-semibold text-white text-sm">
                  {r.coil?.dot} {r.strike} {r.type}
                </span>
                <span className={`text-[10px] font-bold tracking-wide ${igniting ? "text-terminal-bull" : "text-terminal-warn"}`}>
                  {r.in_wave && <span className="text-terminal-accent" title="Confirmed by chain-wave">🌊 </span>}
                  {r.coil?.state}{r.coil?.secs ? ` · ${r.coil.secs}s` : ""}
                </span>
              </div>
              <div className="flex items-center gap-2 mt-1 text-[11px] text-terminal-muted">
                <span className="tabular-nums text-white">₹{r.premium}</span>
                <span>vel {r.velocity}</span>
                <span>OI {r.oi_pct >= 0 ? "+" : ""}{r.oi_pct}%</span>
                <span className="ml-auto">energy {r.coil?.strength}</span>
              </div>
              <div className="h-1 bg-terminal-border rounded mt-1 overflow-hidden">
                <div className={`h-full ${igniting ? "bg-terminal-bull" : "bg-terminal-warn"}`}
                  style={{ width: `${r.coil?.strength || 0}%` }} />
              </div>
              <div className="text-[10px] text-terminal-muted mt-1 leading-snug">{r.coil?.note}</div>
            </div>
          );
        })}
      </div>
      <div className="text-[10px] text-terminal-muted">
        Earliest honest signal — energy building before the premium moves. Observation, not a buy order.
      </div>
    </section>
  );
}
