#!/bin/bash
# Backend launcher for launchd. `exec` so launchd supervises the real process
# (KeepAlive restarts THIS on crash). PATH is set because launchd starts with
# a minimal environment.
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
cd "$(dirname "$0")/../backend" || exit 1

# first-run self-heal: create venv + deps if missing
if [ ! -x ".venv/bin/uvicorn" ]; then
  python3 -m venv .venv
  .venv/bin/pip install -q -r requirements.txt
fi

exec .venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000
