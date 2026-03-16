#!/usr/bin/env bash
# Deploy latest main branch on the VM using docker compose / docker-compose.
set -euo pipefail

APP_SCALE="${1:-5}"
PROJECT_DIR="${PROJECT_DIR:-$HOME/retail-stream-fastapi}"

if docker compose version >/dev/null 2>&1; then
  COMPOSE_CMD="docker compose"
elif command -v docker-compose >/dev/null 2>&1; then
  COMPOSE_CMD="docker-compose"
else
  echo "ERROR: Neither 'docker compose' nor 'docker-compose' is installed."
  exit 1
fi

echo "Deploying project from: ${PROJECT_DIR}"
cd "${PROJECT_DIR}"

if [ ! -f "online_retail_all.csv" ]; then
  echo "ERROR: online_retail_all.csv not found in ${PROJECT_DIR}."
  echo "Upload it first (the file is intentionally not stored in GitHub)."
  exit 1
fi

echo "Updating source code to origin/main..."
git fetch origin main
git reset --hard origin/main

echo "Starting containers..."
# Backward-compatible deploy:
# - If service 'app' exists (old compose), use --scale app=N
# - Otherwise (new compose with app1/app2/app3), run standard up
if ${COMPOSE_CMD} config --services | grep -qx "app"; then
  echo "Detected service 'app'. Using scale=${APP_SCALE}."
  ${COMPOSE_CMD} up -d --build --scale app="${APP_SCALE}"
else
  echo "No 'app' service detected. Using static app services from compose."
  ${COMPOSE_CMD} up -d --build
fi

echo "Container status:"
${COMPOSE_CMD} ps

echo "Health check (via Nginx):"
sleep 3
curl -fsS "http://localhost/health" || true
