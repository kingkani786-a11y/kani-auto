#!/bin/bash
# Rebuild the frontend with the latest code and restart the agents.
# Use after code changes so the always-on production server serves the update.
set -e
DIR="$(cd "$(dirname "$0")/.." && pwd)"
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"
UID_NUM="$(id -u)"

echo "Rebuilding frontend…"
cd "$DIR/frontend"
rm -rf .next
npm run build

echo "Restarting services…"
launchctl kickstart -k "gui/$UID_NUM/com.cloudaitrader.backend"  2>/dev/null || true
launchctl kickstart -k "gui/$UID_NUM/com.cloudaitrader.frontend" 2>/dev/null || true
echo "Done. Latest code is live."
