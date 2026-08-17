#!/usr/bin/env bash
# Deploy legal-os: Fly backend + Vercel frontend, then health-check both.
# Usage: ./scripts/deploy.sh   (or `make deploy`)
set -uo pipefail

BACKEND_HEALTH="https://legal-os-api.fly.dev/health"
FRONTEND_URL="https://legal.sickofancy.ai"

wait_healthy() {
  local url="$1" name="$2"
  echo -n "  waiting for $name"
  for _ in $(seq 1 24); do
    local code
    code=$(curl -s -o /dev/null -w "%{http_code}" "$url" 2>/dev/null || echo 000)
    if [ "$code" = "200" ]; then
      echo "  ✓ ($code)"
      return 0
    fi
    echo -n "."
    sleep 5
  done
  echo "  ✗ (last $code)"
  return 1
}

echo "=== Deploying backend (Fly) ==="
(cd backend && fly deploy) || { echo "✗ backend deploy failed"; exit 1; }
wait_healthy "$BACKEND_HEALTH" "backend" || exit 1

echo "=== Deploying frontend (Vercel) ==="
(cd frontend && vercel --prod --yes) || { echo "✗ frontend deploy failed"; exit 1; }
wait_healthy "$FRONTEND_URL" "frontend" || exit 1

echo "=== Deploy complete — both services healthy ==="
