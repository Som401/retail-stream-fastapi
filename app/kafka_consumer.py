"""
Kafka consumer worker — picks up order events and writes them to PostgreSQL.

Run as a standalone process:  python -m app.kafka_consumer
"""
import asyncio
import json
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import asyncpg
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError

from app.config import settings

MAX_RETRIES = 30
RETRY_DELAY = 5


async def process_order(conn: asyncpg.Connection, order: dict) -> None:
    """Insert a single order into the order_lines table."""
    await conn.execute(
        """INSERT INTO order_lines
           (invoice, stock_code, description, quantity, invoice_date, price, customer_id, country, year)
           VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9)""",
        str(order.get("invoice", "")),
        str(order.get("stock_code", "")),
        order.get("description"),
        int(order.get("quantity", 0)),
        datetime.fromisoformat(order["invoice_date"]).replace(tzinfo=None) if "invoice_date" in order else datetime.utcnow(),
        float(order.get("price", 0)),
        order.get("customer_id"),
        order.get("country"),
        order.get("year"),
    )


async def create_consumer() -> AIOKafkaConsumer:
    """Create and start a Kafka consumer with retry logic."""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            consumer = AIOKafkaConsumer(
                settings.kafka_order_topic,
                bootstrap_servers=settings.kafka_bootstrap_servers,
                group_id="order-processor",
                value_deserializer=lambda v: json.loads(v.decode("utf-8")),
                auto_offset_reset="earliest",
                retry_backoff_ms=1000,
                request_timeout_ms=30000,
            )
            await consumer.start()
            print(f"Consumer connected on attempt {attempt}")
            return consumer
        except (KafkaConnectionError, Exception) as e:
            print(f"Attempt {attempt}/{MAX_RETRIES}: Kafka not ready ({e}). Retrying in {RETRY_DELAY}s...")
            await asyncio.sleep(RETRY_DELAY)

    raise RuntimeError(f"Failed to connect to Kafka after {MAX_RETRIES} attempts")


async def run_consumer() -> None:
    print(f"Kafka consumer starting — topic: {settings.kafka_order_topic}")
    print(f"Kafka broker: {settings.kafka_bootstrap_servers}")
    print(f"Postgres: {settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}")

    pool = await asyncpg.create_pool(
        settings.database_url, min_size=1, max_size=5, command_timeout=10,
    )

    consumer = await create_consumer()
    print("Consumer is listening for order events...")

    try:
        async for msg in consumer:
            order = msg.value
            try:
                async with pool.acquire() as conn:
                    await process_order(conn, order)
                print(f"  Processed order: invoice={order.get('invoice')} stock={order.get('stock_code')}")
            except Exception as e:
                print(f"  Error processing order: {e}")
    finally:
        await consumer.stop()
        await pool.close()


if __name__ == "__main__":
    asyncio.run(run_consumer())
