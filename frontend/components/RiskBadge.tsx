"use client";
// V13 risk chip — highly visible coloured badge. Display only; maps the
// existing risk_level / capital-protection category to a clear status.

const MAP: Record<string, { emoji: string; text: string; cls: string }> = {
  LOW: { emoji: "🟢", text: "LOW RISK", cls: "bg-terminal-bull/15 text-terminal-bull border-terminal-bull/40" },
  SAFE: { emoji: "🟢", text: "LOW RISK", cls: "bg-terminal-bull/15 text-terminal-bull border-terminal-bull/40" },
  MEDIUM: { emoji: "🟡", text: "MODERATE RISK", cls: "bg-terminal-warn/15 text-terminal-warn border-terminal-warn/40" },
  MODERATE: { emoji: "🟡", text: "MODERATE RISK", cls: "bg-terminal-warn/15 text-terminal-warn border-terminal-warn/40" },
  ACCEPTABLE: { emoji: "🟡", text: "MODERATE RISK", cls: "bg-terminal-warn/15 text-terminal-warn border-terminal-warn/40" },
  ELEVATED: { emoji: "🟠", text: "ELEVATED RISK", cls: "bg-orange-500/15 text-orange-400 border-orange-500/40" },
  HIGH: { emoji: "🟠", text: "ELEVATED RISK", cls: "bg-orange-500/15 text-orange-400 border-orange-500/40" },
  CRITICAL: { emoji: "🔴", text: "CRITICAL RISK", cls: "bg-terminal-bear/15 text-terminal-bear border-terminal-bear/40" },
  NONE: { emoji: "⚪️", text: "NO RISK", cls: "bg-terminal-border/30 text-terminal-muted border-terminal-border" },
};

export function RiskBadge({ level, size = "md" }: { level?: string; size?: "sm" | "md" }) {
  const m = MAP[(level || "NONE").toUpperCase()] ?? MAP.NONE;
  const pad = size === "sm" ? "px-2 py-0.5 text-[10px]" : "px-3 py-1 text-xs";
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-full border font-bold tracking-wide ${pad} ${m.cls}`}>
      <span>{m.emoji}</span>{m.text}
    </span>
  );
}
