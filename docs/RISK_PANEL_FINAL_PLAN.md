# Risk Panel Final — Step 7 Plan (V7.0 Roadmap)

Date: 2026-07-26
Status: **IMPLEMENTED — owner signed off on all 4 questions. Backend compile+import clean, direct behavioral tests of the two fixed engines pass, frontend typecheck+production build clean.** (Live browser check was done against a disconnected backend — the native process had independently restarted and needed broker re-login — so verification for this step leaned on direct backend behavioral tests instead, which is at least as rigorous for confirming the actual numbers are correct.)

## What shipped

1. **Fixed the `execution_card.py` crash.** Root cause: `hold = micro["eta_min"]` where `micro` was never defined — a `NameError` on every real BUY signal, silently swallowed, so this card never rendered its risk fields on a live trade. Fixed by computing the hold-time from the same declared time-band table (`_LADDER`/`_TIER_HOLD_MINUTES`) this file already uses elsewhere — never a new computed ETA. Verified with a synthetic real-trade test: previously would have crashed, now returns a correct card with `hold_minutes`.

2. **Fixed the position-sizing divergence.** `decision.py` had its own index-point-based sizing (`recommended_lots`/`max_safe_lots`) feeding `RiskApproval.tsx` — economically wrong for an option buyer (used the underlying's point move as the risk basis, not the premium). Removed it entirely (along with the now-dead `_lot_band` helper and the now-unused `lot_size` parameter). `risk_approval.py` now reads `decision["position_sizing"]` — the same premium-based calculation `market_service.py` already correctly computes and `ScalpingTool.tsx` already correctly shows — applying the same confidence-scaling band decision.py used to. `routes.py`'s `/portfolio/risk` endpoint had the same bug (calling the shared `portfolio_risk.position_size()` function with index-point inputs instead of premium) — now reuses `decision["position_sizing"]` too, and its `capital_allocation_pct` calc was fixed to use `capital_required` (already premium-consistent) instead of mixing a premium-based qty with an index-level price. Verified behaviorally: HIGH conviction → recommended = max lots; MODERATE → half; no active setup → honest nulls, no crash.

3. **Defined Max Loss.** `risk_approval.py`'s `position_size` response now includes `max_loss` (= `capital_required`, the full premium paid — the honest worst case), shown alongside the pre-existing `risk_amount` (loss if SL is hit) — the two were previously unreconciled and unlabeled. `RiskApproval.tsx` now shows both, clearly labeled "Risk (to SL)" and "Max Loss (premium)".

4. **New `TradeRiskPanel.tsx`** (named to avoid the pre-existing, unrelated `RiskPanel` in `SignalPanels.tsx`) shows exactly: Stop Loss in both units side by side (index points AND option premium ₹, so they're never mistaken for the same number), R:R labeled "(to Target 2)" (since that's what the number actually measures, distinct from the T1-based gate), Rec/Max Lots, Risk (to SL), Max Loss (premium), and Next Invalidation (from `decisionContract().invalidations` — the correct pre-entry/armed-trade concept, distinct from AI Thinking's radar-momentum invalidation). Never shows a decision or BUY/SELL wording. Wired into `page.tsx` right after the Evidence Panel.

5. **Rule 11 trim**: `ScalpingTool.tsx`'s "Commander Brief" no longer prints the word "BUY" (always "PLAN" now) — that was a second decision-labelled surface sitting next to risk numbers on the main dashboard. `SignalPanels.tsx`/`EntryFirstDeck.tsx` (same issue, `/advanced` legacy page) deferred to a later pass per owner decision.

Roadmap scope: Stop Loss, Risk (amount), Risk:Reward, Position Size, Max
Loss, Next Invalidation (pre-entry).

**This audit found something more serious than prior steps: actual
position-sizing numbers can disagree between panels for the same trade, and
one confirmed crash bug silently kills a whole card on every live trade.**
This is closer to a correctness issue than a UI-duplication issue, so I'm
laying out findings and asking for explicit direction before touching
anything.

## Confirmed bug (unrelated to consolidation, found along the way)

`backend/app/engines/execution_card.py:171` reads `micro["eta_min"]` where
`micro` is **never defined anywhere in the file**. This line only runs
inside the real-trade branch (`gated in ("BUY CALL","BUY PUT")`). The call
site wraps the whole function in a bare `except Exception: log.exception(...)`
(`market_service.py:795-800`), so **every time a real trade fires, this
raises `NameError` and `decision["execution_card"]` is never set that
cycle** — `ExecutionCard.tsx` then renders nothing (`if (!x?.ready) return
null`). This card has structurally never shown its SL/RR/probability/hold
fields on an actual live trade. Needs root-causing (what was `micro`
supposed to be?) and a real fix, not a silenced exception.

## Field-by-field findings

**1. Stop Loss** — ONE real computation (`confluence.py`, live) → ONE
derivation to premium SL (`strike_selector.py`, delta-based). No numeric
disagreement possible. But 6+ panels show "Stop Loss" mixing **index
points** and **option premium ₹** with no unit label in several places
(`SignalPanels.tsx`, `ScalpingTool.tsx`'s Entry Details) — a trader could
see two very different "SL" numbers on screen that are both correct, just
different units.

**2. Risk (amount)** — `capital × risk_pct / 100` is independently
reimplemented in 4 places (all read the same settings, so they agree
numerically). But `risk_approval.py`'s "Risk ₹" figure is a **flat
capital-percentage number that never looks at entry/stop at all**, despite
its own comment claiming it "reuses the engine's own sizing." Meanwhile
`ScalpingTool.tsx`'s "Risk ₹" is the actual lot-rounded, premium-SL-based
figure. **These are genuinely different numbers and can disagree.**

**3. Risk:Reward** — the number every panel displays (`reward_risk`) is
measured to **Target 2**, but the actual gate that decides whether a trade
is even allowed through (`confluence.py`'s 1:2 veto) is measured to
**Target 1**. Not a disagreement in data, but the displayed "R:R" is not the
ratio that decided tradability — nothing discloses which target it means.

**4. Position Size — the most serious finding.** THREE different
computations exist for the same trade:
   - `decision.py`'s sizing (feeds `RiskApproval.tsx`'s "Rec/Max lots") uses
     **index-point risk × lot_size** — economically wrong for an option
     buyer (a long option's actual risk is the premium paid, not the
     underlying's point move).
   - `market_service.py`'s sizing (feeds `ScalpingTool.tsx`'s "Qty") uses
     the real **premium-based** risk via `portfolio_risk.position_size()`.
   - `routes.py`'s `/portfolio/risk` endpoint calls the *same*
     `portfolio_risk.position_size()` function but feeds it **index-point**
     entry/stop instead of premium — a third number from shared code fed
     wrong inputs.
   
   **`RiskApproval.tsx` and `ScalpingTool.tsx` can show different
   recommended lot counts for the same trade, simultaneously, on the same
   dashboard.**

**5. Max Loss** — doesn't exist as a named field anywhere. Two unreconciled
candidates already sit in the data: `risk_amount` (loss if SL is hit) and
`capital_required` (full premium paid — the true worst case if the option
decays to zero). These differ by a large margin and neither is currently
labelled "Max Loss."

**6. Next Invalidation** — three genuinely different, correctly-computed
concepts (stop-based for an armed trade, S/R-structure-based for a forming
setup with no signal yet, and premium/OI-momentum-based for the radar's
thesis on a watched strike) all render under the plain word "Invalidation"
in different panels, with no label distinguishing which one a viewer is
looking at.

## Rule 11 concerns found in risk-adjacent panels

- **`ScalpingTool.tsx`'s "Commander Brief" line prints the word "BUY"**
  alongside strike/premium/SL/targets/lots — a second decision-labelled
  surface, always visible in both Simple and Advanced mode (not gated).
- `SignalPanels.tsx` (Advanced-only `/advanced` page) shows a large BUY/SELL
  badge next to Entry/SL/Targets/R:R.
- `EntryFirstDeck.tsx` color-codes BUY CALL/PUT next to Stop Loss/R:R.
- None of these compute a new decision (they all read the same
  `execution_gate`/`decision.action` TradeNowCard reads) — so they don't
  contradict the Hero, they just restate it in BUY/SELL language next to
  risk numbers, which is the exact pattern Rule 11 exists to prevent.

## One naming collision to avoid

A component literally named `RiskPanel` already exists (`SignalPanels.tsx`,
`/advanced` page) — it shows *qualitative market risk* (risk_level/ADX/
ATR%/warnings), completely unrelated to this step's Stop Loss/Risk/R:R/
Position Size/Max Loss/Invalidation scope. The new component needs a
different name.

## Sign-off needed

1. **Fix the execution_card.py crash?** (root-cause `micro`, stop the
   silent NameError on every live trade)
2. **Fix the position-sizing divergence** — standardize `decision.py`'s
   `max_safe_lots`/`recommended_lots` (feeding RiskApproval) and
   `routes.py`'s `/portfolio/risk` endpoint to use the same premium-based
   calculation `market_service.py` already uses correctly, and fix
   `risk_approval.py`'s flat "Risk ₹" to read the real position-based
   figure instead of a capital-percentage placeholder?
3. **Define Max Loss** as `capital_required` (full premium paid — the
   honest worst case) shown alongside Risk (`risk_amount` — loss to stop),
   both clearly labeled so they're never confused?
4. **Scope of Rule 11 trims**: fix ScalpingTool's "BUY" Commander Brief
   wording now (main dashboard, always visible)? Defer SignalPanels.tsx/
   EntryFirstDeck.tsx (both on the separate `/advanced` legacy page, lower
   traffic) to a later pass, or fix those too now?
5. **New component name** — proposing `TradeRiskPanel.tsx` to avoid the
   existing `RiskPanel` collision. OK?
