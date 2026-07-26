# Support & Resistance Finalization — Step 3 Plan (V7.0 Roadmap)

Date: 2026-07-26
Status: **IMPLEMENTED — owner signed off same day. Backend compile+import check, a synthetic-data behavioral test of the fixed exit_intelligence.analyze(), full frontend typecheck+production build, and live browser verification (against the real backend on a separate dev port) all pass clean.**

## What shipped

- **Principle 7 clarified, no code needed**: owner confirmed "Hero Card" in this S/R-focused principle means `SRHeroCard`, which already satisfies it perfectly (zero client-side computation, pure re-display of `support_resistance.hero_card()`).
- **Principles 1, 4, 5, 6 fixed in `backend/app/engines/exit_intelligence.py`**: it now calls `support_resistance.spot_levels(candles, cmp=spot)` — the real, single-source S/R engine — instead of reading `structure.py`'s separate single-swing-pivot value. `_booking_zone()` picks its zone boundary from a real engine-ranked level; Gamma Wall and liquidity clusters are confirmation reasons only, never candidates. `support_strength`/`resistance_strength`/`break_probability`/`reject_probability` are now the engine's real `strength_score`/`break_pct`/`bounce_pct` for the relevant level — no more arbitrary `50 + count×12` formulas or momentum-derived "probabilities" wearing observed-history names. Verified behaviorally with synthetic oscillating candle data (a real 100%-bounce resistance level correctly produced strength 100, break_probability 0%, reject_probability 100% — no fabrication) and with no/insufficient candle data (graceful null degradation, no crash, no invented numbers).
- **Principle 2 fixed in `frontend/components/SupportResistancePanel.tsx`**: removed the embedded `PremiumSR` sub-component entirely (it showed CE/PE premium levels inside the same panel as spot levels, contradicting the "never mixed in one panel" rule and its own sibling `PremiumSRStrip.tsx`'s stated design). Panel retitled from "(spot + premium)" to "(spot)". Premium display now lives exclusively in `PremiumSRStrip.tsx` (built in Step 2).
- Small frontend polish: `ExitIntelligencePanel.tsx`'s Break Prob/Reject Prob now show a clean "—" instead of "—%" when no S/R level exists yet (a new legitimate null case introduced by the Principle 5/6 fix, since these are no longer always-computed formulas).


Owner's 7 locked principles for this step, audited against actual code
(backend/app/engines/support_resistance.py is the S/R engine).

## Findings

| # | Principle | Status |
|---|---|---|
| 1 | Spot S/R = single source of truth | **VIOLATED** |
| 2 | Premium S/R never mixed with Spot in one panel | **VIOLATED** (panel level only) |
| 3 | CPR + Daily/Weekly/Monthly Pivots in one place with spot levels | ✅ HOLDS, no action |
| 4 | Gamma Wall/Volume Profile/OI Wall = evidence only, never create a level | **VIOLATED** |
| 5 | Touch/Hold/Break/Reject = observed history only | **VIOLATED** |
| 6 | Strength Rating derived from observed data, never fabricated | **VIOLATED** |
| 7 | Hero Card only references the S/R engine, no separate S/R logic | **Needs your clarification — see below** |

**The pattern:** `support_resistance.py` itself already does everything right (real touch/bounce/break counting, a declared strength formula from those counts, CPR from real pivot math, evidence tags that never create levels). The violations are all in ONE other file, `backend/app/engines/exit_intelligence.py`, which built its own parallel, lighter-weight S/R concept instead of reusing the engine:

- **Principle 1**: `exit_intelligence.py` reads `structure.py`'s `support`/`resistance` (a single last-swing-pivot value, no clustering, no history) instead of `support_resistance.py`'s clustered/touch-scored levels. Two different S/R numbers can be on screen at once — `ExitIntelligencePanel.tsx`'s "Support/Resist" fields disagree with the S/R panels' own numbers.
- **Principle 4**: its `_booking_zone()` uses the Gamma Wall value as a raw candidate for the zone boundary itself — the gamma wall can literally *become* the level, not just confirm one.
- **Principle 5**: its `break_probability`/`reject_probability` are computed from a momentum-strength formula, not from counting actual past touches — they wear the same names as real observed-history stats but aren't.
- **Principle 6**: its `support_strength`/`resistance_strength` (and the booking-zone `strength`) are `50 + count×12`-style arbitrary formulas, not derived from touches/bounces at all.

`structure.py`'s Fibonacci/trendline/liquidity-zone-clustering (stop-hunt detection) are a genuinely separate concept from S/R and are NOT part of this violation — those stay as-is.

## Principle 7 — needs your call before I can act on it

Your Rule 11 (locked in Step 2) already defines "Hero Card" = `TradeNowCard` (the BUY/WAIT verdict card), and separately defines `SRHeroCard` ("S/R Hero") as Evidence, not the Hero. Under that definition, `TradeNowCard` currently has **zero S/R content at all** — it doesn't violate "no separate S/R logic" (it has none), but it also doesn't "reference the S/R engine" in any way. `SRHeroCard.tsx` is the component that actually, cleanly, only re-displays `support_resistance.py`'s own `hero()` output with zero client-side computation — it already satisfies this principle perfectly, but it isn't "Hero Card" under your Rule 11 naming.

So: when you wrote "Hero Card இந்த S/R engine-ஐ மட்டும் reference பண்ணும்" for this S/R-focused step, did you mean:

- **(a) `SRHeroCard`** (the S/R-specific hero surface) — in which case this principle is already satisfied, no work needed, or
- **(b) `TradeNowCard`** (Rule 11's Hero Card) — in which case it should start surfacing S/R-hero data (e.g. nearest level + distance) as part of its own display, which is new wiring, not a fix.

## Proposed fixes for Principles 1, 2, 4, 5, 6 (pending your go-ahead)

1. **`exit_intelligence.py`**: replace its reads of `structure.py`'s `support`/`resistance` with reads of `support_resistance.py`'s own levels (nearest S/R above/below current price from the real engine) — this is a genuine logic change to a live-trade exit-management engine, so I want explicit sign-off before touching it, not just a doc note.
2. Rebuild `_booking_zone()` to pick its zone from an S/R-engine level, using Gamma Wall only as a confirmation reason (as it already does elsewhere in the same function) — never as the candidate itself.
3. Replace `break_probability`/`reject_probability` with the real `break_pct`/`bounce_pct` from the S/R engine for the relevant level (or remove them if no matching level exists, rather than inventing a number).
4. Replace `support_strength`/`resistance_strength` with the S/R engine's own `strength_score`/`strength_stars` for the corresponding level.
5. **`SupportResistancePanel.tsx`**: remove the embedded Premium S/R block (the nested `PremiumSR` sub-component) — Premium display moves exclusively to `PremiumSRStrip.tsx` (already built in Step 2). The Advanced panel keeps spot levels + CPR/Pivots only, retitled to drop "(spot + premium)".

This is exit-management code touching live in-trade decisions — I'd like your explicit go-ahead on item 1-4 specifically before I implement, given how directly it touches capital-protection-adjacent output.
