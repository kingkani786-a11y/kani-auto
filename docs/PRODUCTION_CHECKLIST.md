# AI OS — Production Checklist

**Rule (owner, 2026-07-11): no new layer until the current ones are each
"Production Ready" here.** Honest status only — PENDING is not a failure, it's
an untested item. Last verified: 2026-07-11 (Sat, market closed).

Legend: ✅ verified · ⏳ pending (needs live market / more data) · ⬜ not built

---

## Phase 1 — AI Foundation

### Decision Engine (pre-existing, unchanged)
- ✅ Runs the trading decision deterministically; LLM never in this path
- ✅ Kill-switch / safe-mode hard vetoes intact
- ✅ Unaffected whether the AI layer is on or off

### Context Builder (`cortex/context_builder.py`)
- ✅ Emits only published state (Rule 10) — verified via /api/cortex/snapshot
- ✅ Raw candles never sent to the LLM
- ⏳ Live-market snapshot shape (trend/liquidity scores populated) — verify Mon

### Safety Layer (`cortex/safety.py`)
- ✅ Flags trade-directive language at the code boundary (unit-tested: 3 caught)
- ✅ Always attaches the engine's authoritative decision
- ⏳ Real-world false-positive/negative rate — observe over a live week

### Cost Controller (`cortex/cost_controller.py`)
- ✅ Per-IST-day ₹ + call caps enforced; ledger resets at IST midnight
- ✅ Live: calls + ₹ accrue correctly (verified across A2–A5, ₹0.26 today)
- ⏳ Full-day spend profile under live-market cadence — measure Mon–Fri

### Memory (existing ledgers/module_stats + persistence)
- ✅ Verdict ledger, module_stats, calibration survive restart (rehydrate)
- ⏳ Conversational recall quality via the cortex — evaluate with real questions

### Gemini Integration (`cortex/provider.py`)
- ✅ Live end-to-end on the owner's key; gemini-flash-latest
- ✅ thinking_budget=0 → complete, non-truncated replies
- ✅ Lazy import; backend runs with AI off

### Multi-provider layer
- ✅ Provider-agnostic interface (`cortex.ask`); auto-detects Gemini/Anthropic
- ⏳ Anthropic path unexercised (no key yet) — verify when a key exists

**Phase 1 gate:** green except items needing live-market data (Mon) or a spend
week. Foundation is production-usable now.

---

## Phase 2 — AI Intelligence

### AI Analysis (`cortex/analysis.py` + AIAnalysisCard)
- ✅ 4 blocks (WHY/NEXT/WATCH/CHANGE) populate; parsed with tolerant fallback
- ✅ Cost-cached by decision-band (poll cheap; 1 call per real change)
- ✅ Shows engine decision + Safety banner; hides when cortex off
- ⏳ Block quality on LIVE trend/liquidity data — verify Mon

### AI Timeline (`ai_timeline.py` + AITimelineCard)
- ✅ Endpoint + card live; records transitions read-only in the AI cycle
- ✅ Honest empty state on a closed market
- ⏳ Real transition events (trend flip/entry/target) — fire on live tape (Mon)

### AI Radio v1.0 (VoiceAssistant transition watcher)
- ✅ Builds/compiles; transition logic deterministic
- ⏳ **Live spoken output — VERIFY MON 09:15** (closed tape has no transitions)

### AI Workspace (`/ai-workspace`)
- ✅ AI Chat (6 roles), EOD Reports, Weekend AI, live budget — all live
- ⏳ Sustained-use UX during market hours

### Weekend AI (`weekend_ai.py`)
- ✅ Broker-independent loop; Review/Research/Plan run + stored (verified ₹0.19)
- ✅ "PAUSED" → "Weekend AI ready" in the AI-Brain status
- ⏳ Full weekend soak (auto-cadence over 48h) — observe this weekend

### AI Planner · Teacher · Reviewer
- 🟡 Teacher/Reviewer exist as cortex roles (Workspace/EOD); Planner (09:00) ⬜ not built

**Phase 2 gate:** cards live and cost-safe; the one hard-PENDING is AI Radio
live speech (Mon). Timeline/Analysis live-data quality also verify Mon.

---

## Phase 3 — AI Automation — ⬜ not started (by design)
Daily/weekly/monthly autonomous review·research·audit·propose, all behind the
Phase-22 human-approval gate. Begin only after Phase 2 is green.

---

## AI Health Center — ⬜ recorded, not built
The live dashboard view of this checklist (per-subsystem %, budget, queues).
Natural next build once Phase 2 items clear their live-market verification.

---

## The single blocking item right now
**AI Radio live spoken output — verify Monday 09:15 at market open.** Everything
else is either ✅ or ⏳-on-live-data. No new layer should start until Radio is
confirmed speaking on a live tape.

---

## Deployment (added after the PWA stale-cache bug, owner)
- ✅ Service Worker: network-first for HTML; cache name = git commit (auto-invalidates every build via `scripts/stamp-version.mjs` prebuild)
- ✅ Build Version visible on the dashboard (frontend/backend commit, AI provider, Radio, SW) → self-verifiable, no trust needed
- Per-deploy checks: □ Frontend rebuilt □ Backend restarted □ SW version changed □ version.json commit matches □ dashboard shows the new commit
