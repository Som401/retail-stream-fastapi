"""Redis cache-aside for product reads (GET /products/{stock_code})."""
import json
import redis.asyncio as redis
from app.config import settings

_CACHE_KEY_PREFIX = "product:"


async def get_redis() -> redis.Redis:
    """Return a Redis connection (new each time for simplicity; can use pool later)."""
    return redis.from_url(
        settings.redis_url,
        encoding="utf-8",
        decode_responses=True,
    )


def _cache_key(stock_code: str) -> str:
    return f"{_CACHE_KEY_PREFIX}{stock_code}"


async def get_cached_product(stock_code: str) -> dict | None:
    """
    Cache-aside: get product from Redis. Returns None on miss or error.
    """
    r = await get_redis()
    try:
        key = _cache_key(stock_code.strip())
        data = await r.get(key)
        if data is None:
            return None
        return json.loads(data)
    finally:
        await r.aclose()


async def set_cached_product(stock_code: str, product: dict) -> None:
    """Store product in Redis with TTL."""
    r = await get_redis()
    try:
        key = _cache_key(stock_code.strip())
        await r.set(
            key,
            json.dumps(product),
            ex=settings.cache_ttl_seconds,
        )
    finally:
        await r.aclose()
