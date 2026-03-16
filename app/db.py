"""PostgreSQL connection pool and query helpers (async)."""
from decimal import Decimal

import asyncpg

from app.config import settings

_pool: asyncpg.Pool | None = None


async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            settings.database_url,
            min_size=5,
            max_size=30,
            command_timeout=10,
        )
    return _pool


async def close_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def _row_to_dict(row: asyncpg.Record) -> dict:
    """Convert an asyncpg Record to a plain dict with JSON-safe types."""
    d = dict(row)
    for k, v in d.items():
        if isinstance(v, Decimal):
            d[k] = float(v)
    return d


async def fetch_product(conn: asyncpg.Connection, stock_code: str) -> dict | None:
    row = await conn.fetchrow(
        "SELECT stock_code, description, price FROM products WHERE stock_code = $1",
        stock_code.strip(),
    )
    return _row_to_dict(row) if row else None


async def fetch_order_lines_by_invoice(conn: asyncpg.Connection, invoice: str) -> list[dict]:
    rows = await conn.fetch(
        """SELECT id, invoice, stock_code, description, quantity,
                  invoice_date, price, customer_id, country, year
           FROM order_lines WHERE invoice = $1
           ORDER BY id""",
        invoice.strip(),
    )
    return [_row_to_dict(r) for r in rows]


async def fetch_order_lines_by_customer(
    conn: asyncpg.Connection, customer_id: int, limit: int = 100, offset: int = 0,
) -> list[dict]:
    rows = await conn.fetch(
        """SELECT id, invoice, stock_code, description, quantity,
                  invoice_date, price, customer_id, country, year
           FROM order_lines WHERE customer_id = $1
           ORDER BY invoice_date DESC
           LIMIT $2 OFFSET $3""",
        customer_id, limit, offset,
    )
    return [_row_to_dict(r) for r in rows]


async def fetch_order_lines_by_country(
    conn: asyncpg.Connection, country: str, limit: int = 100, offset: int = 0,
) -> list[dict]:
    rows = await conn.fetch(
        """SELECT id, invoice, stock_code, description, quantity,
                  invoice_date, price, customer_id, country, year
           FROM order_lines WHERE country = $1
           ORDER BY invoice_date DESC
           LIMIT $2 OFFSET $3""",
        country.strip(), limit, offset,
    )
    return [_row_to_dict(r) for r in rows]


async def fetch_top_products(conn: asyncpg.Connection, limit: int = 10) -> list[dict]:
    """Top N products by total quantity sold."""
    rows = await conn.fetch(
        """SELECT stock_code,
                  COALESCE(MAX(description), '') AS description,
                  SUM(quantity) AS total_quantity,
                  ROUND(AVG(price)::numeric, 2) AS avg_price
           FROM order_lines
           WHERE quantity > 0
           GROUP BY stock_code
           ORDER BY total_quantity DESC
           LIMIT $1""",
        limit,
    )
    return [_row_to_dict(r) for r in rows]
