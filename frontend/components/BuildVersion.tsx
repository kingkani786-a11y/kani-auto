"use client";
// Build Version panel (owner request) — shows exactly which build is running so
// anyone can self-verify a deploy without trusting a claim. Frontend commit +
// build time come from /version.json (stamped at build); backend commit + AI
// provider come from /api/version.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

export function BuildVersion() {
  const [fe, setFe] = useState<any>(null);
  const [be, setBe] = useState<any>(null);

  useEffect(() => {
    fetch("/version.json", { cache: "no-store" }).then((r) => r.json()).then(setFe).catch(() => {});
    api.version().then(setBe).catch(() => {});
  }, []);

  const row = (label: string, value: React.ReactNode) => (
    <div className="flex justify-between gap-4">
      <span className="text-terminal-muted">{label}</span>
      <span className="text-white tabular-nums">{value ?? "—"}</span>
    </div>
  );
  const fmt = (iso?: string) => (iso ? iso.replace("T", " ").slice(0, 16) : "—");

  return (
    <section className="panel text-[11px] space-y-1">
      <div className="text-xs font-semibold text-white mb-1">🏷 Build Version</div>
      {row("Frontend", fe?.commit)}
      {row("Frontend built", fmt(fe?.builtAt))}
      {row("Backend", be?.backend_commit)}
      {row("AI Cortex", be?.ai_enabled ? `${be?.ai_provider} · ${be?.ai_model}` : "OFF")}
      {row("Radio", be?.radio)}
      {row("Service Worker", fe?.sw)}
    </section>
  );
}
