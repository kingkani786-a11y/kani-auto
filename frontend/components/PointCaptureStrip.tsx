"use client";
// 📊 OBSERVED OUTCOMES — what actually happened, not what might happen.
//
// This was "Point Capture", rendering a declared decay curve
// (100·exp(-0.7·pts/em)·(0.6+0.4·edge)) as a probability. Checked against the
// black box on 2026-07-21 it overstated reality 3× at 20pt and ~50× at 100pt:
// the strip showed "100pt 42%" when 9 of 1694 ignitions (0.5%) ever got there.
// Every other bug found that day HID information; this one manufactured
// opportunity, which is worse on a card a trader acts from.
//
// Owner's rule, adopted: history and prediction must never wear the same word.
// This shows OBSERVED FREQUENCY with its sample size and is explicitly not a
// forecast. A separate predictive engine (charter Layer 6) stays unbuilt.

import { useMarket } from "@/lib/store";

export function PointCaptureStrip() {
  const { decision } = useMarket();
  const pc = (decision as any)?.execution_card?.point_capture;
  const rows: any[] = pc?.rows || [];
  if (!rows.length) return null;

  const observed = !!pc?.observed;
  const n = pc?.sample_n ?? 0;

  return (
    <div className="panel py-2">
      <div className="flex items-center gap-2">
        <span className="stat-label shrink-0">
          {observed ? "Observed outcomes" : "Modelled (low sample)"}
        </span>
        <div className="flex-1 grid grid-cols-6 gap-1.5 text-center text-[11px]">
          {rows.map((p: any) => (
            <div key={p.points}>
              <div className="font-mono">{p.points}pt</div>
              {/* no colour-coded "good/bad" tiers and no ★ BEST pick — those
                  framed a backward-looking frequency as an opportunity call */}
              <div className="text-gray-200 tabular-nums">
                {p.reached_pct == null ? "—" : `${p.reached_pct}%`}
              </div>
              {p.reached != null && (
                <div className="text-terminal-muted text-[9px]">{p.reached}</div>
              )}
            </div>
          ))}
        </div>
      </div>
      <div className="text-[10px] text-terminal-muted mt-1">
        {observed
          ? `Of ${n.toLocaleString("en-IN")} past radar ignitions, this share went on to reach N points`
          : `Sample too small (${n}) — declared model, not observed`}
        {pc?.false_alert_pct != null && ` · ${pc.false_alert_pct}% of ignitions were false alerts`}
        {" · "}<span className="text-terminal-warn">historical frequency, NOT a prediction</span>
      </div>
    </div>
  );
}
