import redis.asyncio as aioredis
from app.core.config import settings
import json
from typing import Any

_redis_pool: aioredis.Redis | None = None


async def get_redis() -> aioredis.Redis:
    global _redis_pool
    if _redis_pool is None:
        _redis_pool = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            max_connections=20,
        )
    return _redis_pool


async def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> None:
    r = await get_redis()
    await r.setex(key, ttl_seconds, json.dumps(value))


async def cache_get(key: str) -> Any | None:
    r = await get_redis()
    data = await r.get(key)
    return json.loads(data) if data else None


async def cache_delete(key: str) -> None:
    r = await get_redis()
    await r.delete(key)
