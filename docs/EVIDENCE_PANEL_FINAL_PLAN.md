# Evidence Panel Final — Step 6 Plan (V7.0 Roadmap)

Date: 2026-07-26
Status: **IMPLEMENTED — owner signed off same day on all 4 questions (8-row sourcing, 5 bug fixes, trim plan, build now). Backend compile+import clean, frontend typecheck+production build clean, live browser verification (real backend, separate dev port) clean.**

## What shipped

**Part A bug fixes (all 5):**
1. Deleted `frontend/components/FinalDecisionHeader.tsx` (6th dead file Step 1 missed — confirmed unused, only referenced in a stale `page.tsx` comment).
2. Renamed `decision_contract.py`'s ledger pillar from `"Price Action"` to `"Structure/MTF"` (it averages Structure+MTF scores — the label collided with `support_resistance.py`'s real Price Action wick-rejection check).
3. Renamed the `oi_wall` evidence field to `gamma_wall` in `support_resistance.py`'s `attach_evidence()` (was testing Gamma Wall proximity, mislabeled as OI) — updated both frontend consumers (`SRHeroCard.tsx`, `SupportResistancePanel.tsx`).
4. Wired the stale `"structure"` BuyChecklist item (`decision_contract.py`) — was hardcoded `ok: None, "Market Structure Engine not built"` — to read the real Decision Matrix "Structure" row score, now that Structure has been live and audited-clean since Step 5.
5. Dropped the trivially-true `"swing"` field from `attach_evidence()` (was hardcoded `True` for every row, not a real check).

**New Evidence Panel** (`frontend/components/EvidencePanel.tsx`): renders exactly the 8 locked categories, each reused from an existing computed value — zero new scoring:
- Price Action / VWAP / CPR / Gamma Wall ← the Hero S/R level's own evidence chips.
- Swing ← `structure.py`'s real HH/HL/LH/LL sequence.
- OI / Volume ← the Decision Matrix's own "OI"/"Volume Profile" rows (confluence.py's already-shared source).
- Market Structure ← `structure.py`'s event/BOS-CHOCH state.

Never shows a decision, BUY/SELL wording, confidence, or probability — only ✓/○/– per category, with a short reason string for OI/Volume/Swing/Market Structure. Wired into `page.tsx` right after Block Reason Hero (WHY HERE), matching the locked hierarchy.

**Trims:**
- `SRHeroCard.tsx`: removed its per-source evidence checklist and the evidence-ratio stat cell entirely (now the Evidence Panel's job); kept level/distance/strength/stage.
- `DecisionMatrix.tsx`: removed the `dm.decision` (BUY CE/NO TRADE) header text and the `institutional_thoughts` confidence% numbers; kept the per-layer PASS/FAIL/reason grid and the Calibration/behavior-reasoning content.
- Left as-is (reasoned in the plan, confirmed by owner): AI Thinking's radar confirmations (different data/purpose — pre-entry detection, not trade evidence), Structure notes (never rendered anywhere, nothing to remove), Execution panels' OI/Structure condition rows (already just re-display the Decision Matrix rows, not an independent computation, and belong to Execution Status's own hierarchy rung).

Owner's locked rules for this step:
- ONE Evidence Engine, showing only: Price Action, Swing, VWAP, CPR, Gamma Wall, OI, Volume, Market Structure.
- Remove duplicate evidence from S/R Hero chips, Decision Matrix, AI Thinking, Market Structure notes, Execution panels.
- Evidence Panel must NEVER state a decision, say BUY/SELL, or create confidence/probability — only "what evidence exists for this trade."
- Decision is always TradeNowCard (Hero) only.
- Hierarchy: TradeNowCard → Execution Status → WHY HERE → Evidence Panel → Support & Resistance → Market Structure.

## Part A — Bugs found, fix regardless of the consolidation design below

1. **6th dead file Step 1 missed**: `frontend/components/FinalDecisionHeader.tsx` still exists on disk — not imported anywhere (only referenced in a `page.tsx` comment noting it was "removed 2026-07-21," but the file itself was never deleted). Safe to delete now.
2. **"Price Action" naming collision**: `support_resistance.py`'s real Price Action check (wick-rejection at a level) and `decision_contract.py`'s ledger pillar labeled `"Price Action"` (which is actually an average of Structure+MTF scores, nothing to do with candle wicks) are two unrelated computations sharing one label. The mislabeled one feeds TradeNowCard's "Evidence /100." Needs a rename.
3. **"OI Wall" mislabel**: the S/R evidence chip labeled "OI Wall" (`SRHeroCard.tsx`/`SupportResistancePanel.tsx`) is actually testing proximity to the **Gamma Wall** (`expiry.py`), not open-interest buildup. Needs relabeling to "Gamma Wall."
4. **Stale hardcoded "not built" note**: `decision_contract.py`'s BuyChecklist has a `"structure"` item hardcoded to `ok: None` with the note "Market Structure Engine not built — not measured." That was true when written (before 2026-07-24) but is now factually wrong — Structure (HH/HL/LH/LL, BOS/CHOCH) has been live and audited-clean since Step 5. This item should be wired to read the real Decision Matrix "Structure" row.
5. **Trivially-true field**: the S/R evidence chip's `"swing"` field is hardcoded `True` for every level ("these ARE swing-clustered levels, always") — it's not a real check and carries no information as a confirmation signal. Candidate to drop from the evidence chip set.

## Part B — Where "evidence" for the 8 named categories currently lives (condensed)

| Category | Real single source | Duplicates / issues |
|---|---|---|
| Price Action | `support_resistance.py` wick-rejection (per-level) | Colliding label in decision_contract's ledger (see A2) |
| Swing | `structure.py` HH/HL/LH/LL sequence | SR's own "swing" field is trivially true (see A5) — different concept entirely |
| VWAP | `technicals.vwap()`, reused everywhere | Clean, no issue |
| CPR | `support_resistance.py` pivot formula | Clean, no issue |
| Gamma Wall | `expiry.py` | Mislabeled "OI Wall" in SR chips (see A3) |
| OI | `confluence.py`'s `_oi_layer` (PCR/buildup) — already properly shared by Decision Matrix, Execution Gate, Entry Checklist, TradeNowCard's ledger | A 2nd, unrelated "OI" check exists in `premium_radar.py` (per-strike OI% for radar opportunity-detection, not S/R-level evidence) — different question, different data, not a true duplicate |
| Volume | `confluence.py`'s Volume Profile layer (POC/VAH/VAL) — already properly shared by the same 4 consumers as OI | SR's own raw volume-spike check and premium_radar's tick-volume-delta are 2 more independent checks, for different purposes (level-touch vs radar momentum) |
| Market Structure | `structure.py` (the only engine) | Redisplayed separately in Decision Matrix, Execution Control Center, Entry Checklist — same data, 3 different renderings |

**Key judgment call**: OI and Volume each have a "radar" version (`premium_radar.py`, per-strike, powers `AIThinkingPanel`'s pre-entry opportunity reasoning) that is genuinely a different question from "evidence for this trade" (it's about detecting a candidate strike in the first place, a different lifecycle stage). I'm treating those as NOT part of this consolidation — only the S/R-level and confluence-layer versions feed the new Evidence Panel.

## Proposed design: one new Evidence Panel, sourced from existing values only (zero new computation)

| Row | Source (no new logic — reused as-is) |
|---|---|
| Price Action | Hero level's `evidence.price_action` (real wick-rejection check) |
| Swing | `structure.swing` (the real HH/HL/LH/LL sequence — NOT the trivial SR field, which gets dropped per A5) |
| VWAP | Hero level's `evidence.vwap` |
| CPR | Hero level's `evidence.cpr` |
| Gamma Wall | Hero level's `evidence.oi_wall`, relabeled "Gamma Wall" (fixes A3) |
| OI | Decision Matrix's real "OI" row (PCR-based) — reused, not recomputed |
| Volume | Decision Matrix's real "Volume Profile" row — reused, not recomputed |
| Market Structure | `structure.event`/`bos_choch` (breakout/breakdown/BOS/CHOCH state) |

Every row is a read of a value that already exists somewhere in the payload — this is aggregation/derivation only, consistent with how `market_path.py`/`decision_contract.py` are built, so it doesn't require a new "engine" in the Category-3/4 sense the freeze would block.

## What would get trimmed elsewhere (per your explicit call-out of these 5 places)

- **S/R Hero chips**: remove the evidence-chip row from `SRHeroCard.tsx` (now redundant — that's the Evidence Panel's job). `SupportResistancePanel.tsx`'s PER-LEVEL evidence chips (one row per S/R level, explaining why THAT level is rated N stars) are a different, still-useful thing — propose keeping those.
- **Decision Matrix**: keep the per-layer PASS/FAIL/reason grid (it covers more than the 8 categories — Greeks, Smart Money, Trend, MTF, Calibration too), but remove the `dm.decision` (BUY CE/NO TRADE) header text and the `institutional_thoughts` confidence% lines — those are decision/confidence content that don't belong next to an evidence grid.
- **AI Thinking**: propose leaving this mostly as-is — its "RADAR CONFIRMATIONS" are genuinely different data (premium_radar.py's per-strike ticks, a pre-entry detection question), not a duplicate of the new Evidence Panel. Only the shared `BuyChecklist` it already renders would change when Part A's item 4 (Structure) gets fixed.
- **Market Structure notes**: `structure.py`'s natural-language `notes` list currently isn't rendered anywhere at all — nothing to remove.
- **Execution panels**: `ExecutionControlCenter`'s OI/Structure condition rows already just re-display the same Decision Matrix rows (not an independent computation) — propose leaving as-is, since that's Execution Status's own rung in your hierarchy, not a computation duplicate.

## Sign-off needed

1. Confirm the 8-row sourcing table above.
2. Confirm the 5 Part-A bug fixes.
3. Confirm the trim list (remove SRHeroCard's evidence row + DecisionMatrix's decision/confidence lines; leave AI Thinking, Structure notes, and Execution panels as reasoned above).
4. Confirm building a new `EvidencePanel.tsx` + backend aggregation, placed in the hierarchy right after WHY HERE (Block Reason Hero) and before Support & Resistance.
