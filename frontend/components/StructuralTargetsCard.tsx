"use client";
// STRUCTURAL TARGETS — V7.1 Trade Explorer Phase 3A (owner, 2026-08-04).
//
// MEASUREMENT ONLY. The engine trades fixed ATR-multiple targets
// (SL 1.0x, T1/T2/T3 = 2.0/3.0/4.5x ATR) — confluence.py:397-404, unchanged
// by this card. This shows where the REAL touch/bounce-scored S/R levels sit
// so the two can be compared on live data, before anyone proposes changing
// the traded targets (that is Phase 3B — separate approval, since the traded
// T1 feeds the reward:risk veto directly).
//
// BOUNDARIES, deliberate:
//   * Reads `layers.structural_targets`, which changes no target, stop,
//     score or gate. Remove the backend block and the decision is
//     byte-identical (proven: present-vs-stubbed packet comparison).
//   * When S/R is not available, this renders nothing but "UNAVAILABLE" —
//     never an ATR value relabelled as a structural one.
//   * Every strength/touch/bounce number is the S/R engine's OWN value,
//     the same one the S/R panel and Exit Intelligence already show.
//   * Rule 11 intact: no BUY/SELL, no instruction, no second verdict.

import { useMarket } from "@/lib/store";

export function StructuralTargetsCard() {
  const { layers } = useMarket();
  const st = (layers as any)?.structural_targets;
  if (!st) return null;

  const dirTone = st.direction === "BULL" ? "text-terminal-bull"
                 : st.direction === "BEAR" ? "text-terminal-bear"
                 : "text-terminal-muted";

  if (!st.available) {
    return (
      <div className="panel py-2.5 space-y-1 text-[11px]">
        <div className="flex items-center justify-between">
          <span className="font-bold tracking-wider text-terminal-accent">
            STRUCTURAL TARGETS
          </span>
          <span className="text-terminal-muted font-semibold">UNAVAILABLE</span>
        </div>
        <div className="text-terminal-muted">{st.reason || "S/R engine not ready."}</div>
        <div className="text-[10px] text-terminal-muted">
          Measurement only — no ATR value is ever shown under a structural
          label. The traded targets are unaffected either way.
        </div>
      </div>
    );
  }

  const rows: any[] = st.comparison || [];

  return (
    <div className="panel py-2.5 space-y-2 text-[11px]">
      <div className="flex items-center justify-between flex-wrap gap-2">
        <span className="font-bold tracking-wider text-terminal-accent">
          STRUCTURAL TARGETS <span className="text-terminal-muted font-normal">(measurement — not the traded targets)</span>
        </span>
        <span className={`font-bold ${dirTone}`}>{st.direction}</span>
      </div>

      {rows.length > 0 ? (
        <div className="overflow-x-auto">
          <table className="w-full text-[11px]">
            <thead>
              <tr className="text-terminal-muted text-[10px] uppercase tracking-wide">
                <th className="text-left font-normal pr-3">Tier</th>
                <th className="text-right font-normal pr-3">ATR (traded)</th>
                <th className="text-right font-normal pr-3">Structure (observed)</th>
                <th className="text-right font-normal">Δ</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((c) => (
                <tr key={c.tier} className="border-t border-terminal-border/30">
                  <td className="pr-3 text-terminal-muted">{c.tier}</td>
                  <td className="pr-3 text-right tabular-nums">{c.atr_pts} pts</td>
                  <td className="pr-3 text-right tabular-nums">
                    {c.structural_pts} pts
                    <span className="text-terminal-muted"> {c.structural_label}</span>
                  </td>
                  <td className={`text-right tabular-nums font-semibold ${c.structural_is_nearer ? "text-terminal-warn" : "text-terminal-muted"}`}>
                    {c.delta_pts > 0 ? "+" : ""}{c.delta_pts}
                    {c.structural_is_nearer ? " nearer" : ""}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="text-terminal-muted">No comparison — traded targets unavailable this cycle.</div>
      )}

      <div className="space-y-0.5">
        {(st.targets || []).map((t: any) => (
          <div key={t.label} className="text-terminal-muted">
            <span className="font-semibold text-gray-200">{t.label}</span> {t.level}
            {" · "}{t.touches} touches · {t.bounce_pct}% bounce
            {t.established ? " · established" : " · forming"}
          </div>
        ))}
      </div>

      <div className="text-[10px] text-terminal-muted pt-1 border-t border-terminal-border/40">
        The engine trades the ATR column — this changes no target, stop or
        gate. Same touch/bounce-scored levels the S/R panel and Exit
        Intelligence already use. No claim that structure is better; that
        needs outcome data this has not collected yet.
      </div>
    </div>
  );
}
