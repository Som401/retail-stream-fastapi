#!/usr/bin/env bash
# Container entrypoint — supports two modes:
#   MODE=api      (default) → load data if needed, then start uvicorn
#   MODE=consumer           → start Kafka consumer worker
set -e

MODE="${MODE:-api}"

if [ "$MODE" = "consumer" ]; then
    echo "Starting Kafka consumer worker..."
    exec python -m app.kafka_consumer
fi

# --- API mode ---
echo "Checking if data is already loaded..."
ROW_COUNT=$(python -c "
import asyncio, asyncpg, os
async def check():
    conn = await asyncpg.connect(
        host=os.environ.get('APP_POSTGRES_HOST', 'localhost'),
        port=int(os.environ.get('APP_POSTGRES_PORT', '5432')),
        user=os.environ.get('APP_POSTGRES_USER', 'retail'),
        password=os.environ.get('APP_POSTGRES_PASSWORD', 'retail'),
        database=os.environ.get('APP_POSTGRES_DB', 'retail'),
    )
    try:
        return await conn.fetchval('SELECT COUNT(*) FROM order_lines')
    except:
        return 0
    finally:
        await conn.close()
print(asyncio.run(check()))
" 2>/dev/null || echo "0")

if [ "$ROW_COUNT" -lt 1000 ]; then
    CSV_PATH="${APP_CSV_PATH:-/app/online_retail_all.csv}"
    if [ -f "$CSV_PATH" ]; then
        echo "Database is empty (${ROW_COUNT} rows). Loading CSV from ${CSV_PATH}..."
        if ! python scripts/load_data.py; then
            echo "Warning: data load failed on this node; continuing to start API."
        fi
        echo ""
    else
        echo "Database is empty (${ROW_COUNT} rows) but CSV not found at ${CSV_PATH}; skipping load on this node."
    fi
else
    echo "Database already has ${ROW_COUNT} rows. Skipping load."
fi

WORKERS="${UVICORN_WORKERS:-1}"
echo "Starting API with ${WORKERS} uvicorn worker(s)..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers "$WORKERS"
