from typing import Any
from pydantic import BaseModel


class ChatMessage(BaseModel):
    role: str           # user | assistant | tool
    content: str


class ChatRequest(BaseModel):
    message: str
    session_id: str = ""
    stream: bool = True


class ToolCallInfo(BaseModel):
    name: str
    input: dict[str, Any]
    result: str


class ChatResponse(BaseModel):
    content: str
    session_id: str
    tool_calls: list[ToolCallInfo] = []
    references: list[dict[str, Any]] = []
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: int = 0
