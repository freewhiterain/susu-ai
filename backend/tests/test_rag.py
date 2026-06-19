"""RAG Pipeline 测试 — 不依赖真实 Embedding API"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.services.rag import extract_text, chunk_text, RAGService


# ── 文档解析测试 ───────────────────────────────────────────

def test_parse_markdown():
    content = b"# \xe5\x91\x98\xe5\xb7\xa5\xe6\x89\x8b\xe5\x86\x8c\n\n\xe6\xaf\x8f\xe5\xb9\xb4\xe6\x9c\x8a\xe5\x81\x8710\xe5\xa4\xa9\xe5\xb9\xb4\xe5\x81\x87"
    text = extract_text(content, "员工手册.md")
    assert "员工手册" in text
    assert "年假" in text


def test_parse_txt():
    content = "这是纯文本内容。\n\n第二段落。".encode("utf-8")
    text = extract_text(content, "test.txt")
    assert "纯文本" in text
    assert "第二段落" in text


def test_parse_pdf():
    """验证 PDF 解析不崩溃（用最小 PDF 结构）。"""
    # 最小合法 PDF（只含一页空内容）
    minimal_pdf = (
        b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
        b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
        b"3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R>>endobj\n"
        b"xref\n0 4\n0000000000 65535 f\n"
        b"0000000009 00000 n\n0000000058 00000 n\n0000000115 00000 n\n"
        b"trailer<</Size 4/Root 1 0 R>>\nstartxref\n190\n%%EOF"
    )
    text = extract_text(minimal_pdf, "test.pdf")
    assert isinstance(text, str)


def test_parse_unknown_ext_as_text():
    content = "普通内容".encode("utf-8")
    text = extract_text(content, "file.csv")
    assert "普通内容" in text


# ── Chunking 测试 ──────────────────────────────────────────

def test_chunk_basic():
    text = "这是第一段。\n\n这是第二段。\n\n这是第三段。"
    chunks = chunk_text(text, "doc1", "test.md")
    assert len(chunks) >= 1
    assert all(c["doc_id"] == "doc1" for c in chunks)
    assert all(c["filename"] == "test.md" for c in chunks)


def test_chunk_ids_unique():
    text = "\n\n".join([f"第{i}段落内容，包含一些文字。" for i in range(50)])
    chunks = chunk_text(text, "doc1", "test.md")
    ids = [c["id"] for c in chunks]
    assert len(ids) == len(set(ids))


def test_chunk_overlap():
    """验证 chunk 之间有内容重叠（大文档才会触发）。"""
    # 构造一个足够大的文档（超过 500 token）
    long_para = "这是一个很长的段落，包含大量文字。" * 100
    chunks = chunk_text(long_para, "doc1", "big.txt")
    # 若有多个 chunk，相邻 chunk 应有重叠
    if len(chunks) > 1:
        end_of_first = chunks[0]["text"][-20:]
        start_of_second = chunks[1]["text"][:100]
        assert any(w in start_of_second for w in end_of_first.split() if len(w) > 1)


def test_chunk_index_sequential():
    text = "\n\n".join([f"段落{i}。" * 30 for i in range(20)])
    chunks = chunk_text(text, "doc1", "test.md")
    indexes = [c["chunk_index"] for c in chunks]
    assert indexes == list(range(len(chunks)))


# ── RAGService 测试（Mock Embedding + ChromaDB）────────────

@pytest.fixture
def rag(mock_embedding_client, monkeypatch):
    import app.services.llm.embedding as emb_module
    import chromadb

    monkeypatch.setattr(emb_module, "get_embedding_client", lambda: mock_embedding_client)

    mock_col = MagicMock()
    mock_col.count.return_value = 0
    mock_col.get.return_value = {"ids": []}
    mock_col.query.return_value = {
        "documents": [["年假 10 天"]],
        "metadatas": [[{"doc_id": "d1", "filename": "手册.md", "chunk_index": 0}]],
        "distances": [[0.1]],
    }
    mock_chroma = MagicMock()
    mock_chroma.get_or_create_collection.return_value = mock_col

    with patch("chromadb.PersistentClient", return_value=mock_chroma):
        service = RAGService()
        service._col = mock_col
        service._embedder = mock_embedding_client
        yield service


@pytest.mark.asyncio
async def test_index_document(rag):
    content = "员工每年享有 10 天年假。\n\n年假须在当年使用完毕。".encode("utf-8")
    count = await rag.index("doc1", "手册.md", content)
    assert count >= 1
    rag._col.add.assert_called()


@pytest.mark.asyncio
async def test_search_returns_results(rag):
    rag._col.count.return_value = 1
    results = await rag.search("年假几天")
    assert len(results) == 1
    assert results[0].filename == "手册.md"
    assert results[0].score >= 0


@pytest.mark.asyncio
async def test_search_empty_collection(rag):
    rag._col.count.return_value = 0
    results = await rag.search("年假几天")
    assert results == []


@pytest.mark.asyncio
async def test_delete_document(rag):
    rag._col.get.return_value = {"ids": ["doc1_0", "doc1_1"]}
    await rag.delete("doc1")
    rag._col.delete.assert_called_once_with(ids=["doc1_0", "doc1_1"])


@pytest.mark.asyncio
async def test_incremental_update(rag):
    """同名文档重新索引，应先删后增。"""
    rag._col.get.return_value = {"ids": ["old_0", "old_1"]}
    content = "新内容覆盖旧内容。".encode("utf-8")
    await rag.index("doc1", "手册.md", content)
    # 确认 delete 被调用（删除旧向量）
    rag._col.delete.assert_called()
    # 确认 add 被调用（写入新向量）
    rag._col.add.assert_called()
