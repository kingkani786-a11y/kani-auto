"use client";
// System Verify (owner request) — one honest health view. Each subsystem's
// status is derived from live state (paused/off on a closed market is expected,
// not a fault). The health score is computed from core subsystems only, so it
// can't be faked. "Trust by Verification, not by Claims."

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const DOT: Record<string, string> = {
  ok: "🟢", paused: "🟡", degraded: "🟡", off: "🔴", client: "🔵", building: "⚪",
};
const scoreTone = (s: number) =>
  s >= 90 ? "text-terminal-bull" : s >= 60 ? "text-terminal-warn" : "text-terminal-bear";

export function SystemVerify() {
  const [d, setD] = useState<any>(null);
  useEffect(() => {
    const load = () => api.systemVerify().then(setD).catch(() => {});
    load(); const t = setInterval(load, 15000); return () => clearInterval(t);
  }, []);
  if (!d) return null;

  return (
    <section className="panel space-y-2">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white">🩺 System Verify</h2>
        <div className="text-right">
          <span className={`text-lg font-bold ${scoreTone(d.health_score)}`}>{d.health_score}%</span>
          <span className="text-[11px] text-terminal-muted ml-1">{d.health_label}</span>
        </div>
      </div>
      {d.os_status && (
        <div className="text-xs border border-terminal-border rounded p-2">
          <span className="text-white font-medium">{d.os_status}</span>
          {d.os_substatus && <span className="text-terminal-muted"> · {d.os_substatus}</span>}
          {d.next_session && <span className="text-terminal-muted"> · next live {d.next_session}</span>}
        </div>
      )}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-4 gap-y-1 text-xs">
        {(d.subsystems || []).map((s: any) => (
          <div key={s.name} className="flex items-center gap-2">
            <span>{DOT[s.status] || "⚪"}</span>
            <span className="text-white">{s.name}</span>
            <span className="text-terminal-muted truncate">— {s.detail}</span>
          </div>
        ))}
      </div>
      <div className="text-[10px] text-terminal-muted">{d.note}</div>
    </section>
  );
}
