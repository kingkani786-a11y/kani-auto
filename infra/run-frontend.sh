#!/bin/bash
# Frontend launcher for launchd — production server (stable, low memory).
# Builds once if needed, then serves. `update.command` forces a fresh rebuild.
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"
cd "$(dirname "$0")/../frontend" || exit 1

[ -d node_modules ] || npm install
# BUILD_ID exists only after a production `next build` (a dev .next lacks it)
[ -f .next/BUILD_ID ] || npm run build

exec npm run start
