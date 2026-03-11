#!/bin/bash
# ============================================================
# start.sh — App Runner startup script
# Uses /app-local paths that survive the build → runtime copy
# ============================================================

set -e

# Bun and Python venv are under /app (copied from build stage)
export PATH="/app/.bun/bin:$PATH"
export PLAYWRIGHT_BROWSERS_PATH="/app/.playwright"

echo "=== Starting VNStock API service (port 8050) ==="
/app/venv/bin/python3 vnstock/vnstock_service.py &
VNSTOCK_PID=$!

# Wait up to 30s for VNStock health
echo "Waiting for VNStock to be healthy..."
for i in $(seq 1 15); do
  if curl -sf http://localhost:8050/health > /dev/null 2>&1; then
    echo "✅ VNStock is ready (attempt $i)"
    break
  fi
  if [ $i -eq 15 ]; then
    echo "⚠️  VNStock did not respond in time — Dexter will still start"
    echo "    Vietnamese stock tools may return errors until VNStock is ready"
  fi
  sleep 2
done

if ! kill -0 $VNSTOCK_PID 2>/dev/null; then
  echo "⚠️  VNStock process exited — check Python deps"
fi

echo "=== Starting Dexter HTTP server (port 3000) ==="
exec /app/.bun/bin/bun run dexter/src/server.ts
