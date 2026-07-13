"use client";
// 🏆 CAPTURE SCORE — the 'Measure' step, system-measured not eyeballed.
// The one number that says whether the software is actually getting better:
// Opportunity Capture Rate, plus Detection Delay, Alert Accuracy and today's
// Missed Money. Read-only instrumentation; never a trade instruction.

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

const pct = (v: any) => (v === null || v === undefined ? "—" : `${v}%`);

export function CaptureScore() {
  const [d, setD] = useState<any>(null);
  useEffect(() => {
    const load = () => api.opportunityMetrics().then(setD).catch(() => {});
    load();
    const id = setInterval(load, 15000);
    return () => clearInterval(id);
  }, []);

  if (!d) return null;
  const sampled = (d.sample ?? 0) > 0;
  const cr = d.capture_rate;
  const crColor = cr === null ? "text-terminal-muted"
    : cr >= 75 ? "text-terminal-bull" : cr >= 50 ? "text-terminal-warn" : "text-terminal-bear";
  const delay = d.avg_detection_delay_s;
  const delayLabel = delay === null ? "—"
    : delay <= 0 ? `${Math.abs(delay)}s early` : `${delay}s late`;
  const delayColor = delay === null ? "text-terminal-muted"
    : delay <= 5 ? "text-terminal-bull" : delay <= 20 ? "text-terminal-warn" : "text-terminal-bear";

  return (
    <section className="panel space-y-3">
      <div className="flex items-center justify-between">
        <h2 className="text-sm font-semibold text-white">🏆 Capture Score <span className="text-[10px] text-terminal-muted">(system-measured · the Measure step)</span></h2>
        <span className="text-[10px] text-terminal-muted">{d.day}</span>
      </div>

      {!sampled ? (
        <div className="text-xs text-terminal-muted">
          No completed opportunities measured yet today — fills in as strikes move. (Market {d.runners_total === 0 ? "quiet / closed" : "warming up"}.)
        </div>
      ) : (
        <>
          <div className="flex items-end gap-4">
            <div>
              <div className={`text-4xl font-bold tabular-nums leading-none ${crColor}`}>{pct(cr)}</div>
              <div className="text-[10px] text-terminal-muted mt-1">Opportunity Capture Rate</div>
            </div>
            <div className="flex-1 grid grid-cols-3 gap-1 text-center">
              <div className="rounded border border-terminal-bull/30 bg-terminal-bull/10 py-1">
                <div className="text-lg font-bold tabular-nums text-terminal-bull">{d.detected_early}</div>
                <div className="text-[9px] text-terminal-muted">EARLY</div>
              </div>
              <div className="rounded border border-terminal-warn/30 bg-terminal-warn/10 py-1">
                <div className="text-lg font-bold tabular-nums text-terminal-warn">{d.detected_late}</div>
                <div className="text-[9px] text-terminal-muted">LATE</div>
              </div>
              <div className="rounded border border-terminal-bear/30 bg-terminal-bear/10 py-1">
                <div className="text-lg font-bold tabular-nums text-terminal-bear">{d.missed_completely}</div>
                <div className="text-[9px] text-terminal-muted">MISSED</div>
              </div>
            </div>
          </div>

          <div className="grid grid-cols-4 gap-2 text-center border-t border-terminal-border pt-2">
            <div>
              <div className={`text-sm font-semibold tabular-nums ${delayColor}`}>{delayLabel}</div>
              <div className="text-[9px] text-terminal-muted">Detection delay <span className="opacity-70">(≤5s goal)</span></div>
            </div>
            <div>
              <div className="text-sm font-semibold tabular-nums text-white">{pct(d.alert_accuracy)}</div>
              <div className="text-[9px] text-terminal-muted">Alert accuracy <span className="opacity-70">({d.false_alerts}/{d.alerts_total} false)</span></div>
            </div>
            <div>
              <div className="text-sm font-semibold tabular-nums text-white">{d.avg_stability === null || d.avg_stability === undefined ? "—" : d.avg_stability}</div>
              <div className="text-[9px] text-terminal-muted">Prediction stability <span className="opacity-70">(smooth=high)</span></div>
            </div>
            <div>
              <div className="text-sm font-semibold tabular-nums text-white">{d.runners_total}</div>
              <div className="text-[9px] text-terminal-muted">Runners today</div>
            </div>
          </div>

          {d.recovered_pct !== null && d.recovered_pct !== undefined && (
            <div className="border-t border-terminal-border pt-2">
              <div className="flex items-center justify-between text-[10px] text-terminal-muted mb-1">
                <span>Money recovered vs the peak that was available</span>
                <span className="tabular-nums"><b className="text-terminal-bull">{d.recovered_pct}%</b> got · <span className="text-terminal-bear">{d.lost_pct}% lost</span></span>
              </div>
              <div className="h-2 bg-terminal-bear/25 rounded overflow-hidden">
                <div className="h-full bg-terminal-bull" style={{ width: `${d.recovered_pct}%` }} />
              </div>
            </div>
          )}

          {d.missed_money?.length > 0 && (
            <div className="border-t border-terminal-border pt-2">
              <div className="text-[10px] text-terminal-muted mb-1">💸 Today's missed money (potential vs captured)</div>
              <div className="space-y-1">
                {d.missed_money.slice(0, 3).map((m: any, i: number) => (
                  <div key={i} className="flex items-center gap-2 text-[11px]">
                    <span className="w-20 text-white">{m.strike} {m.type}</span>
                    <span className="text-terminal-muted">pot <b className="text-white">+{m.potential}</b></span>
                    <span className="text-terminal-bull">got +{m.captured}</span>
                    <span className="ml-auto text-terminal-bear">lost {m.lost}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </>
      )}
      <div className="text-[10px] text-terminal-muted">{d.note}</div>
    </section>
  );
}
