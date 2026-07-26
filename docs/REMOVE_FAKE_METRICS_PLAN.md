# Remove Fake Metrics — Step 8 Plan (V7.0 Roadmap)

Date: 2026-07-26
Status: **IMPLEMENTED — owner signed off on all 4 questions, display/disclosure-only scope. Backend compile+import clean, frontend typecheck+production build clean, live browser interactive test of the new breakdown toggle confirmed working.**

## What shipped

1. **EntryFirstDeck's 4-chip row** → consolidated to ONE primary "Confidence" chip + "Trade Quality" grade, with a "Breakdown" toggle button that expands to show Signal Score / Execution / Entry Probability, each with a plain-language description of what it actually measures and an explicit closing disclosure: "All declared formula blends of real inputs — none are validated/calibrated probabilities." Verified interactively in a live browser — toggle expands/collapses correctly.
2. **TradeNowCard's bare "Confidence %"** now carries a tooltip disclosure ("Declared confidence blend — not a validated/backtested probability").
3. **3 dropped-disclosure-note bugs fixed**: `MarketPathPanel.tsx` (`live_note || note` was permanently shadowing the real disclaimer since `live_note` is always truthy — both now shown), `CandleProjection.tsx` and `ConfidenceEvolution.tsx` (backend `note` fields computed but never read — now rendered).
4. **`OpportunityBoard.tsx`'s "AI Score"** now has a tooltip disclosing it's a declared 50/50 blend, not a validated AI rating.
5. **"AI Confidence Calibration" naming collision fixed** — `confluence.py`'s Engine 10 gate (5 declared thresholds, unrelated to the real outcome-based `calibration_score`) had its user-facing label changed from "CALIBRATION" to "SIGNAL GATE" in both the veto string and `DecisionMatrix.tsx`'s display, with a tooltip explaining the distinction. The backend dict key (`calibration`) was left as-is to avoid a wider payload change — only text a user reads was changed. **No threshold or gating behavior was touched.**
6. **`probability.py`'s docstring fixed** — no longer calls its declared logistic formula "calibrated" (a word this project reserves for the real, outcome-validated calibration). Pure documentation change, zero behavior change.
7. **`brain.py`'s chat-assistant confidence** — relabeled in the UI from "confidence N%" to "answer confidence N%" with a tooltip clarifying it's the brain's own self-assessed certainty in its answer (a mix of real signal-derived values and static per-template estimates), not a validated trading probability. The ~20 individual hardcoded literals inside `brain.py` were left as-is (rewriting each would require re-deriving what a "correct" number would be for each of 20 different answer templates — a much larger, separate undertaking); the fix here is honest labeling of what the number already is.

## What was explicitly NOT touched (per the confirmed scope boundary)

No gating threshold, veto condition, or trade-blocking logic was changed anywhere — not in `confluence.py`'s `dynamic_confidence<60` veto, not in `execution_gate.py`'s compound "Trade Confidence Lock", not in `signal_maturity.py`'s `buy_allowed` gate. These remain exactly as they were; changing them requires the full Observation→Evidence→Proposal→Approval pipeline this project's own Trading Doctrine already mandates, not a metrics-honesty pass.

Owner's rule: no fabricated Probability/Confidence/AI score anywhere;
Observed Data only.

## Critical scope boundary — read this first

The audit found two different classes of problem, and **only one of them is
safe for this step to touch**:

1. **Display/disclosure honesty** — a number is shown without telling the
   user it's a declared heuristic, not a validated probability; or the same
   concept is labeled differently in different panels; or a backend
   disclosure note exists but a frontend bug drops it before it reaches the
   screen. **Fixing these changes nothing about how any trade is decided —
   only what the user is told about a number that already exists.** Safe to
   do in this pass.

2. **Gating logic** — several of these same undisclosed heuristics are
   wired into REAL veto/allow decisions (e.g. a hard "NO TRADE" if a score
   is below 60, or a compound "Trade Confidence Lock" requiring 4 thresholds
   at once). **This project's own Decision Doctrine already protects exactly
   this category**: "TRADING DOCTRINE (market) — RESEARCH PARAMETERS...
   Confidence threshold... these are NOT constitution — they are hypotheses.
   With repeated evidence they MAY change, but only through the approval
   pipeline" (Observation → Evidence → Proposal → Approval → Deployment →
   Monitoring). **Changing what actually gates a trade is out of scope for
   a metrics-honesty cleanup — that requires the full evidence pipeline, not
   a doc-review pass.** I am not proposing to touch any gating threshold or
   veto logic in this step. Where a gate exists, my proposal is limited to
   making its own documentation/comments honest about what it is (a declared
   heuristic, not a validated calibration) — never changing the threshold or
   removing the gate itself.

## Findings — safe to fix (display/disclosure only)

**1. The confirmed centerpiece (you already flagged this in Step 2): `EntryFirstDeck.tsx`'s 4-chip row.** Four different numbers, no disclosure, near-identical names hiding different math:
   - "Confidence" ← `signal.dynamic_confidence` (a 5-factor blend)
   - "Signal Score" ← `signal.confidence` (a *different*, 7-factor blend — despite the near-identical name)
   - "Execution" ← `strike.selection_score` (a 5-factor strike-quality blend)
   - "Entry Probability" ← `layers.entry_probability.score` (a 10-input blend, banded into text labels)
   
   None are fabricated from nothing — all are declared, formula-based blends of real inputs — but none disclose that, and showing 4 of them side by side with overlapping names is the exact "which number do I trust" pattern this step should end.

**2. A 5th undisclosed sibling, not on your list**: `TradeNowCard.tsx` — the Hero card itself — shows a bare "Confidence %" directly above its own properly-disclosed "Evidence /100" ledger. Same card, inconsistent treatment.

**3. Disclosure notes written in the backend but silently dropped by a frontend bug** (the backend did the honest thing; a rendering bug hid it):
   - `MarketPathPanel.tsx`: `{mp.live_note || mp.note}` — the real disclosure note is permanently shadowed by a different field that's always truthy.
   - `CandleProjection.tsx`: the backend's `cp.note` is never read at all — "~95% range" shown with no qualifier.
   - `ConfidenceEvolution.tsx`: same pattern, `ce.note` never read.

**4. Literal "AI Score" styling with no disclosure**: `OpportunityBoard.tsx` shows "AI 82" (a 50/50 blend of two other undisclosed heuristics) with no note that it's a declared blend, not a validated AI-confidence rating.

**5. A pure naming collision, same class as Step 6's "Price Action" fix**: `confluence.py`'s internal "AI Confidence Calibration" (Engine 10 — 5 arbitrary threshold checks) shares the word "calibration" with `services/analytics.py`'s REAL, outcome-based `calibration_score`. These are unrelated computations; the name collision could make someone think the gate is backed by real settled-outcome data when it's a declared heuristic. **Proposing a rename only** (e.g. to "Signal Quality Gate" or similar) — not touching what it does or its thresholds.

**6. A dishonest code comment (zero behavior change to fix)**: `probability.py`'s `prob_success` is called "calibrated" in its own comment, but it's a declared logistic formula, not validated against real outcomes. Proposing to fix the comment to say what it actually is — this is documentation, not logic, and doesn't touch the value or the fact that it currently gates trades at <60 (that gate itself is out of scope, per the boundary above).

**7. `brain.py`'s chat-assistant confidence** — the AI Q&A brain (a separate feature from the trading decision pipeline) frequently returns a bare hardcoded confidence literal (30/60/65/70/80…) per answer template, shown as "confidence 70%" in the Brain page. This is the chat assistant's own self-reported certainty in its *answer*, not a trading signal — lower stakes, but still an unearned-looking number. Flagging for your call on priority.

## What I am explicitly NOT proposing to touch

- The actual gating thresholds in `confluence.py` (dynamic_confidence<60 veto), `execution_gate.py` (the compound "Trade Confidence Lock": conviction≥80/fire≥85/trade_quality≥800/institutional≥70), or `signal_maturity.py` (false_signal_probability gating buy_allowed). These are live Trading Doctrine parameters — changing them needs the full Observation→Evidence→Proposal→Approval pipeline, not this cleanup pass.

## Sign-off needed

1. Confirm the scope boundary above (display/disclosure only, zero gating-logic changes) before I touch anything.
2. **EntryFirstDeck's 4-chip row** — how should this resolve? Options: (a) reduce to ONE clearly-labeled number with the others available as a tooltip breakdown, (b) keep all 4 but add clear distinct labels/tooltips disclosing what each measures and that none are validated probabilities, (c) something else.
3. Confirm the 3 dead-disclosure-note bugs (MarketPathPanel/CandleProjection/ConfidenceEvolution) get fixed so real backend honesty actually reaches the screen.
4. Confirm the "AI Confidence Calibration" → rename (to avoid the real-calibration-score collision) and the `probability.py` comment fix.
5. Priority on `brain.py`'s hardcoded chat-confidence literals — fix now, or defer?
