# Cloud AI Trader X Pro — Always-On (macOS)

Infrastructure-only. No app code, UI, or trading logic is involved here.

## Why the project lives in `~/cloud-ai-trader`

macOS **TCC privacy** blocks `launchd` background services from reading
`~/Desktop`, `~/Documents`, and `~/Downloads`. Auto-start agents there fail
with `Operation not permitted`. The project was therefore moved to
`~/cloud-ai-trader` (home root, not protected) so the agents run freely with
**no Full Disk Access prompt and no manual steps**.

> Do not move the project back under Desktop/Documents/Downloads or autostart
> will break.

## What's installed (3 LaunchAgents in `~/Library/LaunchAgents`)

| Agent | Role |
|---|---|
| `com.cloudaitrader.backend` | FastAPI on :8000 — `RunAtLoad` + `KeepAlive` |
| `com.cloudaitrader.frontend` | Next.js production on :3000 — `RunAtLoad` + `KeepAlive` |
| `com.cloudaitrader.watchdog` | every 60s: HTTP-checks both; restarts a hung one |

This delivers the spec's phases:
- **Auto-start** on login and after reboot (`RunAtLoad`).
- **Process supervision / crash recovery** — `KeepAlive` respawns a crashed
  process within ~10s (verified: killing the backend respawned it automatically).
- **Hung-process recovery** — the watchdog catches "alive but unresponsive"
  (a curl that fails twice → `launchctl kickstart`).

## You never need the Terminal

| Want to… | Do this |
|---|---|
| Check status | `bash infra/health-check.sh` (shows ONLINE/DEGRADED/OFFLINE) |
| Install / re-enable autostart | double-click `infra/install-autostart.command` |
| Turn autostart off | double-click `infra/uninstall-autostart.command` |
| Apply code changes to the live app | double-click `infra/update.command` (rebuild + restart) |

Logs: `~/Library/Logs/cloudaitrader-{backend,frontend,watchdog}.log`.

> With autostart installed, **don't** use the old `start.command` — it would
> fight launchd for the ports. Use the agents (or `update.command`) instead.

## After any restart

The broker access token is held in memory only (never written to disk), and
Dhan rotates it daily — so after a reboot or token expiry, open the app and
**Settings → SAVE & CONNECT** once. Everything else is automatic.

## Truly always-on (any network, any device)

LaunchAgents keep it up **while this Mac is on and you're logged in**. For a
permanent public URL reachable from phone/anywhere (`app.cloudaitrader.com`),
deploy to Vercel + Railway — see `docs/DEPLOYMENT.md`. That removes the
localhost dependency entirely (Phase 6/7).
