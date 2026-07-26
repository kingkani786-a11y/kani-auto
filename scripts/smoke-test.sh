#!/usr/bin/env bash
# Cloud AI Trader — Docker smoke test (owner, 2026-07-26).
#
# Codifies the exact checks done manually during Phase 1 Docker verification,
# so the 3 real bugs found there (HOSTNAME binding, musl "localhost" ->
# IPv6 resolution, next.config.mjs build-time vs runtime env vars) — and the
# near-incident (Compose merging a ports: override instead of replacing it,
# briefly double-binding host port 8000) — can never silently regress.
#
# Runs identically on a dev machine and in CI (GitHub Actions): same script,
# same checks. Uses a unique Compose project name so it never collides with
# an already-running deployment, and BACKEND_PORT/FRONTEND_PORT so it can run
# side-by-side with one on the default ports.
#
# Usage:
#   ./scripts/smoke-test.sh                                    # ports 8000/3000
#   BACKEND_PORT=8001 FRONTEND_PORT=3001 ./scripts/smoke-test.sh   # side-by-side
#
# Exit 0 = every check passed. Exit 1 = first failure, with the reason printed.
set -euo pipefail
cd "$(dirname "$0")/.."

export BACKEND_PORT="${BACKEND_PORT:-8000}"
export FRONTEND_PORT="${FRONTEND_PORT:-3000}"
export GIT_COMMIT="${GIT_COMMIT:-$(git rev-parse --short HEAD 2>/dev/null || echo unknown)}"
PROJECT="cat-smoke-$$"

cleanup() {
  echo "--- tearing down smoke-test containers (project: $PROJECT) ---"
  docker compose -p "$PROJECT" down -v --remove-orphans >/dev/null 2>&1 || true
}
trap cleanup EXIT

fail() { echo "❌ SMOKE TEST FAILED: $1"; exit 1; }
pass() { echo "✅ $1"; }

echo "=== building (GIT_COMMIT=$GIT_COMMIT, ports $BACKEND_PORT/$FRONTEND_PORT) ==="
docker compose -p "$PROJECT" build

echo "=== starting ==="
docker compose -p "$PROJECT" up -d

echo "=== waiting for both containers to report healthy (max 60s) ==="
backend_cid=$(docker compose -p "$PROJECT" ps -q backend)
frontend_cid=$(docker compose -p "$PROJECT" ps -q frontend)
for i in $(seq 1 20); do
  sleep 3
  bh=$(docker inspect --format='{{.State.Health.Status}}' "$backend_cid" 2>/dev/null || echo "")
  fh=$(docker inspect --format='{{.State.Health.Status}}' "$frontend_cid" 2>/dev/null || echo "")
  [ "$bh" = "healthy" ] && [ "$fh" = "healthy" ] && break
done
[ "$bh" = "healthy" ] || fail "backend container health status: ${bh:-none} (expected healthy)"
pass "Backend Healthy"
[ "$fh" = "healthy" ] || fail "frontend container health status: ${fh:-none} (expected healthy)"
pass "Frontend Healthy"

echo "=== /health ==="
health=$(curl -sf "http://localhost:${BACKEND_PORT}/health") || fail "backend /health did not respond"
echo "$health" | grep -q '"ok":true' || fail "backend /health did not report ok:true — got: $health"
pass "Health Check PASS"

echo "=== /api/version (backend, direct) ==="
backend_version=$(curl -sf "http://localhost:${BACKEND_PORT}/api/version") || fail "backend /api/version did not respond"
backend_commit=$(echo "$backend_version" | python3 -c "import json,sys; print(json.load(sys.stdin)['backend_commit'])" 2>/dev/null || echo "")
[ -n "$backend_commit" ] || fail "backend /api/version had no backend_commit field — got: $backend_version"

echo "=== frontend serves the dashboard ==="
fe_status=$(curl -s -o /dev/null -w "%{http_code}" "http://localhost:${FRONTEND_PORT}/")
[ "$fe_status" = "200" ] || fail "frontend / returned HTTP $fe_status (expected 200)"

echo "=== API Proxy Working (frontend -> backend container, via Docker network) ==="
proxy_version=$(curl -sf "http://localhost:${FRONTEND_PORT}/api/version") || fail "frontend /api/version proxy did not respond"
proxy_commit=$(echo "$proxy_version" | python3 -c "import json,sys; print(json.load(sys.stdin)['backend_commit'])" 2>/dev/null || echo "")
[ -n "$proxy_commit" ] || fail "frontend /api/version proxy had no backend_commit field — got: $proxy_version (this is the exact failure mode of the BACKEND_URL build-time-vs-runtime bug found 2026-07-26)"
pass "API Proxy Working"
pass "Docker Network Working"

echo "=== Version Match (backend direct vs. through the proxy — proves the SAME backend answers both) ==="
[ "$backend_commit" = "$proxy_commit" ] || fail "version mismatch: direct backend=$backend_commit, via frontend proxy=$proxy_commit"
pass "Version Match ($backend_commit)"

if [ "$GIT_COMMIT" != "unknown" ]; then
  [ "$backend_commit" = "$GIT_COMMIT" ] || fail "backend_commit ($backend_commit) does not match the commit being built ($GIT_COMMIT) — GIT_COMMIT build arg not reaching the image"
  pass "backend_commit matches the commit under test ($GIT_COMMIT)"
fi

echo
echo "✅✅✅ SMOKE TEST PASS — all checks green ($BACKEND_PORT/$FRONTEND_PORT, commit $GIT_COMMIT)"
exit 0
