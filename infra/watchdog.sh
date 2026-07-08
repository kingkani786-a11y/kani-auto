#!/bin/bash
# HTTP watchdog (Phase 3/5): catches the "process alive but unresponsive" case
# that KeepAlive alone can't. Runs every 60s via its own LaunchAgent. If a
# health URL fails twice, it kicks the LaunchAgent so launchd respawns it.
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"
LOG="$HOME/Library/Logs/cloudaitrader-watchdog.log"
UID_NUM="$(id -u)"

check() {  # $1 url  $2 label  $3 agent-label
  if ! curl -sf --max-time 8 "$1" >/dev/null 2>&1; then
    sleep 5
    if ! curl -sf --max-time 8 "$1" >/dev/null 2>&1; then
      echo "$(date '+%F %T') $2 unresponsive — restarting" >> "$LOG"
      launchctl kickstart -k "gui/$UID_NUM/$3" 2>/dev/null
    fi
  fi
}

check "http://localhost:8000/health"  "backend"  "com.cloudaitrader.backend"
check "http://localhost:3000/"        "frontend" "com.cloudaitrader.frontend"
