import os
import json
import structlog
from typing import Any, Optional

logger = structlog.get_logger(__name__)

_redis_client = None
_local_cache = {}

async def init_cache():
    global _redis_client
    if os.getenv("CACHE_BACKEND") == "redis":
        try:
            import aioredis
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            redis_password = os.getenv("REDIS_PASSWORD")
            
            if redis_password and "@" not in redis_url:
                redis_url = redis_url.replace("redis://", f"redis://:{redis_password}@")
                
            _redis_client = await aioredis.from_url(redis_url, decode_responses=True)
            await _redis_client.ping()
            logger.info("Redis cache initialized")
        except Exception as e:
            logger.warning("Redis unavailable, falling back to in-memory dict", error=str(e))
            _redis_client = None

async def get_cache(key: str) -> Optional[Any]:
    if _redis_client:
        try:
            val = await _redis_client.get(key)
            return json.loads(val) if val else None
        except Exception as e:
            logger.error("Redis get error", error=str(e), key=key)
            return None
    else:
        return _local_cache.get(key)

async def set_cache(key: str, value: Any, ttl: int = 86400):
    if _redis_client:
        try:
            await _redis_client.setex(key, ttl, json.dumps(value))
        except Exception as e:
            logger.error("Redis set error", error=str(e), key=key)
    else:
        _local_cache[key] = value

async def increment_metric(key: str, amount: float = 1.0):
    if _redis_client:
        try:
            if isinstance(amount, float) and amount != int(amount):
                await _redis_client.incrbyfloat(key, amount)
            else:
                await _redis_client.incrby(key, int(amount))
        except Exception as e:
            logger.error("Redis increment error", error=str(e), key=key)
    else:
        _local_cache[key] = _local_cache.get(key, 0) + amount

async def get_metric(key: str) -> float:
    if _redis_client:
        try:
            val = await _redis_client.get(key)
            return float(val) if val else 0.0
        except Exception as e:
            logger.error("Redis get metric error", error=str(e), key=key)
            return 0.0
    else:
        return float(_local_cache.get(key, 0.0))

async def close_cache():
    if _redis_client:
        await _redis_client.close()
