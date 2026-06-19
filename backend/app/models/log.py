from datetime import datetime
from typing import Optional
from sqlmodel import SQLModel, Field


class ConversationLog(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    session_id: str = Field(index=True)
    platform: str = Field(default="web")        # web | dingtalk | feishu
    user_id: str = Field(default="")
    user_msg: str
    assistant_msg: str
    tools_called: str = Field(default="")       # JSON 列表，工具名
    input_tokens: int = Field(default=0)
    output_tokens: int = Field(default=0)
    cost_usd: float = Field(default=0.0)
    latency_ms: int = Field(default=0)
    has_reference: bool = Field(default=False)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class ConversationLogRead(SQLModel):
    id: int
    session_id: str
    platform: str
    user_id: str
    user_msg: str
    assistant_msg: str
    tools_called: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: int
    has_reference: bool
    created_at: datetime
