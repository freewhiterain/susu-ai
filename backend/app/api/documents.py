import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, UploadFile, File, HTTPException, BackgroundTasks, Depends
from sqlmodel import Session, select
from loguru import logger
from app.db.database import get_session
from app.models.document import Document, DocumentRead, IndexStatus
from app.services.rag import get_rag

router = APIRouter(prefix="/api/documents", tags=["documents"])

ALLOWED_TYPES = {".md", ".pdf", ".docx", ".txt"}
MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB


async def _index_document(doc_id: str, filename: str, content: bytes) -> None:
    """后台任务：解析文档并写入向量库，更新状态。"""
    from app.db.database import get_engine
    from sqlmodel import Session

    rag = get_rag()
    with Session(get_engine()) as session:
        doc = session.get(Document, doc_id)
        if not doc:
            return
        try:
            chunk_count = await rag.index(doc_id, filename, content)
            doc.status = IndexStatus.indexed
            doc.chunk_count = chunk_count
            doc.error_msg = ""
        except Exception as e:
            logger.error(f"Index failed for {filename}: {e}")
            doc.status = IndexStatus.failed
            doc.error_msg = str(e)[:500]
        doc.updated_at = datetime.now(timezone.utc)
        session.add(doc)
        session.commit()


@router.post("", status_code=201, response_model=DocumentRead)
async def upload_document(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: Session = Depends(get_session),
):
    from pathlib import Path
    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_TYPES:
        raise HTTPException(400, f"不支持的文件类型 {ext}，支持：{ALLOWED_TYPES}")

    content = await file.read()
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(400, "文件超过 20MB 限制")
    if not content:
        raise HTTPException(400, "文件内容为空")

    filename = file.filename or "unknown"

    # 增量更新：同名文件找到旧记录，复用 id（会触发 delete 旧向量）
    existing = session.exec(
        select(Document).where(Document.filename == filename)
    ).first()

    doc_id = existing.id if existing else str(uuid.uuid4())
    now = datetime.now(timezone.utc)

    doc = Document(
        id=doc_id,
        filename=filename,
        file_type=ext.lstrip("."),
        file_size=len(content),
        status=IndexStatus.pending,
        chunk_count=0,
        error_msg="",
        created_at=existing.created_at if existing else now,
        updated_at=now,
    )
    # merge 返回受 session 管理的持久化实例；必须使用返回值，
    # 否则对原 detached 实例 refresh 会抛 "not persistent within this Session"。
    doc = session.merge(doc)
    session.commit()
    session.refresh(doc)

    background_tasks.add_task(_index_document, doc_id, filename, content)
    return doc


@router.get("", response_model=list[DocumentRead])
def list_documents(session: Session = Depends(get_session)):
    return session.exec(select(Document).order_by(Document.updated_at.desc())).all()


@router.get("/{doc_id}", response_model=DocumentRead)
def get_document(doc_id: str, session: Session = Depends(get_session)):
    doc = session.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "文档不存在")
    return doc


@router.delete("/{doc_id}", status_code=204)
async def delete_document(doc_id: str, session: Session = Depends(get_session)):
    doc = session.get(Document, doc_id)
    if not doc:
        raise HTTPException(404, "文档不存在")
    await get_rag().delete(doc_id)
    session.delete(doc)
    session.commit()
