// Display-label mapping — Execution Lock rename (owner, 2026-07-23, item #3).
//
// "Kill Switch" ⟶ "Execution Lock" is a UI LABEL change only. The internal
// identifier stays "Kill Switch" everywhere in the backend — execution_gate.py
// (add("Kill Switch", ...) at execution_gate.py:34) and missed_winner.py:92
// string-MATCH the literal text "Kill Switch" to attribute a block to the
// capital-protection gate; renaming those strings breaks that attribution.
// So every backend field (killSwitch.*, blocking_reasons entries prefixed
// "Kill Switch: ...", conditions[].name === "Kill Switch") keeps its exact
// value — this module only transforms what gets RENDERED, at the last
// possible step, and nowhere else.
/**
 * Substring replace, not exact-match: risk_approval.py:59 emits the compound
 * literal "Daily risk / Kill Switch" as a checklist row name — an exact-match
 * dict lookup silently passed it through unmapped (caught 2026-07-23 from a
 * live dashboard capture showing raw "Kill Switch" in Risk Approval and the
 * Top Blocker stat). Any future compound label containing the term is now
 * covered without needing its own dict entry.
 */
export function displayLabel(name: string | undefined | null): string {
  if (!name) return name ?? "";
  return name.replace(/Kill Switch/g, "Execution Lock");
}

/**
 * Map a backend reason/blocker STRING for display. Originally anchored to only
 * the "Kill Switch: <reason>" prefix format (execution_gate.blocking_reasons,
 * execution_gate.py:120) — too narrow: risk_approval.py's blockers array can
 * carry the bare compound "Daily risk / Kill Switch" with no colon, which the
 * anchored regex silently passed through unmapped (2026-07-23 live capture).
 * Same substring replace as displayLabel; kept as a separate export since
 * call sites read as "reason" vs "label" and may diverge later.
 */
export function displayReason(reason: string | undefined | null): string {
  return displayLabel(reason);
}

/** Map every string in a blocking_reasons / waiting_on array for display. */
export function displayReasons(reasons: (string | undefined | null)[] | undefined | null): string[] {
  return (reasons || []).map((r) => displayReason(r));
}
