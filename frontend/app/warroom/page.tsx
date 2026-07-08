"use client";
// WAR ROOM — Buyer vs Seller (Layer 6). Reads war-room data already streamed
// in layers (no new fetch). Derivation-only; probabilities/strength, not calls.

import { useMarket } from "@/lib/store";

export default function WarRoomPage() {
  const { layers, status } = useMarket();
  const w = (layers as any)?.future?.war_room;

  if (status && !status.connected) return <div className="panel text-sm text-terminal-muted">Connect to open the War Room.</div>;
  if (!w) return <div className="panel text-sm text-terminal-muted">War Room loads with the first analysis cycle.</div>;

  const buyer = w.buyer_strength ?? 50;
  const seller = w.seller_strength ?? 50;

  return (
    <div className="space-y-4 max-w-3xl mx-auto">
      <section className="panel">
        <div className="panel-title">Buyer vs Seller — {w.dominance} in control</div>
        <div className="flex h-8 rounded-lg overflow-hidden bg-terminal-bg font-bold text-xs">
          <div className="bg-terminal-bull/70 flex items-center justify-center" style={{ width: `${buyer}%` }}>
            BUYERS {buyer}%
          </div>
          <div className="bg-terminal-bear/70 flex items-center justify-center" style={{ width: `${seller}%` }}>
            {seller}% SELLERS
          </div>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mt-4 text-sm">
          <div><div className="stat-label">Winning</div><div className={`stat-value ${w.winning === "BUYERS" ? "text-terminal-bull" : w.winning === "SELLERS" ? "text-terminal-bear" : ""}`}>{w.winning}</div></div>
          <div><div className="stat-label">Losing</div><div className="stat-value text-terminal-muted">{w.losing}</div></div>
          <div><div className="stat-label">Delta Imbalance</div><div className="stat-value">{w.delta_imbalance ?? "—"}</div></div>
          <div><div className="stat-label">Absorption</div><div className={`stat-value ${w.absorption ? "text-terminal-warn" : "text-terminal-muted"}`}>{w.absorption ? "Detected" : "No"}</div></div>
          <div><div className="stat-label">Exhaustion</div><div className={`stat-value ${w.exhaustion ? "text-terminal-warn" : "text-terminal-muted"}`}>{w.exhaustion ? "Detected" : "No"}</div></div>
          <div><div className="stat-label">PCR</div><div className="stat-value">{w.pcr ?? "—"}</div></div>
        </div>
      </section>

      <section className="panel">
        <div className="panel-title">Who Is Trapped?</div>
        <div className={`text-sm ${w.trapped && w.trapped !== "None detected" ? "text-terminal-bear" : "text-terminal-muted"}`}>
          {w.trapped}
        </div>
      </section>
    </div>
  );
}
