# Explainability Final — Step 9 Plan (V7.0 Roadmap)

Date: 2026-07-27
Status: **IMPLEMENTED — owner signed off on all 4 decisions + 2 found bugs. Backend compile+import clean, direct behavioral tests of both BUY and WAIT scenarios pass (including the voice narration), frontend typecheck+production build clean.** (Live browser check confirmed the new panel gracefully renders nothing against the still-running pre-Step-9 backend — expected, since restart stays deferred to your planned batch — so full visual confirmation of `AIDealerPanel` and the live voice output will happen once you restart.)

## What shipped

**New `decision_contract.py` fields** (`ai_dealer`, extended `invalidations`):
- `_ai_dealer()` — a pure-narrator function reading ONLY already-computed fields (Hero's own `execution_gate`/`premium_plan`, the S/R engine's real CPR pivot + nearest resistance, `structure.py`'s real `bos_choch`, the Decision Matrix's real Volume Profile/Liquidity rows, `risk_approval.py`'s real approval status). Zero new computation. Produces exactly: WHY BUY (6 items), WHY NOT BUY (only the reasons actually active — never padded with inactive ones), NEXT LEVEL (Next Resistance/Next Premium Target/Gamma Wall — OI Wall dropped per your decision), INVALIDATION.
- `_invalidations()` extended with the 2 new conditions (CPR lost, Swing broken) using real, already-computed data threaded across a module boundary it didn't previously cross.
- Verified with direct synthetic tests: a realistic BUY scenario correctly evaluated all 6 WHY BUY items and produced real Next Resistance (25103, matching Step 3's own test data) and Next Premium Target; a WAIT scenario correctly populated all 5 WHY NOT BUY items only when genuinely active; both degrade to honest nulls with no candle/gamma data, never fabricating.

**New `frontend/components/AIDealerPanel.tsx`** — renders the 4 sections exactly, styled consistently with `EvidencePanel.tsx`/`TradeRiskPanel.tsx`, never shows a competing verdict (only restates the Hero's own `verdict`/`is_buy`). Wired into `page.tsx` right after Trade Risk.

**`brain.py`'s Golden Rule violations fixed**:
- 3 opinion/advice answer branches ("take trades only at...", "don't average a losing trade", etc.) rewritten to restate real current field values instead of giving generic advice.
- `options_professor.py`'s imperative templates ("Buy a CE because...", "so don't buy either") — reachable through Voice unfiltered — rewritten to descriptive phrasing ("CE is favored because...") with identical underlying reasoning, zero data change.
- New `_ai_dealer_speech()` composer in `brain.py`, matching your example format (verdict → reason → target/stop for BUY; verdict → reasons → No Trade for WAIT), verified with a direct synthetic test producing output matching your example almost verbatim. Wired to lead `briefing()`'s existing Radio rundown (the older, broader briefing feature itself was left otherwise unchanged).

**2 found-along-the-way bugs fixed** (independent of AI Dealer):
- `risk_approval.py`'s dead Liquidity check — was reading a key (`layers.get("liquidity")`) that never existed anywhere in `confluence.py`'s output, so it silently always evaluated to unknown. Now reads the real Decision Matrix "Liquidity" row.
- `TradeRiskPanel.tsx`'s "Next Invalidation" list wasn't passed through the existing `displayReason()` rename helper, so it could show raw "Kill Switch" instead of "Execution Lock." Fixed — confirmed live in browser showing "Execution Lock" correctly.

## What was explicitly left alone (per your decisions)

- The existing `BuyChecklist`/`buy_checklist` (TradeNowCard/AIThinkingPanel's own 7-item checklist) — untouched, a separate prior owner decision.
- `AIAnalysisCard.tsx` (Gemini-powered WHY/NEXT/WATCH/CHANGE) — left as a separate existing feature alongside the new deterministic AI Dealer.
- "OI Wall" in NEXT LEVEL — dropped rather than reusing/repeating a mislabel.

Owner's locked rule: AI Dealer is a pure NARRATOR, never a new decision
engine — it only reads Hero Decision / Execution Status / WHY HERE /
Evidence / Structure / Risk / S/R and translates them into human language.
Voice never gives a second opinion. Golden Rule: never introduce new
information. Exact target structure: WHY BUY (6-item checklist), WHY NOT
BUY (5-item checklist), NEXT LEVEL (4 items), INVALIDATION (4 items).

## Headline finding: `brain.py` needs full rewiring, not extension

`brain.py` (the existing "AI Market Brain," which both `VoiceAssistant.tsx`
and the `/brain` chat page consume) currently has **no WHY BUY / WHY NOT
BUY / NEXT LEVEL / INVALIDATION structure at all** — it's free-form Q&A.
Worse, it reads the OLD, pre-canonical sources (raw `confluence.py` layer
scores) — it never touches `support_resistance.py`, `structure.py`'s
`bos_choch`, or `risk_approval.py` at all. It needs to be rewired from
scratch to read the canonical engines Steps 3/5/6/7 already built, not
patched incrementally.

## A confirmed Golden Rule violation, already in production

`brain.py` currently gives actual advice/opinions in a few answer branches, not
factual restatements:
- *"Take trades only at grade A/B with confirmed structure."*
- *"Only if structure + institutions align; respect the kill switch."*
- *"Re-enter only on a fresh confirmed setup... Don't average a losing trade."*
- It also re-exposes `options_professor.py`'s own directive templates
  verbatim (e.g. *"Buy a CE because..."*, *"...so don't buy either."*).

`VoiceAssistant.tsx` itself is clean — no opinion language, purely
templated — but it calls `brain.answer()`/`brain.briefing()` directly, so
any opinion-language in brain.py flows straight through Voice's mouth
unfiltered. **Fixing brain.py fixes Voice's Golden Rule compliance too.**

## WHY BUY — all 6 items map to real data, no fabrication needed

| Item | Real source | Wiring needed? |
|---|---|---|
| VWAP | `tech.vwap` vs spot, or evidence's `vwap` proximity | New wiring |
| Gamma Support | `expiry.py`'s `gamma_wall` (direction vs spot) | New wiring |
| Structure BOS | `structure.py`'s `bos_choch` field directly | New wiring — the *existing* `buy_checklist.structure` item uses the aggregate Structure *score*, not BOS specifically; this would read a different, more precise field |
| CPR Above | `support_resistance.py`'s daily CPR pivot vs spot | New wiring |
| Volume Confirmation | Volume Profile layer score, or evidence's volume-spike boolean | New wiring |
| Risk Approved | `risk_approval.approve().status` | **Already wired** — same source as the existing checklist's `risk_gate` item |

## WHY NOT BUY — mixed: 2 exist, 1 partial+buggy, 2 need wiring

| Item | Status |
|---|---|
| Execution Lock | Exists fully, already gates and already renamed for display |
| High Risk | Exists fully, already gates (`capital_protection.category`) |
| Low Liquidity | Partially exists, but **found a real pre-existing bug**: `risk_approval.py`'s dedicated Liquidity check reads `layers.get("liquidity")` — a key that doesn't exist anywhere in `confluence.py`'s output (only `order_flow` and a differently-shaped decision-matrix row named `"Liquidity"`) — so this check has always silently evaluated to unknown/None. Not caused by AI Dealer, but found while auditing it. |
| No BOS | Doesn't exist as a distinct reason yet — real field (`bos_choch is None`) exists, just not surfaced as a reason |
| Weak Volume | Doesn't exist yet — Volume Profile isn't in the mandatory-gate list at all today, so it's never been a "blocking reason." Real score exists. **Important: I am proposing to surface this only as an explanatory item when relevant — never as a new hard gate/veto. Turning it into an actual blocker would be a Trading Doctrine change (same boundary Step 8 drew), which this step must not do.** |

## NEXT LEVEL — 3 clean, 1 genuine conflict with your spec

- **Next Resistance**: clean, `support_resistance.py`'s R1.
- **Next Premium Target**: two real candidates that answer different questions — `decision_contract.premium_plan`'s actual target1/2/3 for the live trade (concrete, decided) vs. `premium_forecast.py`'s scenario projection (speculative, "what premium might reach"). Recommend the live trade's real target1, since a narrator shouldn't surface a speculative forecast number as if it were "the" next level — but flagging so you can override.
- **Gamma Wall**: clean, already exists.
- **OI Wall — a real conflict, not a wiring gap.** No genuine, separate "OI Wall" concept exists in this codebase. The only two candidates are: (a) `expiry.py`'s `gamma_wall` — but this is literally the field a prior step already renamed FROM "OI Wall" TO "Gamma Wall" because it was mislabeled (it measures gamma exposure, not OI buildup) — reusing it here would exactly repeat the bug just fixed; or (b) Max Pain (`index_analytics.py`) — a real, different, legitimate concept (the strike minimizing aggregate option-buyer payout) but not what "OI Wall" conventionally means, so labeling it that would be a *new* mislabel, not a fix. **I need your call on this — see questions below.**

## INVALIDATION — 1 exists, 2 need wiring, 1 has a labeling bug

- **VWAP lost**: exists 1:1 already.
- **CPR lost**: real data exists (CPR pivots are already computed) but isn't currently reachable from `_invalidations()` — needs the CPR value threaded across a module boundary it doesn't currently cross. No new computation.
- **Swing broken**: real signal exists (`structure.py`'s `bos_choch == "CHOCH"`, which is definitionally "the break goes against the prevailing sequence") — needs the raw structure layer threaded into `_invalidations()`, which currently only receives aggregate scores. No new computation.
- **Execution Lock enabled**: exists (mentions Kill Switch, marks "ACTIVE NOW"). **Found a real display bug along the way**: `TradeRiskPanel.tsx` renders the invalidations list without passing it through the existing `displayReason()` rename helper — so it currently shows raw "Kill Switch" text instead of "Execution Lock," inconsistent with the rest of the dashboard. Pre-existing, unrelated to AI Dealer, worth fixing regardless.

## `AIAnalysisCard.tsx` (Gemini) — a weaker guarantee than what you're asking for

This is the closest existing analogue (same "engine decides, AI phrases" doctrine) but it's a genuine LLM call, only content-scanned for buy/sell-directive *phrasing* — not code-enforced against inventing a number or a level in general. The system prompt says "don't invent data," but that's a request to the model, not a guarantee. Your Golden Rule wants a code-enforced guarantee, which points toward the new AI Dealer being a fully **deterministic** template engine (not LLM-based) — but AIAnalysisCard itself isn't asked to change, so I need your call on whether it stays as a separate, existing, already-accepted feature, or whether this step should also fold it in somehow.

## Sign-off needed (4 real decisions)

1. **OI Wall**: drop it from NEXT LEVEL (recommended — no honest distinct data exists), reuse Gamma Wall's value under the "OI Wall" label anyway (repeats a bug already fixed once), or label Max Pain as "OI Wall" (a different kind of mislabel)?
2. **Scope of WHY BUY**: is this a brand-new "AI Dealer" narration panel (separate from the existing `BuyChecklist`/TradeNowCard, which keeps its own 7 items exactly as previously locked), or should it replace the existing BuyChecklist's contents? I'm recommending **new, separate panel** — the existing checklist was a prior, explicit owner decision I shouldn't silently overwrite.
3. **Fix brain.py's Golden Rule violations** (the "take trades only at..."/"don't average a losing trade" advice-style answers, and options_professor.py's directive templates reaching Voice unfiltered) as part of this step?
4. **AIAnalysisCard (Gemini)**: leave untouched as a separate existing feature, or fold/replace with the new deterministic AI Dealer?

Two small, low-risk bugs found along the way (independent of the above, safe to fix regardless): the dead `risk_approval.py` Liquidity check, and `TradeRiskPanel.tsx`'s missing `displayReason()` pass-through.
