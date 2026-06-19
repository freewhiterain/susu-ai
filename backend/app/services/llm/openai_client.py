import json
from typing import AsyncIterator
from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception
from app.core.config import get_settings
from app.services.llm.base import (
    LLMClient, LLMResponse, LLMChunk, LLMUsage, ToolCall, ToolDefinition
)


def _to_openai_tools(tools: list[ToolDefinition]) -> list[dict]:
    return [
        {"type": "function", "function": {
            "name": t.name,
            "description": t.description,
            "parameters": t.parameters,
        }}
        for t in tools
    ]


class OpenAIClient(LLMClient):
    def __init__(self):
        s = get_settings()
        self._client = AsyncOpenAI(
            api_key=s.openai_api_key,
            base_url=s.openai_base_url,
        )
        self._model = s.openai_model

    @retry(
        retry=retry_if_exception(lambda e: getattr(e, "status_code", 0) in {429, 503}),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(3),
        reraise=True,
    )
    async def chat(
        self, messages: list[dict], tools: list[ToolDefinition] | None = None
    ) -> LLMResponse:
        kwargs: dict = {"model": self._model, "messages": messages}
        if tools:
            kwargs["tools"] = _to_openai_tools(tools)
            kwargs["tool_choice"] = "auto"

        resp = await self._client.chat.completions.create(**kwargs)
        choice = resp.choices[0]
        msg = choice.message
        content = msg.content or ""
        tool_calls: list[ToolCall] = []

        if msg.tool_calls:
            for tc in msg.tool_calls:
                tool_calls.append(ToolCall(
                    id=tc.id,
                    name=tc.function.name,
                    input=json.loads(tc.function.arguments or "{}"),
                ))

        return LLMResponse(
            content=content,
            tool_calls=tool_calls,
            usage=LLMUsage(
                input_tokens=resp.usage.prompt_tokens if resp.usage else 0,
                output_tokens=resp.usage.completion_tokens if resp.usage else 0,
            ),
            stop_reason="tool_use" if tool_calls else "end_turn",
        )

    async def stream(
        self, messages: list[dict], tools: list[ToolDefinition] | None = None
    ) -> AsyncIterator[LLMChunk]:
        kwargs: dict = {"model": self._model, "messages": messages, "stream": True}
        if tools:
            kwargs["tools"] = _to_openai_tools(tools)
            kwargs["tool_choice"] = "auto"
            # 需要在流式结束时拿到 usage
            kwargs["stream_options"] = {"include_usage": True}

        input_tokens = 0
        output_tokens = 0
        # tool_call 的 delta 是分片到达的，按 index 累积
        tool_acc: dict[int, dict] = {}

        async for chunk in await self._client.chat.completions.create(**kwargs):
            if chunk.usage:
                input_tokens = chunk.usage.prompt_tokens
                output_tokens = chunk.usage.completion_tokens
            choice = chunk.choices[0] if chunk.choices else None
            if not choice:
                continue
            delta = choice.delta
            if delta.content:
                yield LLMChunk(delta=delta.content)
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    acc = tool_acc.setdefault(tc.index, {"id": "", "name": "", "args": ""})
                    if tc.id:
                        acc["id"] = tc.id
                    if tc.function and tc.function.name:
                        acc["name"] = tc.function.name
                    if tc.function and tc.function.arguments:
                        acc["args"] += tc.function.arguments

        tool_calls = [
            ToolCall(
                id=acc["id"],
                name=acc["name"],
                input=json.loads(acc["args"] or "{}"),
            )
            for _, acc in sorted(tool_acc.items())
        ]
        yield LLMChunk(
            tool_calls=tool_calls,
            usage=LLMUsage(input_tokens=input_tokens, output_tokens=output_tokens),
            stop_reason="tool_use" if tool_calls else "end_turn",
        )


from functools import lru_cache

@lru_cache
def get_llm_client() -> LLMClient:
    provider = get_settings().llm_provider
    if provider == "claude":
        # 延迟导入，避免在仅用 openai 时强制加载 anthropic SDK
        from app.services.llm.claude import ClaudeClient
        return ClaudeClient()
    return OpenAIClient()
