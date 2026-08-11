# Cloud AI Trader — Runbook

V7 Finalization item 13 (owner, 2026-08-11). The point of this file: you
should not have to be a developer to run your own trading day. This is the
whole procedure, front to back — nothing here requires opening a code editor.

Everything below already exists in the running system. This file only
collects the steps in one place.

---

## Market open

1. **Connect broker.** Settings → paste today's access token → SAVE & CONNECT.
   The token expires daily; this is expected, not a fault.
2. **Run the audit:**
   ```bash
   bash infra/final-audit.sh
   ```
   Confirm `🟢 FINAL AUDIT: PASS`. WARNs are fine (they're expected
   conditions — broker not yet connected, market not yet open). A FAIL means
   stop and read [Incident](#incident) below before trading.
3. **Wait for the opening range** (09:15–09:30). The Entry Evidence Board and
   several other panels need it; they say so plainly until it forms.
4. **Check Decision Integrity** (top of dashboard) at a glance:
   - `IS THE SOFTWARE WORKING?` should read 🟢 or 🟡 (degraded feed is not a
     fault). 🔴 means read the rows below it before doing anything else.
   - `IS A TRADE ALLOWED?` is the real answer to "can I trade right now" —
     this is the only place both questions sit side by side.
5. **Trade only if the Final Gate allows it.** The Hero card (TradeNowCard)
   is the one and only decision surface (Rule 11). Every other panel explains
   or locates; none of them override it.

## Market close

1. **Check Calibration Watch** — note today's calibration score and whether
   it moved.
2. **Check Shadow Calibration** — note `sample_blocked` and
   `blocked_win_rate`. This is the evidence that eventually lets the
   calibration formula (not the threshold) be reviewed — see
   [[cat-freeze-observe-mode]] in memory.
3. **Session saves itself** — nothing to do manually. Memory, outcomes, and
   research data persist automatically (Supabase-backed).
4. Optional: if today's deploy was clean and you watched it run without
   issue, mark it as the rollback point:
   ```bash
   bash infra/rollback.sh --mark
   ```

## Incident

Use this whenever something looks wrong — a stuck WAIT, a panel showing
contradictory numbers, repeated restarts, or the dashboard just feels off.

1. **The system never places orders** — there is nothing to "kill" in the
   sense of stopping a live position, and there is no manual "freeze
   execution now" button, because execution is never something the software
   does on your behalf in the first place. (The Voice Narrator's "🚨
   Emergency override" checkbox is unrelated — it only controls whether the
   voice speaks during silent hours; it has no effect on any gate.) If you
   see something you don't like, close your own position in Dhan directly —
   that has always been true, independent of anything this dashboard says.
2. **Run the audit:**
   ```bash
   bash infra/final-audit.sh
   ```
   Read every 🔴 FAIL line — each one names the actual broken thing.
3. **Check backend/frontend directly:**
   ```bash
   curl http://127.0.0.1:8000/health
   curl -I http://127.0.0.1:3000/
   ```
4. **Check Dhan** — is `Broker: Connected` on the dashboard? If not, is
   today's access token still fresh (Settings)?
5. **Check logs:**
   ```bash
   tail -100 ~/Library/Logs/cloudaitrader-backend.log
   tail -20  ~/Library/Logs/cloudaitrader-watchdog.log
   ```
   The watchdog log is the honest record of restarts — if it's busy today,
   something is genuinely hanging, not a one-off.
6. **Roll back if required** — only if the audit shows a real regression
   and a `last-known-good` tag exists:
   ```bash
   bash infra/rollback.sh
   ```
   This asks for a typed `yes` before touching anything. It creates a new
   commit (never rewrites history) and restarts both services.
7. **If none of the above resolves it**, this is a genuine engineering
   question — bring the audit output and the last ~100 log lines to the next
   session rather than guessing at a fix live.

---

## What this runbook is not

- Not a substitute for `infra/final-audit.sh` — that script is the source of
  truth; this document just tells you when to run it.
- Not permission to change strategy, threshold, gate, or scoring code during
  an incident. A rollback restores known-good *code*; it is not itself a
  strategy decision. See [[cat-freeze-observe-mode]].
- Not a reason to add new dashboard widgets when something looks confusing —
  raise it as a finding first; most "confusing" readings turn out to be
  correctly-designed (see the Kill Switch / Safe Mode "green integrity, red
  execution" distinction that Decision Integrity was built to make legible).
