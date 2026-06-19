from datetime import datetime, timezone
from enum import Enum
from sqlmodel import SQLModel, Field


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class IndexStatus(str, Enum):
    pending = "pending"
    indexed = "indexed"
    failed = "failed"


class Document(SQLModel, table=True):
    id: str = Field(primary_key=True)          # uuid
    filename: str
    file_type: str                              # md | pdf | docx | txt
    file_size: int = Field(default=0)
    status: IndexStatus = Field(default=IndexStatus.pending)
    chunk_count: int = Field(default=0)
    error_msg: str = Field(default="")
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class DocumentRead(SQLModel):
    id: str
    filename: str
    file_type: str
    file_size: int
    status: IndexStatus
    chunk_count: int
    error_msg: str
    created_at: datetime
    updated_at: datetime
