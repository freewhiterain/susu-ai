from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func
from loguru import logger
from app.core.config import get_settings
from app.db.database import get_session
from app.models.document import Document
from app.tools.registry import MAX_TOOL_ROUNDS_DEFAULT

router = APIRouter(prefix="/api/settings", tags=["settings"])


def _redis_connected() -> bool:
    """同步探测 Redis 可用性（设置页只读展示，容忍短超时）。"""
    try:
        import redis
        s = get_settings()
        client = redis.from_url(s.redis_url, socket_connect_timeout=1)
        client.ping()
        return True
    except Exception:
        return False


def _vector_count() -> int:
    try:
        from app.services.rag import get_rag
        return get_rag()._col.count()
    except Exception as e:
        logger.warning(f"vector_count failed: {e}")
        return 0


@router.get("")
def read_settings(session: Session = Depends(get_session)):
    """返回当前运行配置（只读）。敏感字段（API Key）一律不下发。"""
    s = get_settings()

    if s.llm_provider == "claude":
        llm_model = s.anthropic_model
    else:
        llm_model = s.openai_model

    if s.embedding_provider == "voyage":
        embedding_model = s.voyage_embedding_model
    elif s.embedding_provider == "local":
        embedding_model = s.local_embedding_model
    else:
        embedding_model = s.openai_embedding_model

    doc_count = session.exec(select(func.count()).select_from(Document)).one()

    return {
        "llm_provider": s.llm_provider,
        "llm_model": llm_model,
        "embedding_provider": s.embedding_provider,
        "embedding_model": embedding_model,
        "input_price_per_m": s.input_price_per_m,
        "output_price_per_m": s.output_price_per_m,
        "max_tool_rounds": MAX_TOOL_ROUNDS_DEFAULT,
        "langfuse_enabled": s.langfuse_enabled,
        "redis_connected": _redis_connected(),
        "document_count": doc_count,
        "vector_count": _vector_count(),
    }
