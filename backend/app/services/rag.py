import io
import uuid
from pathlib import Path
from dataclasses import dataclass
from loguru import logger
import tiktoken
import chromadb
from app.core.config import get_settings
from app.services.llm.embedding import get_embedding_client

COLLECTION = "documents"
CHUNK_SIZE = 500    # tokens
CHUNK_OVERLAP = 50  # tokens
TOP_K = 5


@dataclass
class SearchResult:
    doc_id: str
    filename: str
    chunk_index: int
    text: str
    score: float


# ── 文本提取 ──────────────────────────────────────────────

def extract_text(content: bytes, filename: str) -> str:
    ext = Path(filename).suffix.lower()
    if ext in (".md", ".txt"):
        return content.decode("utf-8", errors="ignore")
    if ext == ".pdf":
        return _extract_pdf(content)
    if ext == ".docx":
        return _extract_docx(content)
    return content.decode("utf-8", errors="ignore")


def _extract_pdf(content: bytes) -> str:
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(content))
    pages = [p.extract_text() or "" for p in reader.pages]
    return "\n\n".join(p for p in pages if p.strip())


def _extract_docx(content: bytes) -> str:
    from docx import Document
    doc = Document(io.BytesIO(content))
    paras = [p.text for p in doc.paragraphs if p.text.strip()]
    return "\n\n".join(paras)


# ── Chunking ──────────────────────────────────────────────

def chunk_text(text: str, doc_id: str, filename: str) -> list[dict]:
    enc = tiktoken.get_encoding("cl100k_base")
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

    chunks: list[dict] = []
    current_tokens: list[int] = []
    idx = 0

    def flush():
        nonlocal idx, current_tokens
        if not current_tokens:
            return
        chunk_text = enc.decode(current_tokens)
        chunks.append({
            "id": f"{doc_id}_{idx}",
            "doc_id": doc_id,
            "filename": filename,
            "chunk_index": idx,
            "text": chunk_text,
        })
        idx += 1
        # 保留末尾 CHUNK_OVERLAP 个 token 作为下一 chunk 的开头
        current_tokens = current_tokens[-CHUNK_OVERLAP:]

    for para in paragraphs:
        para_tokens = enc.encode(para)
        # 单段落超过 CHUNK_SIZE，先 flush 再按 token 强制分割
        if len(para_tokens) > CHUNK_SIZE:
            flush()
            for i in range(0, len(para_tokens), CHUNK_SIZE - CHUNK_OVERLAP):
                current_tokens = para_tokens[i: i + CHUNK_SIZE]
                flush()
        else:
            if len(current_tokens) + len(para_tokens) > CHUNK_SIZE:
                flush()
            current_tokens.extend(para_tokens)

    flush()
    return chunks


# ── RAGService ────────────────────────────────────────────

class RAGService:
    def __init__(self):
        s = get_settings()
        Path(s.chroma_persist_path).mkdir(parents=True, exist_ok=True)
        self._chroma = chromadb.PersistentClient(path=s.chroma_persist_path)
        self._col = self._chroma.get_or_create_collection(
            COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )
        self._embedder = get_embedding_client()

    # 索引文档，返回 chunk 数量
    async def index(self, doc_id: str, filename: str, content: bytes) -> int:
        # 删除旧版本（增量更新）
        await self.delete(doc_id)

        text = extract_text(content, filename)
        if not text.strip():
            raise ValueError("文档内容为空，无法索引")

        chunks = chunk_text(text, doc_id, filename)
        if not chunks:
            raise ValueError("文档分块失败")

        # 批量 Embedding（最多 100 条/批）
        batch_size = 100
        for i in range(0, len(chunks), batch_size):
            batch = chunks[i: i + batch_size]
            texts = [c["text"] for c in batch]
            embeddings = await self._embedder.embed_batch(texts)
            self._col.add(
                ids=[c["id"] for c in batch],
                embeddings=embeddings,
                documents=texts,
                metadatas=[{
                    "doc_id": c["doc_id"],
                    "filename": c["filename"],
                    "chunk_index": c["chunk_index"],
                } for c in batch],
            )

        logger.info(f"Indexed {len(chunks)} chunks for doc={doc_id} ({filename})")
        return len(chunks)

    # 取出某文档的全部 chunk（按 chunk_index 升序），供前端「来源跳转/高亮」查看原文
    def get_chunks(self, doc_id: str) -> list[dict]:
        res = self._col.get(where={"doc_id": doc_id}, include=["documents", "metadatas"])
        items = [
            {"chunk_index": int(meta["chunk_index"]), "text": text}
            for text, meta in zip(res["documents"], res["metadatas"])
        ]
        items.sort(key=lambda x: x["chunk_index"])
        return items

    # 删除文档所有 chunk
    async def delete(self, doc_id: str) -> None:
        existing = self._col.get(where={"doc_id": doc_id})
        if existing["ids"]:
            self._col.delete(ids=existing["ids"])
            logger.info(f"Deleted {len(existing['ids'])} chunks for doc={doc_id}")

    # 语义检索，返回带来源的结果列表
    async def search(self, query: str, n: int = TOP_K) -> list[SearchResult]:
        if self._col.count() == 0:
            return []

        embedding = await self._embedder.embed(query)
        results = self._col.query(
            query_embeddings=[embedding],
            n_results=min(n, self._col.count()),
            include=["documents", "metadatas", "distances"],
        )

        hits: list[SearchResult] = []
        for text, meta, dist in zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        ):
            hits.append(SearchResult(
                doc_id=meta["doc_id"],
                filename=meta["filename"],
                chunk_index=meta["chunk_index"],
                text=text,
                score=round(1 - dist, 4),  # cosine distance → similarity
            ))
        return hits


_rag: RAGService | None = None


def get_rag() -> RAGService:
    global _rag
    if _rag is None:
        _rag = RAGService()
    return _rag
