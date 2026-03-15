"""
Retail Stream API — Backend with Redis cache-aside + Kafka async orders.

GET /products/{stock_code}  → Redis cache-aside → PostgreSQL
POST /orders                → Kafka (async) → Consumer → PostgreSQL
"""
from contextlib import asynccontextmanager
from datetime import datetime

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
from app.kafka_producer import close_producer, publish_order
from app.models import (
    OrderAcceptedResponse,
    OrderCreateRequest,
    OrderLineResponse,
    ProductResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    yield
    await close_producer()
    await close_pool()


app = FastAPI(
    title="Retail Stream API",
    description="Scalable data service: Nginx LB → N × FastAPI → Redis cache + Kafka async orders → PostgreSQL.",
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

@app.get("/products/top/{n}")
async def top_products(n: int = 10):
    """Top N products by total quantity sold."""
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await fetch_top_products(conn, limit=n)
    return rows


@app.get("/products/{stock_code}", response_model=ProductResponse)
async def get_product(stock_code: str):
    """Cache-aside: Redis hit → return; miss → PostgreSQL → populate Redis → return."""
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


# ── Orders (POST via Kafka) ──────────────────────────────────────────────────

@app.post("/orders", response_model=OrderAcceptedResponse, status_code=202)
async def create_order(order: OrderCreateRequest):
    """
    Publish order to Kafka → return 202 immediately.
    The Kafka consumer processes it in the background (INSERT into PostgreSQL).
    """
    event = {
        "invoice": order.invoice,
        "stock_code": order.stock_code,
        "description": order.description,
        "quantity": order.quantity,
        "invoice_date": datetime.utcnow().isoformat(),
        "price": order.price,
        "customer_id": order.customer_id,
        "country": order.country,
        "year": None,
    }
    await publish_order(event)
    return OrderAcceptedResponse(invoice=order.invoice)


# ── Order lines (GET) ────────────────────────────────────────────────────────

@app.get("/orders/invoice/{invoice}", response_model=list[OrderLineResponse])
async def get_orders_by_invoice(invoice: str):
    """All order lines for a given invoice."""
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
