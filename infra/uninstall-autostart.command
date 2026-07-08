#!/bin/bash
# Remove the always-on autostart. Double-click in Finder.
LA="$HOME/Library/LaunchAgents"
for svc in backend frontend watchdog; do
  dst="$LA/com.cloudaitrader.$svc.plist"
  launchctl unload "$dst" 2>/dev/null || true
  rm -f "$dst"
  echo "removed com.cloudaitrader.$svc"
done
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "next-server" 2>/dev/null || true
echo "Autostart removed. The app will no longer start on its own."
