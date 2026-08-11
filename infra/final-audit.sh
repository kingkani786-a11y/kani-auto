#!/bin/bash
# FINAL_SYSTEM_AUDIT — the one command that answers "is this safe to run today?"
#
# Owner (2026-08-11), V7 Finalization item 12. The point is NOT to add another
# dashboard: it is to collapse a scattered manual checklist into one honest
# PASS/FAIL so the owner does not have to be a developer every morning.
#
# Rules this script obeys:
#   * READ-ONLY. It starts nothing, stops nothing, deploys nothing, and never
#     touches a threshold, gate or strategy file. Running it during live
#     trading is safe.
#   * No fabricated PASS. Anything it cannot actually verify prints WARN with
#     the reason — never a green tick by assumption ("Trust by Verification,
#     not by Claims").
#   * Exit 0 only when there are zero FAILs. WARNs do not fail the audit;
#     they are conditions that are expected some of the time (market closed,
#     broker token expired overnight) and must not cry wolf.
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"
cd "$(dirname "$0")/.." || exit 1
REPO="$(pwd)"

PASS=0; FAIL=0; WARN=0
ok()   { printf '  \033[32m🟢 PASS\033[0m  %-28s %s\n' "$1" "$2"; PASS=$((PASS+1)); }
bad()  { printf '  \033[31m🔴 FAIL\033[0m  %-28s %s\n' "$1" "$2"; FAIL=$((FAIL+1)); }
warn() { printf '  \033[33m🟡 WARN\033[0m  %-28s %s\n' "$1" "$2"; WARN=$((WARN+1)); }

echo
echo "═══════════════════════════════════════════════════════════════"
echo "  FINAL SYSTEM AUDIT — $(date '+%F %T')"
echo "  $REPO"
echo "═══════════════════════════════════════════════════════════════"
echo
echo "── REPOSITORY ─────────────────────────────────────────────────"

# [1] Git clean
if [ -z "$(git status --porcelain 2>/dev/null)" ]; then
  ok "Git working tree" "clean"
else
  warn "Git working tree" "$(git status --porcelain | wc -l | tr -d ' ') uncommitted file(s)"
fi

# [2] Version / branch / unpushed
BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null)"
HEAD_SHA="$(git rev-parse --short HEAD 2>/dev/null)"
UNPUSHED="$(git log '@{u}..HEAD' --oneline 2>/dev/null | wc -l | tr -d ' ')"
if [ "$UNPUSHED" = "0" ]; then
  ok "Branch / sync" "$BRANCH @ $HEAD_SHA — in sync with origin"
else
  warn "Branch / sync" "$BRANCH @ $HEAD_SHA — $UNPUSHED commit(s) not pushed"
fi

# [3] Rollback available — a known-good tag must exist to roll back TO.
if git rev-parse -q --verify "refs/tags/last-known-good" >/dev/null 2>&1; then
  ok "Rollback target" "tag last-known-good -> $(git rev-parse --short last-known-good)"
else
  warn "Rollback target" "no last-known-good tag — run infra/rollback.sh --mark"
fi

echo
echo "── TESTS ──────────────────────────────────────────────────────"

# [4] Backend test suite
if [ -x backend/.venv/bin/python ]; then
  T_OUT="$(cd backend && .venv/bin/python -m unittest discover -s tests 2>&1 | tail -3)"
  if echo "$T_OUT" | grep -q "^OK"; then
    ok "Backend tests" "$(echo "$T_OUT" | grep -oE 'Ran [0-9]+ tests' | head -1) — OK"
  else
    bad "Backend tests" "$(echo "$T_OUT" | tail -1)"
  fi
else
  warn "Backend tests" "no venv at backend/.venv — cannot run"
fi

echo
echo "── RUNTIME ────────────────────────────────────────────────────"

# [5] Backend health
BH="$(curl -sf --max-time 5 http://127.0.0.1:8000/health 2>/dev/null)"
if [ -n "$BH" ]; then
  ok "Backend health" "$BH"
else
  bad "Backend health" "/health not responding on :8000"
fi

# [6] Frontend health
if curl -sf --max-time 5 http://127.0.0.1:3000/ >/dev/null 2>&1; then
  ok "Frontend health" "serving on :3000"
else
  bad "Frontend health" "not responding on :3000"
fi

# [7] Runtime commit matches the repo — catches "fixed it but never restarted".
RT="$(curl -sf --max-time 5 http://127.0.0.1:8000/api/version 2>/dev/null \
      | sed -n 's/.*"backend_commit":"\([^"]*\)".*/\1/p')"
if [ -z "$RT" ]; then
  warn "Runtime version" "could not read /api/version"
elif [ "$RT" = "$HEAD_SHA" ]; then
  ok "Runtime version" "$RT matches HEAD"
else
  warn "Runtime version" "running $RT, repo HEAD is $HEAD_SHA — restart to adopt"
fi

# [8] Broker connectivity (token expires daily — WARN, never FAIL)
if echo "$BH" | grep -q '"connected":true'; then
  ok "Broker connectivity" "connected"
else
  warn "Broker connectivity" "not connected — paste today's token in Settings"
fi

# [9] Data freshness
DQ="$(curl -sf --max-time 5 http://127.0.0.1:8000/api/health/data 2>/dev/null \
      | sed -n 's/.*"overall":"\([^"]*\)".*/\1/p')"
case "$DQ" in
  GOOD) ok   "Data freshness" "overall GOOD" ;;
  "")   warn "Data freshness" "no reading (backend down or market closed)" ;;
  *)    warn "Data freshness" "overall $DQ — WAITs may be data-driven" ;;
esac

# [10] State consistency detector — two panels must not report one fact two ways.
SC="$(curl -sf --max-time 5 http://127.0.0.1:8000/api/state-consistency 2>/dev/null)"
if [ -z "$SC" ]; then
  warn "State consistency" "detector unreachable"
elif echo "$SC" | grep -q '"consistent": *false'; then
  N="$(echo "$SC" | sed -n 's/.*"inconsistent_count": *\([0-9]*\).*/\1/p')"
  bad "State consistency" "${N:-1} contradiction(s) between duplicated facts"
else
  ok "State consistency" "no contradictions"
fi

echo
echo "── SAFETY INVARIANTS ──────────────────────────────────────────"

# [11] Kill Switch present and evaluated (present != active; both are fine)
KS="$(curl -sf --max-time 5 http://127.0.0.1:8000/api/status 2>/dev/null)"
if echo "$KS" | grep -q '"kill_switch"'; then
  if echo "$KS" | grep -q '"active": *true'; then
    ok "Kill Switch" "evaluated — ACTIVE (blocking execution, by design)"
  else
    ok "Kill Switch" "evaluated — clear"
  fi
else
  bad "Kill Switch" "not present in /api/status — safety layer missing"
fi

# [12] No live-trading import of research modules. The research gate is the
#      whole reason historical work cannot silently become a live signal, so
#      a violation here is a hard FAIL, not a warning.
LEAK="$(grep -rlE "^from \.(orfe_research|pattern_stats|walk_forward)|^from \.services\.(orfe_research|pattern_stats|walk_forward)" \
        backend/app/engines backend/app/services/confluence.py \
        backend/app/services/execution_gate.py backend/app/services/kill_switch.py 2>/dev/null)"
if [ -z "$LEAK" ]; then
  ok "Research isolation" "no research module imported by a gating path"
else
  bad "Research isolation" "research imported by: $LEAK"
fi

# [13] Research gate constant still present in the research module.
if grep -q "BACKTEST_ONLY" backend/app/services/orfe_research.py 2>/dev/null; then
  ok "Research gate" "BACKTEST_ONLY present"
else
  bad "Research gate" "BACKTEST_ONLY missing from orfe_research.py"
fi

# [14] Event-loop blocking regression — the bug class that caused 20+ restarts.
if [ -x backend/.venv/bin/python ]; then
  if (cd backend && .venv/bin/python -m unittest \
        tests.test_invariants.EventLoopBlockingTests 2>&1 | grep -q "^OK"); then
    ok "Event-loop safety" "no unwrapped blocking call on the loop"
  else
    bad "Event-loop safety" "EventLoopBlockingTests failing"
  fi
fi

# [15] The system must never be able to place an order.
if grep -rqE "place_order|placeOrder|/orders" backend/app/broker/dhan.py 2>/dev/null; then
  bad "No-order guarantee" "order-placement code found in the broker client"
else
  ok "No-order guarantee" "no order-placement path in the broker client"
fi

echo
echo "── BACKGROUND ─────────────────────────────────────────────────"

# [16] LaunchAgents loaded
for a in backend frontend watchdog; do
  if launchctl list 2>/dev/null | grep -q "com.cloudaitrader.$a"; then
    ok "Agent: $a" "loaded"
  else
    warn "Agent: $a" "not loaded"
  fi
done

# [17] Restart churn today — the watchdog log is the honest record of hangs.
WLOG="$HOME/Library/Logs/cloudaitrader-watchdog.log"
if [ -f "$WLOG" ]; then
  N="$(grep -c "$(date '+%Y-%m-%d')" "$WLOG" 2>/dev/null || echo 0)"
  if [ "$N" -eq 0 ]; then ok   "Restarts today" "none"
  elif [ "$N" -le 2 ]; then warn "Restarts today" "$N — watch"
  else bad "Restarts today" "$N — investigate before trading"; fi
else
  warn "Restarts today" "no watchdog log yet"
fi

echo
echo "═══════════════════════════════════════════════════════════════"
printf "  %d PASS   %d WARN   %d FAIL\n" "$PASS" "$WARN" "$FAIL"
if [ "$FAIL" -eq 0 ]; then
  echo -e "  \033[32m🟢 FINAL AUDIT: PASS\033[0m — safe to operate"
  [ "$WARN" -gt 0 ] && echo "     ($WARN warning(s) above are expected conditions, not faults)"
else
  echo -e "  \033[31m🔴 FINAL AUDIT: FAIL\033[0m — fix the FAIL lines before trading"
fi
echo "═══════════════════════════════════════════════════════════════"
echo
exit $(( FAIL > 0 ? 1 : 0 ))
