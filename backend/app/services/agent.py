import json
import time
from typing import AsyncIterator
from loguru import logger
from app.core.config import get_settings
from app.services.llm.base import LLMUsage, ToolCall
from app.services.llm.openai_client import get_llm_client
from app.services.session import get_history, save_history
from app.tools.registry import TOOLS, MAX_TOOL_ROUNDS_DEFAULT
from app.tools.utils import dispatch
from app.models.chat import ChatResponse, ToolCallInfo
from app.core.observability import observe_conversation

SYSTEM_PROMPT = """你是「小苏」，公司内部 AI 助手。

规则：
1. 优先使用提供的工具查找准确信息，而不是凭记忆回答。
2. 回答必须附带引用来源（文件名和段落），格式：【来源：xxx】。
3. 若工具检索结果为空或相关度不足，明确告知「文档里没找到相关信息」，不要编造。
4. 保持上下文，记住对话中提及的人名、工号等关键信息。
5. 回答简洁、专业，使用中文。"""

MAX_TOOL_ROUNDS = MAX_TOOL_ROUNDS_DEFAULT  # 防止无限循环


def _cost(usage: LLMUsage) -> float:
    s = get_settings()
    return round(
        usage.input_tokens * s.input_price_per_m / 1_000_000
        + usage.output_tokens * s.output_price_per_m / 1_000_000,
        6,
    )


def _extract_references(messages: list[dict]) -> list[dict]:
    """从工具调用结果中提取 search_docs 的引用信息。"""
    refs = []
    for m in messages:
        if m.get("role") == "tool" and m.get("tool_name") == "search_docs":
            content = m.get("content", "")
            for block in content.split("---"):
                if "【来源：" in block:
                    refs.append({"snippet": block.strip()})
    return refs


def _append_tool_result(
    messages: list[dict], tc: ToolCall, result: str, tool_name: str
) -> None:
    messages.append({
        "role": "tool",
        "tool_call_id": tc.id,
        "tool_name": tool_name,
        "content": result,
    })


async def run(
    user_msg: str,
    session_id: str,
    platform: str = "web",
    user_id: str = "",
) -> ChatResponse:
    """非流式 Agent 主循环（IM 端使用）。"""
    t0 = time.monotonic()
    history = await get_history(session_id)
    history.append({"role": "user", "content": user_msg})

    llm = get_llm_client()
    total_usage = LLMUsage()
    tool_calls_log: list[ToolCallInfo] = []
    has_reference = False

    with observe_conversation(
        session_id=session_id, platform=platform, user_id=user_id, user_msg=user_msg
    ) as trace:
        try:
            for _ in range(MAX_TOOL_ROUNDS):
                messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
                resp = await llm.chat(messages, TOOLS)

                total_usage.input_tokens += resp.usage.input_tokens
                total_usage.output_tokens += resp.usage.output_tokens

                if not resp.tool_calls:
                    history.append({"role": "assistant", "content": resp.content})
                    break

                # 执行工具调用
                assistant_msg: dict = {
                    "role": "assistant",
                    "content": resp.content,
                    "tool_calls": [
                        {"id": tc.id, "type": "function",
                         "function": {"name": tc.name, "arguments": json.dumps(tc.input)}}
                        for tc in resp.tool_calls
                    ],
                }
                history.append(assistant_msg)

                for tc in resp.tool_calls:
                    logger.info(f"Tool call: {tc.name}({tc.input})")
                    result = await dispatch(tc.name, tc.input)
                    _append_tool_result(history, tc, result, tc.name)
                    tool_calls_log.append(ToolCallInfo(name=tc.name, input=tc.input, result=result[:500]))
                    if tc.name == "search_docs":
                        has_reference = True
            else:
                history.append({"role": "assistant", "content": "处理超时，请重新提问。"})

        except Exception as e:
            logger.error(f"Agent error: {e}")
            fallback = "抱歉，我暂时无法回答，请稍后重试。"
            history.append({"role": "assistant", "content": fallback})
            await save_history(session_id, history)
            trace.update(output=fallback, metadata={"error": str(e)})
            return ChatResponse(content=fallback, session_id=session_id)

        await save_history(session_id, history)
        final_content = history[-1].get("content", "")
        cost = _cost(total_usage)
        latency = int((time.monotonic() - t0) * 1000)

        trace.update(
            output=final_content,
            metadata={
                "tools": [t.name for t in tool_calls_log],
                "input_tokens": total_usage.input_tokens,
                "output_tokens": total_usage.output_tokens,
                "cost_usd": cost,
                "latency_ms": latency,
            },
        )
        trace.score_reference(has_reference)

        # 写对话日志
        await _log(session_id, platform, user_id, user_msg, final_content,
                   tool_calls_log, total_usage, cost, latency, has_reference)

        return ChatResponse(
            content=final_content,
            session_id=session_id,
            tool_calls=tool_calls_log,
            references=_extract_references(history),
            input_tokens=total_usage.input_tokens,
            output_tokens=total_usage.output_tokens,
            cost_usd=cost,
            latency_ms=latency,
        )


async def run_stream(
    user_msg: str, session_id: str
) -> AsyncIterator[str]:
    """流式 Agent：工具调用轮次非流式，最终回复流式推送。"""
    t0 = time.monotonic()
    history = await get_history(session_id)
    history.append({"role": "user", "content": user_msg})

    llm = get_llm_client()
    total_usage = LLMUsage()
    tool_calls_log: list[ToolCallInfo] = []
    has_reference = False

    def _sse(data: dict) -> str:
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    trace_cm = observe_conversation(
        session_id=session_id, platform="web", user_id="", user_msg=user_msg
    )
    trace = trace_cm.__enter__()
    try:
        # 单一流式循环：每一轮都流式生成；若该轮产生工具调用则执行后继续，
        # 否则即为最终回复（已逐字推送完毕）。避免「非流式生成一遍再流式重生成一遍」的浪费。
        full_content = ""
        for _ in range(MAX_TOOL_ROUNDS):
            messages = [{"role": "system", "content": SYSTEM_PROMPT}] + history
            turn_text = ""
            turn_tool_calls: list[ToolCall] = []

            async for chunk in llm.stream(messages, TOOLS):
                if chunk.delta:
                    turn_text += chunk.delta
                    yield _sse({"type": "text", "delta": chunk.delta})
                if chunk.usage.input_tokens:
                    total_usage.input_tokens += chunk.usage.input_tokens
                if chunk.usage.output_tokens:
                    total_usage.output_tokens += chunk.usage.output_tokens
                if chunk.tool_calls:
                    turn_tool_calls = chunk.tool_calls

            if not turn_tool_calls:
                full_content = turn_text
                history.append({"role": "assistant", "content": full_content})
                break

            # 该轮有工具调用：记录 assistant 轮次（含可能的前导文本）并执行工具
            history.append({
                "role": "assistant",
                "content": turn_text,
                "tool_calls": [
                    {"id": tc.id, "type": "function",
                     "function": {"name": tc.name, "arguments": json.dumps(tc.input)}}
                    for tc in turn_tool_calls
                ],
            })
            for tc in turn_tool_calls:
                yield _sse({"type": "tool_start", "name": tc.name, "input": tc.input})
                result = await dispatch(tc.name, tc.input)
                _append_tool_result(history, tc, result, tc.name)
                tool_calls_log.append(ToolCallInfo(name=tc.name, input=tc.input, result=result[:500]))
                if tc.name == "search_docs":
                    has_reference = True
                yield _sse({"type": "tool_result", "name": tc.name, "result": result[:300]})
        else:
            # 达到最大轮次仍未收敛
            full_content = turn_text or "处理超时，请重新提问。"
            history.append({"role": "assistant", "content": full_content})

        await save_history(session_id, history)

        cost = _cost(total_usage)
        latency = int((time.monotonic() - t0) * 1000)
        refs = _extract_references(history)

        yield _sse({"type": "references", "data": refs})
        yield _sse({"type": "done", "session_id": session_id,
                    "input_tokens": total_usage.input_tokens,
                    "output_tokens": total_usage.output_tokens,
                    "cost_usd": cost, "latency_ms": latency})

        trace.update(
            output=full_content,
            metadata={
                "tools": [t.name for t in tool_calls_log],
                "input_tokens": total_usage.input_tokens,
                "output_tokens": total_usage.output_tokens,
                "cost_usd": cost,
                "latency_ms": latency,
            },
        )
        trace.score_reference(has_reference)

        await _log(session_id, "web", "", user_msg, full_content,
                   tool_calls_log, total_usage, cost, latency, has_reference)

    except Exception as e:
        logger.error(f"Stream agent error: {e}")
        trace.update(metadata={"error": str(e)})
        yield _sse({"type": "error", "message": "服务暂时不可用，请稍后重试"})
    finally:
        trace_cm.__exit__(None, None, None)


async def _log(
    session_id: str, platform: str, user_id: str,
    user_msg: str, assistant_msg: str,
    tool_calls: list[ToolCallInfo], usage: LLMUsage,
    cost: float, latency: int, has_reference: bool,
) -> None:
    try:
        from app.db.database import get_engine
        from app.models.log import ConversationLog
        from sqlmodel import Session
        log = ConversationLog(
            session_id=session_id,
            platform=platform,
            user_id=user_id,
            user_msg=user_msg,
            assistant_msg=assistant_msg,
            tools_called=json.dumps([t.name for t in tool_calls], ensure_ascii=False),
            input_tokens=usage.input_tokens,
            output_tokens=usage.output_tokens,
            cost_usd=cost,
            latency_ms=latency,
            has_reference=has_reference,
        )
        with Session(get_engine()) as s:
            s.add(log)
            s.commit()
    except Exception as e:
        logger.error(f"Log write failed: {e}")
