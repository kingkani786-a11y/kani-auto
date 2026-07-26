# Hero Dashboard Finalization — Step 2 Plan (V7.0 Roadmap)

Date: 2026-07-26
Status: **IMPLEMENTED — owner signed off same day. Typecheck + full production build + live browser verification (against the real backend on a separate dev port, zero disruption to the running production app) all pass clean.**

## What shipped

- New `PremiumSRStrip.tsx` — nearest ATM CE/PE premium level only (reuses the existing `supportResistancePremium()` data, no new backend engine); full multi-level breakdown stays in Advanced `SupportResistancePanel`.
- New `ExecutionStatusStrip.tsx` — Final Decision + Gate PASS/BLOCKED only, reads the same `execution_gate` the Hero's own contract is built from; full conditions grid stays in Advanced `ExecutionControlCenter`.
- Reordered `page.tsx`: Active Market (Top Bar) + Spot Price + Market Status banner + the two new strips + Safe Mode + Execution Lock + Block Reason Hero (WHY HERE) all moved from ~27-30 panels down to sit directly after the Hero Card and Spot S/R Hero, which were already correctly first. Nothing else was removed or reordered relative to itself — the rest of the dashboard just moves below this zone, unchanged.
- Fixed `LiveCandleCommand`'s stale "first thing on screen" comment (it wasn't — 14 panels down) to correctly describe it as Execution-detail supporting content, not a second verdict, per Rule 11.
- Verified live in a browser against the real running backend (read-only, separate dev port, production app on 3000/8000 untouched): correct order, "AI Conviction" label renders correctly, zero console errors.
Governed by: Rule 11 "One Hero → One Decision" (docs/DECISION_DOCTRINE.md).

Roadmap's own scope for this step: top-of-page ONLY shows Active Market,
Spot Price, Spot S/R, Premium S/R, Hero Card, Execution Status, WHY HERE.
Everything else stays where it is, just moves below this zone.

## Current reality vs the 7-item spec

| Spec item | What exists today | Where it actually renders |
|---|---|---|
| Hero Card | `TradeNowCard` — verdict, confidence, grade, strike, R:R | Line 173 — already first. ✅ |
| Spot S/R | `SRHeroCard` — nearest level, already self-documented as Evidence not verdict | Line 181 — right after Hero. ✅ |
| Active Market | `MarketStatusBanner` + the symbol/LIVE indicator in the "Top Bar" block | Line 331-373 — **~27 panels down**, not top-of-page. |
| Spot Price | LTP ticker, inside the same "Top Bar" block | Same as above — 27 panels down. |
| WHY HERE | `BlockReasonHero` — single highest-priority reason banner | Line 398 — also ~27+ panels down. |
| Execution Status | `ExecutionControlCenter` — full gate/conditions grid | **Advanced-mode only** — no Simple-mode presence at all. |
| Premium S/R | Only exists inside `SupportResistancePanel` | **Advanced-mode only** — no Simple-mode presence at all. |

**Root issue:** the Hero Card and Spot S/R Hero are already correctly first (good — no work needed there, and their own code comments already respect Rule 11). But Active Market, Spot Price, and WHY HERE are pushed ~27 panels down by the "V20 ACTION-FIRST ORDER" reorg from 2026-07-02, and Execution Status + Premium S/R never got a Simple-mode presence at all. `LiveCandleCommand`'s own comment ("THE decision card — first thing on screen") is stale — it renders 14 panels down, not first.

## Proposed target top-of-page order (Simple mode)

1. Active Market (Market Status banner + symbol/session state) — **moved up** from line 331/371.
2. Spot Price (LTP + change% + LIVE/DELAYED) — **moved up**, same Top Bar block.
3. Hero Card (`TradeNowCard`) — unchanged, already correct.
4. Spot S/R (`SRHeroCard`) — unchanged, already correct.
5. Premium S/R — **new minimal strip needed** (see open question below — nothing Simple-mode-visible exists to promote).
6. Execution Status — **condensed version needed** (see open question below — the existing `ExecutionControlCenter` is a full Advanced-only grid, too heavy for a top summary slot).
7. WHY HERE (`BlockReasonHero`) — **moved up** from line 398.

Everything currently between the old top and line ~373 (Smart Alerts, Early Warning, Hot Now, AI Attention, Premium Radar, Capture Score, AI Thinking, Decision Contract, Risk Approval, AI Analysis, AI Timeline, Live Candle, Opportunity Board, Index Radar, Scalping Tool, Point Capture, Gamma Shield, System Verify, AI Health, Measurement Health, Calibration Watch, S/R Heat Map, Feed Diagnostics, Missed Winners, Move Observer, Voice Assistant) **stays exactly as-is, just moves below the new 7-item zone** — none of it is being removed or judged in this step, that's what Steps 3-8 are for.

`LiveCandleCommand`'s stale "first thing on screen" comment gets corrected to describe its actual role and position (per your decision: kept as Execution-Status-adjacent supporting detail, TRUST%/AI Master Score relabeled as clearly-supporting, not a second verdict).

## Two open questions before I touch code

1. **Premium S/R has no Simple-mode component to promote — it needs new UI.** Should I build a minimal always-visible strip now (just the nearest premium level + distance, mirroring how `SRHeroCard` does it for spot), or leave a placeholder/link to the Advanced panel for now and do the real build in Step 4 (Premium Panel Final), which explicitly owns "Spot and Premium must never be mixed"?
2. **Execution Status has no lightweight version — only the full Advanced grid.** Should I extract just the Gate PASS/BLOCKED chip + Final Decision (2-3 fields) into a new slim top-of-page strip, leaving the full conditions grid in Advanced `ExecutionControlCenter` untouched?
