#!/bin/bash
# ROLLBACK TO LAST KNOWN GOOD — V7 Finalization item 10 (owner, 2026-08-11).
#
# Two modes:
#   infra/rollback.sh --mark     Tag the CURRENT commit as last-known-good.
#                                 Run this after a verified, working deploy —
#                                 e.g. right after a push you've watched run
#                                 clean through a live market session.
#   infra/rollback.sh            Roll the repo back to that tag and restart
#                                 both services. Destructive: requires typing
#                                 "yes" — this is not a step that should ever
#                                 run by accident or unattended.
#
# What this does NOT do: touch git history (no reset --hard, no force-push —
# it creates a new revert commit), change any threshold/gate/strategy file
# (a rollback restores code, it is not itself a strategy decision), or run
# without a human present to type "yes".
set -e
export PATH="/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin"
cd "$(dirname "$0")/.." || exit 1
TAG="last-known-good"

if [ "$1" = "--mark" ]; then
  if [ -n "$(git status --porcelain)" ]; then
    echo "🔴 Working tree is not clean — commit or stash first, then re-mark."
    git status --short
    exit 1
  fi
  CUR="$(git rev-parse --short HEAD)"
  git tag -f "$TAG" HEAD
  echo "🟢 Marked $CUR as last-known-good."
  echo "   Push the tag if you want it to survive a fresh clone:"
  echo "   git push origin $TAG --force"
  exit 0
fi

if ! git rev-parse -q --verify "refs/tags/$TAG" >/dev/null 2>&1; then
  echo "🔴 No '$TAG' tag exists yet. Run 'infra/rollback.sh --mark' after your"
  echo "   next verified-good deploy, then this command will have something"
  echo "   to roll back to."
  exit 1
fi

GOOD_SHA="$(git rev-parse --short "$TAG")"
CUR_SHA="$(git rev-parse --short HEAD)"

if [ "$GOOD_SHA" = "$CUR_SHA" ]; then
  echo "🟢 Already at last-known-good ($GOOD_SHA). Nothing to roll back."
  exit 0
fi

echo "═══════════════════════════════════════════════════════════════"
echo "  ROLLBACK TO LAST KNOWN GOOD"
echo "═══════════════════════════════════════════════════════════════"
echo "  Current HEAD:      $CUR_SHA"
echo "  Rolling back to:   $GOOD_SHA  (tag: $TAG)"
echo
echo "  Commits between them (newest first):"
git log --oneline "$TAG..HEAD" | sed 's/^/    /'
echo
echo "  This creates a NEW commit that reverts to $GOOD_SHA's state — it"
echo "  does not rewrite history, and it will restart both services."
echo "═══════════════════════════════════════════════════════════════"
read -r -p "  Type 'yes' to proceed: " CONFIRM
if [ "$CONFIRM" != "yes" ]; then
  echo "  Aborted — nothing changed."
  exit 1
fi

git checkout "$TAG" -- .
git add -A
git commit -m "rollback: restore last-known-good ($GOOD_SHA)

Reverts working tree to the state tagged last-known-good, via
infra/rollback.sh. Not a history rewrite — a new commit." \
  --allow-empty

echo "  Committed. Restarting services..."
launchctl kickstart -k "gui/$(id -u)/com.cloudaitrader.backend" 2>/dev/null
launchctl kickstart -k "gui/$(id -u)/com.cloudaitrader.frontend" 2>/dev/null

echo "  Waiting for backend to come back..."
for _ in $(seq 1 30); do
  curl -sf --max-time 3 http://127.0.0.1:8000/health >/dev/null 2>&1 && break
  sleep 2
done

echo
echo "🟢 Rollback complete. Run infra/final-audit.sh to verify."
