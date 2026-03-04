"""
Retail Stream API – Backend with cache-aside (Redis) for product reads.

Dataset: Online Retail (Invoice, StockCode, Description, Quantity,
InvoiceDate, Price, Customer ID, Country, year).
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Query

from app.cache import get_cached_product, set_cached_product
from app.db import (
    close_pool,
    fetch_order_lines_by_country,
    fetch_order_lines_by_customer,
    fetch_order_lines_by_invoice,
    fetch_product,
    fetch_top_products,
    get_pool,
)
from app.models import OrderLineResponse, ProductResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_pool()


app = FastAPI(
    title="Retail Stream API",
    description="Data service for Online Retail dataset with Redis cache-aside.",
    lifespan=lifespan,
)


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/health")
async def health():
    return {"status": "ok"}

@app.get("/ready")
async def ready():
    errors = []
    try:
        pool = await get_pool()
        async with pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
    except Exception as e:
        errors.append(f"postgres: {e!s}")

    try:
        from app.cache import get_redis
        r = await get_redis()
        await r.ping()
        await r.aclose()
    except Exception as e:
        errors.append(f"redis: {e!s}")

    if errors:
        from fastapi.responses import JSONResponse
        return JSONResponse(status_code=503, content={"status": "not_ready", "errors": errors})
    return {"status": "ready"}


# ── Products (cache-aside) ────────────────────────────────────────────────────

@app.get("/products/{stock_code}", response_model=ProductResponse)
async def get_product(stock_code: str):
    """
    Get product by stock code. Uses Redis cache-aside:
    hit → Redis; miss → PostgreSQL → populate Redis → return.
    """
    stock_code = stock_code.strip()
    cached = await get_cached_product(stock_code)
    if cached is not None:
        return ProductResponse(**cached)

    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await fetch_product(conn, stock_code)
    if row is None:
        raise HTTPException(status_code=404, detail="Product not found")

    await set_cached_product(stock_code, row)
    return ProductResponse(**row)


@app.get("/products/top/{n}")
async def top_products(n: int = 10):
    """Top N products by total quantity sold."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await fetch_top_products(conn, limit=n)
    return rows


# ── Order lines ───────────────────────────────────────────────────────────────

@app.get("/orders/invoice/{invoice}", response_model=list[OrderLineResponse])
async def get_orders_by_invoice(invoice: str):
    """All order lines for a given invoice (e.g. 489434 or C489449)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await fetch_order_lines_by_invoice(conn, invoice)
    if not rows:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return rows


@app.get("/orders/customer/{customer_id}", response_model=list[OrderLineResponse])
async def get_orders_by_customer(
    customer_id: int,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Order lines for a customer (paginated)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await fetch_order_lines_by_customer(conn, customer_id, limit, offset)
    if not rows:
        raise HTTPException(status_code=404, detail="No orders for this customer")
    return rows


@app.get("/orders/country/{country}", response_model=list[OrderLineResponse])
async def get_orders_by_country(
    country: str,
    limit: int = Query(default=100, le=500),
    offset: int = Query(default=0, ge=0),
):
    """Order lines by country (paginated)."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await fetch_order_lines_by_country(conn, country, limit, offset)
    if not rows:
        raise HTTPException(status_code=404, detail="No orders for this country")
    return rows
