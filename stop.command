#!/bin/bash
# Cloud AI Trader X Pro — stop both servers. Double-click in Finder.
echo "Stopping Cloud AI Trader X Pro…"
pkill -f "uvicorn app.main:app" 2>/dev/null && echo "Backend stopped." || echo "Backend was not running."
pkill -f "next dev" 2>/dev/null
pkill -f "next-server" 2>/dev/null && echo "Frontend stopped." || echo "Frontend was not running."
echo "Done. You can close this window."
