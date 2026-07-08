#!/bin/bash
# Cloud AI Trader X Pro — one-click launcher.
# Double-click this file in Finder to start both servers, then open the app.
cd "$(dirname "$0")"

echo "Starting Cloud AI Trader X Pro…"

# --- Backend (FastAPI on :8000) ---
cd backend
if [ ! -d ".venv" ]; then
  echo "First run: creating Python environment…"
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi
# stop any old instance, then start detached
pkill -f "uvicorn app.main:app" 2>/dev/null
nohup .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000 > /tmp/cat_backend.log 2>&1 &
cd ..

# --- Frontend (Next.js on :3000) ---
cd frontend
if [ ! -d "node_modules" ]; then
  echo "First run: installing frontend packages…"
  npm install
fi
pkill -f "next dev" 2>/dev/null
pkill -f "next-server" 2>/dev/null
nohup npm run dev > /tmp/cat_frontend.log 2>&1 &
cd ..

echo "Waiting for the dashboard to come up…"
until [ "$(curl -s -o /dev/null -w '%{http_code}' http://localhost:3000/ 2>/dev/null)" = "200" ]; do
  sleep 2
done

echo "Ready. Opening http://localhost:3000"
open http://localhost:3000
echo ""
echo "Both servers are running in the background."
echo "You can close this window — they will keep running."
echo "To stop them later, double-click stop.command."
