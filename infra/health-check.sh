#!/bin/bash
# On-demand health report (Phase 3). Run anytime: bash infra/health-check.sh
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"

status() {  # $1 url
  code="$(curl -s -o /dev/null -w '%{http_code}' --max-time 8 "$1" 2>/dev/null)"
  [ "$code" = "200" ] && echo "ONLINE" || { [ "$code" = "000" ] && echo "OFFLINE" || echo "DEGRADED ($code)"; }
}

bport() { lsof -ti :"$1" >/dev/null 2>&1 && echo "in use" || echo "free"; }
mem() {  # rss MB for a process pattern
  ps -Ao rss,command | grep -E "$1" | grep -v grep | awk '{s+=$1} END {printf "%.0f MB", s/1024}'
}

echo "CLOUD AI TRADER X PRO — health"
echo "-------------------------------"
echo "Backend  (:8000) : $(status http://localhost:8000/health)   port $(bport 8000)   mem $(mem 'uvicorn app.main')"
echo "Frontend (:3000) : $(status http://localhost:3000/)   port $(bport 3000)   mem $(mem 'next-server|next start')"
echo "Autostart agents :"
launchctl list 2>/dev/null | grep cloudaitrader || echo "  (not installed — run infra/install-autostart.command)"
