import os
import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session
from sqlmodel.pool import StaticPool

# 关键：在调用 SQLModel.metadata.create_all 之前导入全部 table 模型，
# 否则 metadata 里没有这些表 → 测试报 "no such table"。
import app.models.document  # noqa: F401,E402
import app.models.log  # noqa: F401,E402


# 测试环境变量（不依赖真实 API）
os.environ.setdefault("OPENAI_API_KEY", "sk-test-fake")
os.environ.setdefault("OPENAI_BASE_URL", "https://api.openai.com/v1")
os.environ.setdefault("LLM_PROVIDER", "openai")
os.environ.setdefault("EMBEDDING_PROVIDER", "openai")
os.environ.setdefault("MOCK_API_BASE_URL", "http://localhost:8001")
os.environ.setdefault("DATABASE_URL", "sqlite://")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("CHROMA_PERSIST_PATH", "/tmp/test_chroma")


@pytest.fixture
def mock_embedding_client():
    """返回固定向量的 Mock Embedding 客户端。"""
    client = AsyncMock()
    client.embed.return_value = [0.1] * 1536
    client.embed_batch.return_value = [[0.1] * 1536]
    return client


@pytest.fixture
def mock_llm_client():
    """返回预设回复的 Mock LLM 客户端。"""
    from app.services.llm.base import LLMResponse, LLMUsage
    client = AsyncMock()
    client.chat.return_value = LLMResponse(
        content="这是测试回复",
        tool_calls=[],
        usage=LLMUsage(input_tokens=10, output_tokens=20),
        stop_reason="end_turn",
    )
    return client


@pytest.fixture
def test_session():
    """内存 SQLite，每个测试独立。"""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(test_session, mock_embedding_client, monkeypatch):
    """FastAPI TestClient，注入 Mock 依赖。"""
    import app.services.rag as rag_module
    import app.services.llm.embedding as emb_module

    monkeypatch.setattr(emb_module, "get_embedding_client", lambda: mock_embedding_client)

    # Mock ChromaDB
    mock_col = MagicMock()
    mock_col.count.return_value = 0
    mock_col.get.return_value = {"ids": []}
    mock_col.query.return_value = {
        "documents": [[]], "metadatas": [[]], "distances": [[]]
    }
    mock_chroma = MagicMock()
    mock_chroma.get_or_create_collection.return_value = mock_col
    monkeypatch.setattr("chromadb.PersistentClient", lambda **kw: mock_chroma)

    from app.main import app
    from app.db.database import get_session
    app.dependency_overrides[get_session] = lambda: test_session
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()
