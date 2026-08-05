"use client";
// V3.0 — Smart Alert Bar. Sticky one-line banner showing the single most recent
// critical alert (entry window / kill switch / feed). Freshness is tracked
// client-side by alert id (backend ts is a display string). Auto-hides after
// 3 minutes or on dismiss; never stacks or duplicates. Existing alert stream only.

import { useEffect, useState } from "react";
import { useMarket } from "@/lib/store";

const CRITICAL = ["ENTRY", "SL"];   // entry-window + kill-switch/feed alerts
const MAX_AGE_MS = 180_000;

export function SmartAlertBar() {
  const { alerts, status, killSwitch } = useMarket();
  const [seen, setSeen] = useState<{ id: string; at: number } | null>(null);
  const [dismissed, setDismissed] = useState<string>("");
  const [, tick] = useState(0);
  useEffect(() => { const t = setInterval(() => tick((n) => n + 1), 5000); return () => clearInterval(t); }, []);

  const latest = (alerts || []).find((a: any) => CRITICAL.includes(a.kind));

  // record arrival time of each new critical alert (id change = new alert)
  useEffect(() => {
    if (latest && latest.id !== seen?.id) setSeen({ id: latest.id, at: Date.now() });
  }, [latest?.id]);   // eslint-disable-line react-hooks/exhaustive-deps

  if (!latest || !seen || seen.id !== latest.id) return null;
  if (Date.now() - seen.at > MAX_AGE_MS) return null;
  if (dismissed === latest.id) return null;
  // feed-quality alert self-clears the moment quality recovers (no stale POOR
  // banner while the system strip says GOOD).
  // OBS-12 fix (owner, 2026-08-05) — status?.data_quality is source A
  // (state.data_quality), NOT source B (data_quality.report().overall,
  // what Kill Switch/the gate actually run on). Suppressing on A alone
  // could auto-hide a genuine feed-quality alert while B (and therefore
  // the actual Execution Lock) still says POOR. Require B to agree too,
  // via the already-computed killSwitch.reason_tags — no new fetch.
  const bDataQualityPoor = (killSwitch?.reason_tags || []).includes("DATA_QUALITY");
  if (/feed quality/i.test(latest.title || "")
      && (status as any)?.data_quality === "GOOD" && !bDataQualityPoor) return null;

  const isEntry = latest.kind === "ENTRY";
  return (
    <div className={`sticky top-14 z-30 rounded-lg border px-3 py-2 flex items-center justify-between gap-3 text-sm backdrop-blur
      ${isEntry ? "border-terminal-bull/60 bg-terminal-bull/15 text-terminal-bull"
                : "border-terminal-bear/60 bg-terminal-bear/15 text-terminal-bear"}`}>
      <span className="font-bold truncate">{isEntry ? "🔔" : "⚠️"} {latest.title}
        {latest.body ? <span className="font-normal text-gray-300"> — {latest.body}</span> : null}
      </span>
      <button onClick={() => setDismissed(latest.id)}
        className="text-terminal-muted hover:text-white text-xs shrink-0">✕</button>
    </div>
  );
}
