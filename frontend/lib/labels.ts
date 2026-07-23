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
export const DISPLAY_LABEL: Record<string, string> = {
  "Kill Switch": "Execution Lock",
};

/** Map a bare label/name (e.g. a checklist row name, a Tile label) for display. */
export function displayLabel(name: string | undefined | null): string {
  if (!name) return name ?? "";
  return DISPLAY_LABEL[name] ?? name;
}

/**
 * Map a backend reason STRING that may carry a "Kill Switch: <reason>" prefix
 * (execution_gate.blocking_reasons format: `f"{c['name']}: {c['reason']}"`,
 * execution_gate.py:120) to its display form. Only the prefix is rewritten;
 * the reason text itself (which never contains the label) is untouched.
 */
export function displayReason(reason: string | undefined | null): string {
  if (!reason) return reason ?? "";
  return reason.replace(/^Kill Switch:/, "Execution Lock:");
}

/** Map every string in a blocking_reasons / waiting_on array for display. */
export function displayReasons(reasons: (string | undefined | null)[] | undefined | null): string[] {
  return (reasons || []).map((r) => displayReason(r));
}
