"use client";
// V13 AI Market Narrator — concise 4–6 line plain-language read. Composed from
// existing engine outputs (display only); deliberately avoids repeating the
// BUY CALL / levels already shown in the Final Signal Banner.

import { useMarket } from "@/lib/store";

export function MarketNarratorPanel() {
  const { decision: d, layers, signal } = useMarket();
  const L = layers as any;

  const lines: string[] = [];
  const bias = L?.global_context?.bias;
  const regime = L?.regime?.regime;
  const strength = L?.market_strength?.label;
  const mom = Number(signal?.tech?.momentum ?? 0);
  const cap = L?.capital_protection;

  // Hybrid Tamil + trading-English (display only; terms/levels stay English).
  if (regime) lines.push(`சந்தை தற்போது ${String(regime).replace(/_/g, " ").toLowerCase()} regime-ல் உள்ளது${bias && bias !== "NEUTRAL" ? `, ${bias.toLowerCase()} lean-உடன்` : ""}.`);
  if (strength) lines.push(`Underlying strength தற்போது ${String(strength).replace(/_/g, " ").toLowerCase()}-ஆக உள்ளது.`);
  if (Number.isFinite(mom) && mom !== 0) lines.push(`Momentum ${mom > 0.1 ? "upside-ல் உருவாகிக்கொண்டிருக்கிறது" : mom < -0.1 ? "downside-ல் rollover ஆகிறது" : "flat-ஆக உள்ளது"}.`);
  // V13.1 futures confirmation context
  const fut = L?.futures;
  if (fut?.buildup && fut.buildup !== "Neutral") {
    lines.push(`Futures பகுதியில் ${fut.buildup.toLowerCase()} காணப்படுகிறது${fut.relation === "CONFIRMS" ? " — signal-ஐ support செய்கிறது" : fut.relation === "CONTRADICTS" ? " — signal-க்கு எதிராக உள்ளது" : ""}.`);
  }
  if (cap?.category) lines.push(`Capital risk தற்போது ${String(cap.category).toLowerCase()}${cap.action && cap.action !== "NORMAL" ? ` — ${cap.action.replace(/_/g, " ").toLowerCase()}` : ""}.`);
  if (d?.action) {
    lines.push(d.is_trade
      ? `பரிந்துரை: நிலை நீடிக்கும் வரை ${d.action}.`
      : `பரிந்துரை: stand aside — ${d.reason || "qualifying edge இல்லை"}.`);
  }

  return (
    <section className="panel">
      <div className="panel-title">AI Market Narrator</div>
      {lines.length === 0 ? (
        <p className="text-sm text-terminal-muted">Reading the tape… narration appears after the first analysis cycle.</p>
      ) : (
        <ul className="space-y-1.5 text-sm leading-relaxed">
          {lines.slice(0, 6).map((l, i) => (
            <li key={i} className="flex gap-2">
              <span className="text-terminal-accent shrink-0">›</span>
              <span className={i === lines.length - 1 ? "text-white font-medium" : "text-gray-300"}>{l}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
