import json
import uuid
from loguru import logger

_redis = None


def _get_redis():
    global _redis
    if _redis is None:
        import redis.asyncio as aioredis
        from app.core.config import get_settings
        _redis = aioredis.from_url(get_settings().redis_url, decode_responses=True)
    return _redis


def new_session_id() -> str:
    return str(uuid.uuid4())


def _key(session_id: str) -> str:
    return f"session:{session_id}"


async def get_history(session_id: str) -> list[dict]:
    try:
        r = _get_redis()
        raw = await r.get(_key(session_id))
        return json.loads(raw) if raw else []
    except Exception as e:
        logger.warning(f"Redis get failed: {e}，使用空历史")
        return []


async def save_history(session_id: str, messages: list[dict]) -> None:
    from app.core.config import get_settings
    try:
        r = _get_redis()
        ttl = get_settings().redis_session_ttl
        await r.setex(_key(session_id), ttl, json.dumps(messages, ensure_ascii=False))
    except Exception as e:
        logger.warning(f"Redis save failed: {e}")


async def clear_session(session_id: str) -> None:
    try:
        await _get_redis().delete(_key(session_id))
    except Exception as e:
        logger.warning(f"Redis clear failed: {e}")
