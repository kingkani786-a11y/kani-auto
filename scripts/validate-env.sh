#!/usr/bin/env bash
# Environment Validation (owner, 2026-07-26) — confirms backend/.env.example
# stays the source of truth for what config CAN be set, and flags anything
# backend/.env is missing relative to it. Never checks VALUES (secrets stay
# out of this script's output) — only whether each documented KEY is present.
set -euo pipefail
cd "$(dirname "$0")/.."

EXAMPLE="backend/.env.example"
REAL="backend/.env"

[ -f "$EXAMPLE" ] || { echo "❌ $EXAMPLE missing — nothing to validate against"; exit 1; }

example_keys=$(grep -oE '^[A-Z_]+=' "$EXAMPLE" | tr -d '=' | sort -u)

if [ ! -f "$REAL" ]; then
  echo "⚠️  $REAL does not exist — fine for CI (env_file is optional there), but a real deployment needs it."
  echo "Documented keys ($EXAMPLE):"
  echo "$example_keys" | sed 's/^/  - /'
  exit 0
fi

real_keys=$(grep -oE '^[A-Z_]+=' "$REAL" | tr -d '=' | sort -u)
missing=$(comm -23 <(echo "$example_keys") <(echo "$real_keys"))

if [ -n "$missing" ]; then
  echo "⚠️  $REAL is missing keys that $EXAMPLE documents (may be intentional if you don't use that feature):"
  echo "$missing" | sed 's/^/  - /'
else
  echo "✅ Environment Validation PASS — every key in $EXAMPLE is present in $REAL"
fi
