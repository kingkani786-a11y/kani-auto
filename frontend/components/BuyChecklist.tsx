"use client";
// ✅ BUY CHECKLIST — ONE component, ONE backend object, rendered in both the
// Trade Now hero and AI Thinking (owner 2026-07-21: "Hero மற்றும் AI Thinking
// இரண்டும் ஒரே backend object-ஐ render செய்ய வேண்டும்"). Before this, the hero
// rendered decision_contract's 4 booleans while AI Thinking rendered the
// radar's own 4 DIFFERENT checks — two things both called "the checklist"
// that could disagree on screen at the same instant.
//
// Three states, not two:
//   ✔ pass · ✗ fail · ○ NOT MEASURED
// ○ exists because honesty outranks a tidy UI: Structure has no Market
// Structure Engine yet, so it is not measured — showing it as ✗ would claim
// evidence of failure we do not have.

export function BuyChecklist({ c, compact = false }: { c: any; compact?: boolean }) {
  const items: any[] = Array.isArray(c?.buy_checklist) ? c.buy_checklist : [];
  if (items.length === 0) return null;
  const s = c?.buy_checklist_score;

  return (
    <div>
      <div className="flex items-baseline justify-between mb-0.5">
        <span className="text-[10px] font-semibold text-terminal-muted uppercase tracking-wide">BUY Checklist</span>
        {s && (
          <span className="text-[10px] text-terminal-muted tabular-nums">
            {s.passed}/{s.measured} passed
            {s.total > s.measured ? ` · ${s.total - s.measured} not measured` : ""}
          </span>
        )}
      </div>
      <ul className={`text-xs text-gray-200 ${compact ? "grid grid-cols-2 gap-x-3" : "space-y-0.5"}`}>
        {items.map((it) => {
          const mark = it.ok === true ? "✔" : it.ok === false ? "✗" : "○";
          const tone = it.ok === true ? "text-terminal-bull"
            : it.ok === false ? "text-terminal-bear" : "text-terminal-muted";
          return (
            <li key={it.key} className="flex gap-1.5" title={it.note || ""}>
              <span className={tone}>{mark}</span>
              <span className={it.ok === null || it.ok === undefined ? "text-terminal-muted" : ""}>{it.label}</span>
            </li>
          );
        })}
      </ul>
    </div>
  );
}
