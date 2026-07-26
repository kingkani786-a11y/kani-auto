# Premium Panel Final — Step 4 Plan (V7.0 Roadmap)

Date: 2026-07-26
Status: **IMPLEMENTED — owner signed off same day. Typecheck + full production build + live browser verification (real backend, separate dev port) all pass clean.**

## What shipped

- Removed the duplicate "Premium Forecast" box from `EntryZonePremium.tsx` (it rendered the identical `decision.premium_forecast` object `PremiumTimeline.tsx` already shows). `EntryZonePremium.tsx` now shows Entry Zone + Confidence Explainer only, in a 2-column grid. `PremiumTimeline.tsx` is unchanged and is now the one canonical Premium panel.
- No other Spot/Premium mixing violations found anywhere else in the codebase — the core Step 4 rule was already fully satisfied by Step 3's fix.

Owner's rule for this step: Spot and Premium must NEVER be mixed in one
panel, always separate. As anticipated, Step 3 already enforced this rule
(the one violation — `SupportResistancePanel.tsx` embedding Premium
alongside Spot — was fixed there). This step's audit re-checked the rule
against every other premium-consuming component.

## Findings

| Component | Mixes spot+premium? | Notes |
|---|---|---|
| `PremiumSRStrip.tsx` | No | Premium-only, built Step 2. |
| `PremiumRadar.tsx` | No | Pure premium/strike movement tracking (runner score, phase, ladder) — no spot levels. |
| `ScalpingTool.tsx` | No | Shows `premium_forecast` fields as one contextual line inside a broader strike-execution card — not a level-mixing violation. |
| `EntryZonePremium.tsx` | No | Entry Zone / Premium Forecast / Confidence Explainer are 3 separately-bordered sub-panels side by side — grouped, not merged. |

**No further Spot/Premium mixing violations found — the rule is fully satisfied.**

## One genuine duplicate found (different question — not spot/premium mixing, but duplicate panels)

`PremiumTimeline.tsx` ("Premium Roadmap") and `EntryZonePremium.tsx`'s embedded "Premium Forecast" box both render the identical `decision.premium_forecast` object:

- Same classification + probability header.
- Same per-horizon (15/30/60/90m) premium + change% figures.
- Same expansion/decay/theta/IV-crush footer line, word-for-word.
- Both are Advanced-mode-only and both render simultaneously on the same page.

The only difference: `PremiumTimeline.tsx` additionally shows the strike identity and a "Now" starting point in its timeline; `EntryZonePremium.tsx`'s version is a plainer 4-column grid with no strike label.

**Proposed fix:** keep `PremiumTimeline.tsx` as the canonical Premium panel (it's the more complete version — strike identity + "Now" anchor). Remove the "Premium Forecast" box from `EntryZonePremium.tsx`, leaving Entry Zone + Confidence Explainer as a 2-column grid instead of 3.

## Sign-off needed

Confirm: remove the duplicate "Premium Forecast" box from `EntryZonePremium.tsx`, keep `PremiumTimeline.tsx` as-is?
