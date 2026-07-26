# Dashboard Cleanup Audit — Step 1 of V7.0 Roadmap

Date: 2026-07-26
Status: **IMPLEMENTED — owner signed off on all 6 items same day; backend import check + full frontend production build both pass clean.**

## What actually shipped (owner decisions)

1. **5 dead files deleted**: EntryPanel.tsx, SelfCheck.tsx, FinalActionBar.tsx, FinalSignalBanner.tsx, RiskBadge.tsx.
2. **Conviction label standardized** to "AI Conviction" in AIHealthStrip, ExecutionControlCenter, DecisionIntelligence (same `intelligence_synthesis.conviction` field, was 3 different labels).
3. **MissedMoveProtection merged** into ExecutionControlCenter's blocking-reasons display — but its live move-episode-facts section was kept **Simple-mode visible** as a new standalone `MoveObserverStrip.tsx`, since the original panel's "Incident #001 rule" (a building move must be visible even during WAIT) would otherwise have been silently demoted to Advanced-mode-only. `MissedMoveProtection.tsx` deleted.
4. **TradeManagement merged** into ExitIntelligencePanel — live P/L, trailing stop, re-entry status/safety-rule messaging, cycle forecast, and the trade-cycle stage timeline were all folded in as additional sections. `TradeManagement.tsx` deleted. Both components already shared `store.exitIntel`, so no visibility-tier issue here (both were Simple-mode visible).
5. **EntryFirstDeck's 4-metric confidence row** — left as-is, deferred to Step 9 (Explainability Final) per owner decision.
6. **ScalpRadarPanel removed entirely** — frontend component, the now-empty "DEEP ANALYSIS" page section and its dead `showBottom` flag, backend `scalp_radar.py` engine, `scalp_state.py` service, the `/api/scalp` route, `state.scalp` field, the `scalp`/`scalp_mgmt` websocket broadcasts, and all wiring through `market_service.py`, `brain.py`, and the frontend store (`store.tsx`) were removed. Verified zero residual references via full-repo grep.
Scope: every component rendered by `frontend/app/page.tsx` (59 panels) + confirmed-dead files.

Rule this document exists to satisfy (locked by owner): audit every panel for duplicate
panels/metrics/confidence/signals, unneeded cards, empty widgets — produce a
Keep/Merge/Remove/Rename list per panel and get sign-off BEFORE touching any code.

---

## 1. REMOVE — dead code (zero risk, nothing imports these)

| File | Why remove |
|---|---|
| `components/EntryPanel.tsx` | Not imported anywhere in the app. |
| `components/SelfCheck.tsx` | Not imported. Superseded by `SystemVerify.tsx` — page.tsx's own comment already says "System Verify replaced the old duplicate AI SELF-CHECK panel; owner: one health source only," but the old file was never deleted. |
| `components/FinalActionBar.tsx` | Not imported. Same shape of card as the already-removed `FinalDecisionHeader` (removed 2026-07-21 as "duplicate of TradeNowCard"). |
| `components/FinalSignalBanner.tsx` | Not imported. Same field set as `FinalDecisionHeader` was (action, entry/stop/T1-3, confidence, risk badge) — looks like a sibling that escaped the same cleanup pass. |
| `components/RiskBadge.tsx` | Only consumer is the dead `FinalSignalBanner.tsx` above — transitively dead. |

**Recommendation: delete all 5.** No dashboard behavior changes; nothing references them.

---

## 2. MERGE candidates — same backend data, overlapping purpose

| Panels | Overlap | Recommendation |
|---|---|---|
| **MissedMoveProtection** vs **ExecutionControlCenter** | Both read `execution_gate.blocking_reasons` / `.blocker_research`. MissedMoveProtection adds an "observed move facts" layer on top; ExecutionControlCenter shows the same blocker list plus the full gate/mandatory-conditions grid. | Owner call needed — see Q1 below. |
| **TradeManagement** vs **ExitIntelligencePanel** | Both read `store.exitIntel` directly. TradeManagement adds a re-entry engine + cycle forecast + one recommended action on top of the same exit score/confidence data ExitIntelligencePanel already shows in full. | Owner call needed — see Q2 below. |

---

## 3. RENAME — same field, three different labels (this is likely the exact "Trust 65% vs Conviction 29% vs Confidence 33.9%" confusion reported earlier)

| Label shown | Component | Field |
|---|---|---|
| "AI Conf" | AIHealthStrip | `intelligence_synthesis.conviction` |
| "Confidence" | ExecutionControlCenter | `intelligence_synthesis.conviction` |
| "Conviction" | DecisionIntelligence | `intelligence_synthesis.conviction` |

**It's the same number, wearing three names.** Recommendation: pick one label (suggest **"AI Conviction"**, since that's the backend's own field name) and use it everywhere this field appears. This is a pure rename, zero logic risk — flagging it now, but happy to bundle it into Step 9 (Explainability Final) instead of doing it in this pass, since that step already touches conviction/confidence wiring end to end.

---

## 4. Needs owner judgment (not a simple keep/remove)

**EntryFirstDeck's 4-way confidence row** — shows, side by side, in one card: "Confidence" (`signal.dynamic_confidence`), "Signal Score" (`signal.confidence` — a *different* field despite the near-identical name), "Execution" (`strike.selection_score`), "Entry Probability" (`layers.entry_probability.score`). Four differently-sourced percentages presented as one visual group is the most likely single source of "which number do I trust" confusion on the whole dashboard. See Q3.

**ScalpRadarPanel** — an explicitly "independent" scalp engine (own scoring, own win-rate, parallel to the main decision pipeline). It was never part of the locked V7.0 roadmap. See Q4.

**AIHealthStrip** — a one-line strip that repeats pieces already shown in full elsewhere: overall health (also in SystemVerify), calibration (also in CalibrationWatchCard), feed status (also in FeedDiagnostics), on top of the conviction-rename issue above. Not asking a formal question on this one — **default recommendation: keep as an at-a-glance summary strip, no removal**, since a single-line overview genuinely serves a different job than the detail panels. Flag if you disagree.

**BuildVersion / AIChangelog / AITimelineCard** — dev/ops info (git commit, changelog, engine event log) sitting among trading panels. **Default recommendation: keep them, but relocate to a separate "System" section/tab in a later pass** — not a Step-1 removal, just noted so it doesn't get lost.

---

## 5. KEEP — everything else (~45 panels)

Every remaining panel reads a distinct backend field and serves a distinct purpose (pre-entry radar vs post-signal decision vs directional bias vs capital-risk gates vs exit management vs system health detail), or is a correctly-quiet panel that only renders when it has real data (confirmed via early-return audit — no accidental empty widgets found; every `return null` traced to a real "nothing to show yet" or "feature not ready" condition, not a bug). Full per-panel inventory with data sources is available on request if you want to review the complete list rather than just the flagged items above.

---

## Sign-off needed on 4 points before any code changes

1. MissedMoveProtection ↔ ExecutionControlCenter — merge, or keep both?
2. TradeManagement ↔ ExitIntelligencePanel — merge, or keep both?
3. EntryFirstDeck's 4-metric confidence row — simplify now, or defer to Step 9 (Explainability Final)?
4. ScalpRadarPanel — keep, remove, or park for later?

Everything in §1 (dead file removal) and §3 (rename) can proceed once you say go — low risk, easy to bundle together.
