#!/usr/bin/env bash
# Load schema and sample data into PostgreSQL.
# Run from project root after: docker compose up -d
set -e
cd "$(dirname "$0")/.."
docker compose up -d postgres 2>/dev/null || true
sleep 2
docker exec -i "$(docker compose ps -q postgres)" psql -U retail -d retail < scripts/init_db.sql
echo "Done: products table and sample data loaded."
