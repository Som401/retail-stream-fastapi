#!/usr/bin/env python3
"""
Load online_retail_all.csv into PostgreSQL (order_lines + products).
Uses COPY for fast bulk loading instead of row-by-row INSERT.
"""
import asyncio
import csv
import io
import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

try:
    import asyncpg
except ImportError:
    print("Install asyncpg: pip install asyncpg")
    sys.exit(1)

POSTGRES_HOST = os.environ.get("APP_POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.environ.get("APP_POSTGRES_PORT", "5432"))
POSTGRES_USER = os.environ.get("APP_POSTGRES_USER", "retail")
POSTGRES_PASSWORD = os.environ.get("APP_POSTGRES_PASSWORD", "retail")
POSTGRES_DB = os.environ.get("APP_POSTGRES_DB", "retail")
DATABASE_URL = (
    f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
    f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
)

CSV_PATH = ROOT / "online_retail_all.csv"
BATCH_SIZE = 50_000


def parse_row(row: dict) -> tuple | None:
    """Parse a CSV dict-row into a tuple for insertion. Returns None if row is invalid."""
    invoice = (row.get("Invoice") or "").strip()
    stock_code = (row.get("StockCode") or "").strip()
    description = (row.get("Description") or "").strip() or None
    country = (row.get("Country") or "").strip() or None
    year = (row.get("year") or "").strip() or None

    if not invoice or not stock_code:
        return None

    try:
        quantity = int(float(row.get("Quantity", "")))
    except (ValueError, TypeError):
        return None

    try:
        price = float(row.get("Price", ""))
    except (ValueError, TypeError):
        return None

    try:
        invoice_date = datetime.strptime(
            (row.get("InvoiceDate") or "").strip(), "%Y-%m-%d %H:%M:%S"
        )
    except (ValueError, TypeError):
        return None

    customer_id_raw = (row.get("Customer ID") or "").strip()
    customer_id = None
    if customer_id_raw:
        try:
            customer_id = int(float(customer_id_raw))
        except (ValueError, TypeError):
            pass

    return (invoice, stock_code, description, quantity, invoice_date, price, customer_id, country, year)


async def create_tables(conn: asyncpg.Connection) -> None:
    """Run init_db.sql to create schema."""
    sql_path = ROOT / "scripts" / "init_db.sql"
    sql = sql_path.read_text()
    await conn.execute(sql)
    print("  Tables created.")


async def load_csv(conn: asyncpg.Connection) -> int:
    """Bulk-load CSV into order_lines using COPY (much faster than INSERT)."""
    if not CSV_PATH.exists():
        print(f"CSV not found: {CSV_PATH}")
        sys.exit(1)

    columns = [
        "invoice", "stock_code", "description", "quantity",
        "invoice_date", "price", "customer_id", "country", "year",
    ]
    inserted = 0
    batch: list[tuple] = []

    with open(CSV_PATH, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f)
        for row in reader:
            parsed = parse_row(row)
            if parsed is None:
                continue
            batch.append(parsed)

            if len(batch) >= BATCH_SIZE:
                await conn.copy_records_to_table(
                    "order_lines", records=batch, columns=columns,
                )
                inserted += len(batch)
                print(f"  order_lines: {inserted:,} rows ...")
                batch = []

    if batch:
        await conn.copy_records_to_table(
            "order_lines", records=batch, columns=columns,
        )
        inserted += len(batch)

    print(f"  order_lines: {inserted:,} rows total.")
    return inserted


async def build_products(conn: asyncpg.Connection) -> None:
    """Derive products table from order_lines (distinct stock_code, latest description, avg price)."""
    await conn.execute("""
        INSERT INTO products (stock_code, description, price)
        SELECT stock_code,
               COALESCE(MAX(description), '') AS description,
               ROUND(AVG(price)::numeric, 2) AS price
        FROM order_lines
        GROUP BY stock_code
        ON CONFLICT (stock_code) DO UPDATE SET
            description = EXCLUDED.description,
            price = EXCLUDED.price
    """)
    count = await conn.fetchval("SELECT COUNT(*) FROM products")
    print(f"  products: {count:,} distinct products.")


async def main() -> None:
    print(f"Connecting to {POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB} ...")
    conn = await asyncpg.connect(DATABASE_URL)
    try:
        print("Creating tables ...")
        await create_tables(conn)
        print("Loading CSV ...")
        await load_csv(conn)
        print("Building products table ...")
        await build_products(conn)
        print("Done.")
    finally:
        await conn.close()


if __name__ == "__main__":
    asyncio.run(main())
