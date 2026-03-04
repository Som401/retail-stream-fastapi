#!/usr/bin/env bash
# Container entrypoint: load data if needed, then start the API.
set -e

echo "Checking if data is already loaded..."
# Try to count rows in order_lines. If table doesn't exist or is empty, load data.
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
    echo "Database is empty (${ROW_COUNT} rows). Loading CSV..."
    python scripts/load_data.py
    echo ""
else
    echo "Database already has ${ROW_COUNT} rows. Skipping load."
fi

echo "Starting API..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
