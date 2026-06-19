from abc import ABC, abstractmethod
from typing import Any, AsyncIterator
from pydantic import BaseModel


class ToolDefinition(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any]   # JSON Schema object


class ToolCall(BaseModel):
    id: str
    name: str
    input: dict[str, Any]


class LLMUsage(BaseModel):
    input_tokens: int = 0
    output_tokens: int = 0


class LLMResponse(BaseModel):
    content: str
    tool_calls: list[ToolCall] = []
    usage: LLMUsage = LLMUsage()
    stop_reason: str = "end_turn"  # end_turn | tool_use


class LLMChunk(BaseModel):
    delta: str = ""
    tool_calls: list[ToolCall] = []
    usage: LLMUsage = LLMUsage()
    stop_reason: str = ""


class LLMClient(ABC):
    @abstractmethod
    async def chat(
        self,
        messages: list[dict],
        tools: list[ToolDefinition] | None = None,
    ) -> LLMResponse: ...

    @abstractmethod
    async def stream(
        self,
        messages: list[dict],
        tools: list[ToolDefinition] | None = None,
    ) -> AsyncIterator[LLMChunk]: ...


class EmbeddingClient(ABC):
    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...

    @abstractmethod
    async def embed_batch(self, texts: list[str]) -> list[list[float]]: ...
