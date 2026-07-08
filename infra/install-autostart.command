#!/bin/bash
# Install always-on autostart (Phase 1/2/5). Double-click in Finder once.
# Installs three LaunchAgents: backend, frontend, watchdog. They start now,
# on every login, after reboot, and auto-restart on crash — no Terminal needed.
set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"   # project root (absolute, space-safe)
LA="$HOME/Library/LaunchAgents"
mkdir -p "$LA" "$HOME/Library/Logs"

echo "Installing Cloud AI Trader autostart from:"
echo "  $DIR"

# stop any manually-started servers so the agents own the ports
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "next dev" 2>/dev/null || true
pkill -f "next-server" 2>/dev/null || true
sleep 1

chmod +x "$DIR/infra/"*.sh

for svc in backend frontend watchdog; do
  src="$DIR/infra/com.cloudaitrader.$svc.plist"
  dst="$LA/com.cloudaitrader.$svc.plist"
  sed -e "s#__PROJECT_DIR__#$DIR#g" -e "s#__HOME__#$HOME#g" "$src" > "$dst"
  launchctl unload "$dst" 2>/dev/null || true
  launchctl load -w "$dst"
  echo "  loaded com.cloudaitrader.$svc"
done

echo ""
echo "Done. The app now starts automatically and self-restarts."
echo "Bringing the dashboard up (first frontend build may take ~1 min)…"
for i in $(seq 1 90); do
  if curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/ 2>/dev/null | grep -q 200; then
    open http://localhost:3000; echo "Dashboard is up."; break
  fi
  sleep 2
done
echo "Tip: check status anytime with  bash infra/health-check.sh"
