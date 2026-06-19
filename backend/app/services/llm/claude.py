import json
from typing import AsyncIterator
from anthropic import AsyncAnthropic
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from loguru import logger
from app.core.config import get_settings
from app.services.llm.base import (
    LLMClient, LLMResponse, LLMChunk, LLMUsage, ToolCall, ToolDefinition
)


def _to_claude_tools(tools: list[ToolDefinition]) -> list[dict]:
    return [
        {"name": t.name, "description": t.description, "input_schema": t.parameters}
        for t in tools
    ]


def _to_claude_messages(messages: list[dict]) -> list[dict]:
    """OpenAI 格式 → Claude 格式，合并相邻同 role 消息。"""
    result: list[dict] = []
    for m in messages:
        role = m["role"]
        if role == "tool":
            # tool result → Claude user message with tool_result block
            block = {
                "type": "tool_result",
                "tool_use_id": m.get("tool_call_id", ""),
                "content": str(m["content"]),
            }
            if result and result[-1]["role"] == "user" and isinstance(result[-1]["content"], list):
                result[-1]["content"].append(block)
            else:
                result.append({"role": "user", "content": [block]})
        elif role == "assistant" and m.get("tool_calls"):
            blocks = []
            if m.get("content"):
                blocks.append({"type": "text", "text": m["content"]})
            for tc in m["tool_calls"]:
                fn = tc.get("function", tc)
                args = fn.get("arguments", "{}")
                inp = json.loads(args) if isinstance(args, str) else args
                blocks.append({
                    "type": "tool_use",
                    "id": tc.get("id", ""),
                    "name": fn.get("name", ""),
                    "input": inp,
                })
            result.append({"role": "assistant", "content": blocks})
        else:
            result.append({"role": role, "content": m.get("content", "")})
    return result


class ClaudeClient(LLMClient):
    def __init__(self):
        s = get_settings()
        self._client = AsyncAnthropic(
            api_key=s.anthropic_api_key,
            base_url=s.anthropic_base_url,
        )
        self._model = s.anthropic_model
        self._settings = s

    @retry(
        retry=retry_if_exception(lambda e: getattr(e, "status_code", 0) in {429, 503}),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def chat(
        self, messages: list[dict], tools: list[ToolDefinition] | None = None
    ) -> LLMResponse:
        kwargs: dict = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": _to_claude_messages(messages),
        }
        if tools:
            kwargs["tools"] = _to_claude_tools(tools)

        resp = await self._client.messages.create(**kwargs)
        content_text = ""
        tool_calls: list[ToolCall] = []

        for block in resp.content:
            if block.type == "text":
                content_text += block.text
            elif block.type == "tool_use":
                tool_calls.append(ToolCall(id=block.id, name=block.name, input=block.input))

        return LLMResponse(
            content=content_text,
            tool_calls=tool_calls,
            usage=LLMUsage(
                input_tokens=resp.usage.input_tokens,
                output_tokens=resp.usage.output_tokens,
            ),
            stop_reason="tool_use" if tool_calls else "end_turn",
        )

    async def stream(
        self, messages: list[dict], tools: list[ToolDefinition] | None = None
    ) -> AsyncIterator[LLMChunk]:
        kwargs: dict = {
            "model": self._model,
            "max_tokens": 4096,
            "messages": _to_claude_messages(messages),
        }
        if tools:
            kwargs["tools"] = _to_claude_tools(tools)

        async with self._client.messages.stream(**kwargs) as s:
            async for text in s.text_stream:
                yield LLMChunk(delta=text)
            final = await s.get_final_message()
            yield LLMChunk(
                usage=LLMUsage(
                    input_tokens=final.usage.input_tokens,
                    output_tokens=final.usage.output_tokens,
                ),
                stop_reason=final.stop_reason or "end_turn",
            )
