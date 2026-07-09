# TRADING FAILURE INVESTIGATIONS

*Owner-ordered forensic audits of "the dashboard should have told me" events.
Evidence first; no gate/parameter change happens here — findings feed
PROPOSALS.md through the normal pipeline.*

---

## INCIDENT #001 — 2026-07-09 — Expiry-day breakdown, no ENTRY signal

| Field | Value |
|---|---|
| Time | ~14:45–15:27 IST (expiry day) |
| Market | SENSEX broke ~250+ pts down through the 77000 gamma wall |
| Premium | 77000 PE ₹75.95 (14:58) → ₹257.70 (15:27) — **+240%** |
| Dashboard | WAIT throughout (14:28 and 14:58 dumps on record) |
| Expected (owner) | ENTRY |
| Actual | NO SIGNAL — day logged 45–47 missed winners, +1120–1160 pts, top blocker "Premium: AVOID" |

### Signal chain trace (from the 14:28 / 14:58 live dumps + verdict ledger)

| Layer | Verdict | Evidence |
|---|---|---|
| Scanner / Index selector | **PASS** | SENSEX active + tracked all day |
| Opportunity / Strike Watch | **PASS** | 77000 PE ranked #1 — AI 97 at 14:28, AI 90 at 14:58, ENTRY QUEUE "NEXT: 77000 PE" — the right strike, BEFORE the move |
| Direction engine | **PASS** | BEARISH bias (bear 52 vs bull 23), futures Short Buildup 98% at 14:28 |
| Strike Selector | **PASS** (selection) | Correct strike; its premium plan numbers were the since-fixed RC1.16.1 Taylor bug |
| **Execution Gate** | **BLOCKED — the failure point** | see decomposition below |
| Decision | WAIT (consequence of gate) | — |
| Notification | NOT REACHED | nothing to notify — the layer went untested by this incident |

Not a scanner failure, not latency, not "logic didn't run" — every layer ran
and saw the setup. **Policy blocked it.** The gate's block decomposes into
three distinct causes:

**1. Premium: AVOID — the persistent final blocker.** The premium forecast
(theta-decay model) predicted 77000 PE would DECAY −13% to ₹63 in the hour
it actually rose +240%. It is a pinning-regime model that was applied during
a breakout. Ledger context (572 settled): Premium gate blocked 420, **saved
81% / missed 19%** — overall it earns its keep 4:1; it was wrong on this
specific regime, not wrong in general. → regime-conditionality research, not
removal.

**2. Mandatory Structure/OI layers lagged.** Both sat at neutral 50 (< 55
bar) at 14:28 and 14:58 — Structure only printed BREAKDOWN 87 PASS in the
15:34 dump, AFTER the move. Confirmation arrived when the move was over.

**3. Deliberate expiry-day hostility (working as designed).** Gamma Shield
HIGH ("price hugging wall 77000 — moves can trap"), No-Trade-Zone ACTIVE at
14:28, hostile-regime bar +12. The breakdown THROUGH the wall is exactly the
pattern the shield treats as trap-risk; this time it was real. Whether wall
breaks with volume should override pinning logic is a Trading-Doctrine
question — Proposal #001's exact shape.

### Ledger findings surfaced by this investigation (572 settled verdicts)

- **Greeks gate is measurably the worst performer**: blocked 283, saved 44% /
  missed 56%; when Greeks was the SOLO blocker: **87 of 106 = 83% missed
  winners**. This is precisely the evidence Proposal #001 (Greeks Gate
  Softening) was waiting for — though its regime-spread + event-day approval
  conditions still apply.
- Premium: AVOID 81% saved (good gate, breakout blind spot).
- Structure 77% saved. Safe Mode 57/43 borderline (n=42).

### Verdict

The system did NOT fail to see the trade — it saw strike, direction and
timing before the move and refused on capital-protection policy. Two of the
three refusal causes now have measured evidence justifying refinement
proposals; one (expiry gamma hostility) is deliberate doctrine pending the
same evidence pipeline. All changes go through PROPOSALS.md + owner approval
(Rule 9: repetition across regimes required — this is ONE incident).

### Follow-ups filed
- Proposal #001 (Greeks): ledger evidence updated — 83% solo-missed.
- Research Question #007 (new): Premium-AVOID regime-conditionality — should
  a confirmed wall-break with volume flip the premium forecast from decay
  model to expansion model?
- Notification layer remains untested — needs one real fired ENTRY (or a
  drill) to validate end-to-end.
