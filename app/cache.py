"""Redis cache-aside for product reads (GET /products/{stock_code})."""
import orjson

import redis.asyncio as redis

from app.config import settings

_CACHE_KEY_PREFIX = "product:"
_pool: redis.ConnectionPool | None = None


def _get_pool() -> redis.ConnectionPool:
    global _pool
    if _pool is None:
        _pool = redis.ConnectionPool.from_url(
            settings.redis_url,
            encoding="utf-8",
            decode_responses=True,
            max_connections=50,
        )
    return _pool


async def get_redis() -> redis.Redis:
    """Return a Redis client backed by a shared connection pool."""
    return redis.Redis(connection_pool=_get_pool())


async def close_redis() -> None:
    global _pool
    if _pool is not None:
        await _pool.aclose()
        _pool = None


def _cache_key(stock_code: str) -> str:
    return f"{_CACHE_KEY_PREFIX}{stock_code}"


async def get_cached_product(stock_code: str) -> dict | None:
    r = await get_redis()
    data = await r.get(_cache_key(stock_code.strip()))
    if data is None:
        return None
    return orjson.loads(data)


async def set_cached_product(stock_code: str, product: dict) -> None:
    r = await get_redis()
    await r.set(
        _cache_key(stock_code.strip()),
        orjson.dumps(product),
        ex=settings.cache_ttl_seconds,
    )
