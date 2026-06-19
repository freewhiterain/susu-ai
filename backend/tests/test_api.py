"""API 端点测试 — 使用 FastAPI TestClient，不依赖真实 LLM"""
import pytest
from unittest.mock import AsyncMock, patch


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


# ── 文档上传 ───────────────────────────────────────────────

def test_upload_markdown(client):
    with patch("app.api.documents._index_document", new=AsyncMock()):
        resp = client.post(
            "/api/documents",
            files={"file": ("员工手册.md", b"# \xe5\x91\x98\xe5\xb7\xa5\xe6\x89\x8b\xe5\x86\x8c\n\n\xe5\xb9\xb4\xe5\x81\x8510\xe5\xa4\xa9", "text/markdown")},
        )
    assert resp.status_code == 201
    data = resp.json()
    assert data["filename"] == "员工手册.md"
    assert data["status"] == "pending"
    assert data["file_type"] == "md"


def test_upload_unsupported_type(client):
    resp = client.post(
        "/api/documents",
        files={"file": ("data.xlsx", b"content", "application/octet-stream")},
    )
    assert resp.status_code == 400


def test_upload_empty_file(client):
    resp = client.post(
        "/api/documents",
        files={"file": ("empty.md", b"", "text/markdown")},
    )
    assert resp.status_code == 400


# ── 文档列表 ───────────────────────────────────────────────

def test_list_documents_empty(client):
    resp = client.get("/api/documents")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_documents_after_upload(client):
    with patch("app.api.documents._index_document", new=AsyncMock()):
        client.post(
            "/api/documents",
            files={"file": ("test.md", b"content", "text/markdown")},
        )
    resp = client.get("/api/documents")
    assert resp.status_code == 200
    assert len(resp.json()) == 1


# ── 文档删除 ───────────────────────────────────────────────

def test_delete_document(client):
    with patch("app.api.documents._index_document", new=AsyncMock()):
        up = client.post(
            "/api/documents",
            files={"file": ("del.md", b"content", "text/markdown")},
        )
    doc_id = up.json()["id"]

    with patch("app.services.rag.RAGService.delete", new=AsyncMock()):
        resp = client.delete(f"/api/documents/{doc_id}")
    assert resp.status_code == 204

    # 再次列表确认已删除
    lst = client.get("/api/documents")
    assert all(d["id"] != doc_id for d in lst.json())


def test_delete_nonexistent(client):
    with patch("app.services.rag.RAGService.delete", new=AsyncMock()):
        resp = client.delete("/api/documents/nonexistent-id")
    assert resp.status_code == 404


# ── 增量更新（同名文件）─────────────────────────────────────

def test_incremental_update_same_filename(client):
    with patch("app.api.documents._index_document", new=AsyncMock()):
        r1 = client.post(
            "/api/documents",
            files={"file": ("手册.md", b"v1 content", "text/markdown")},
        )
        r2 = client.post(
            "/api/documents",
            files={"file": ("手册.md", b"v2 content updated", "text/markdown")},
        )
    assert r1.status_code == 201
    assert r2.status_code == 201
    # 同名文件应复用同一个 id
    assert r1.json()["id"] == r2.json()["id"]
    # 列表里只有一条记录
    lst = client.get("/api/documents")
    assert len(lst.json()) == 1
