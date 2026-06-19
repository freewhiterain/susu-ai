"""Agent 工具调度测试 — Mock LLM，不调用真实 API"""
import json
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from app.services.llm.base import LLMResponse, LLMUsage, ToolCall
from app.models.chat import ChatResponse


def _make_llm_response(content="", tool_calls=None):
    return LLMResponse(
        content=content,
        tool_calls=tool_calls or [],
        usage=LLMUsage(input_tokens=10, output_tokens=20),
        stop_reason="tool_use" if tool_calls else "end_turn",
    )


# ── 工具选择测试 ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_rag_tool_selected():
    """模型返回 search_docs 调用 → agent 执行检索并回复。"""
    tool_resp = _make_llm_response(
        tool_calls=[ToolCall(id="tc1", name="search_docs", input={"query": "年假几天"})]
    )
    final_resp = _make_llm_response(content="根据员工手册，每年有10天年假。【来源：员工手册.md】")

    mock_llm = AsyncMock()
    mock_llm.chat.side_effect = [tool_resp, final_resp]
    mock_llm.stream = AsyncMock()

    with patch("app.services.agent.get_llm_client", return_value=mock_llm), \
         patch("app.services.agent.get_history", return_value=[]), \
         patch("app.services.agent.save_history"), \
         patch("app.services.agent._log"), \
         patch("app.services.rag.get_rag") as mock_rag:

        mock_rag.return_value.search = AsyncMock(return_value=[
            MagicMock(filename="员工手册.md", chunk_index=0, text="每年享有10天年假", score=0.9)
        ])

        result = await __import__("app.services.agent", fromlist=["run"]).run(
            user_msg="年假几天", session_id="s1"
        )

    assert "年假" in result.content
    assert any(t.name == "search_docs" for t in result.tool_calls)


@pytest.mark.asyncio
async def test_api_tool_selected():
    """模型返回 get_employee 调用 → agent 调用 Mock API 并回复。"""
    tool_resp = _make_llm_response(
        tool_calls=[ToolCall(id="tc2", name="get_employee", input={"emp_id": "001"})]
    )
    final_resp = _make_llm_response(content="员工001张三，来自研发部，P5级别。")

    mock_llm = AsyncMock()
    mock_llm.chat.side_effect = [tool_resp, final_resp]

    emp_data = json.dumps({"id": "001", "name": "张三", "dept": "研发部", "level": "P5"})

    with patch("app.services.agent.get_llm_client", return_value=mock_llm), \
         patch("app.services.agent.get_history", return_value=[]), \
         patch("app.services.agent.save_history"), \
         patch("app.services.agent._log"), \
         patch("app.tools.internal_api.get_employee", return_value=emp_data):

        from app.services import agent
        result = await agent.run(user_msg="员工001是哪个部门的", session_id="s2")

    assert any(t.name == "get_employee" for t in result.tool_calls)
    assert "研发部" in result.content


@pytest.mark.asyncio
async def test_time_tool_selected():
    """模型返回 get_current_time → agent 调用时间工具。"""
    tool_resp = _make_llm_response(
        tool_calls=[ToolCall(id="tc3", name="get_current_time", input={})]
    )
    final_resp = _make_llm_response(content="现在是2026年6月19日 14:30:00，星期五。")

    mock_llm = AsyncMock()
    mock_llm.chat.side_effect = [tool_resp, final_resp]

    with patch("app.services.agent.get_llm_client", return_value=mock_llm), \
         patch("app.services.agent.get_history", return_value=[]), \
         patch("app.services.agent.save_history"), \
         patch("app.services.agent._log"):

        from app.services import agent
        result = await agent.run(user_msg="现在几点", session_id="s3")

    assert any(t.name == "get_current_time" for t in result.tool_calls)


# ── 多轮上下文测试 ──────────────────────────────────────────

@pytest.mark.asyncio
async def test_multi_turn_context():
    """第二轮问题应携带第一轮历史，模型能理解「他」指代员工001。"""
    existing_history = [
        {"role": "user", "content": "员工001是谁"},
        {"role": "assistant", "content": "员工001是张三，研发部，P5"},
    ]
    tool_resp = _make_llm_response(
        tool_calls=[ToolCall(id="tc4", name="get_attendance", input={"emp_id": "001", "start_date": "2026-06-09", "end_date": "2026-06-13"})]
    )
    final_resp = _make_llm_response(content="张三上周出勤4天，周五缺勤。")

    mock_llm = AsyncMock()
    mock_llm.chat.side_effect = [tool_resp, final_resp]

    captured_messages = []

    async def capture_chat(messages, tools=None):
        captured_messages.extend(messages)
        return mock_llm.chat.side_effect.pop(0)

    mock_llm.chat = capture_chat

    with patch("app.services.agent.get_llm_client", return_value=mock_llm), \
         patch("app.services.agent.get_history", return_value=existing_history), \
         patch("app.services.agent.save_history"), \
         patch("app.services.agent._log"), \
         patch("app.tools.internal_api.get_attendance", return_value='{"records":[]}'):

        from app.services import agent
        result = await agent.run(user_msg="他上周来上班几天", session_id="s4")

    # 确认历史被传入（多轮上下文存在）
    user_msgs = [m["content"] for m in captured_messages if m["role"] == "user"]
    assert any("员工001" in m for m in user_msgs)


# ── 拒答测试 ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_refusal_when_no_docs():
    """检索结果为空时，模型应明确说找不到，不能编造。"""
    tool_resp = _make_llm_response(
        tool_calls=[ToolCall(id="tc5", name="search_docs", input={"query": "CEO家庭住址"})]
    )
    # 检索返回"未找到"，模型应拒答
    final_resp = _make_llm_response(content="文档里没找到相关信息，我无法提供这个答案。")

    mock_llm = AsyncMock()
    mock_llm.chat.side_effect = [tool_resp, final_resp]

    with patch("app.services.agent.get_llm_client", return_value=mock_llm), \
         patch("app.services.agent.get_history", return_value=[]), \
         patch("app.services.agent.save_history"), \
         patch("app.services.agent._log"), \
         patch("app.services.rag.get_rag") as mock_rag:

        mock_rag.return_value.search = AsyncMock(return_value=[])

        from app.services import agent
        result = await agent.run(user_msg="CEO家庭住址是什么", session_id="s5")

    assert "没找到" in result.content or "无法" in result.content


# ── 错误兜底测试 ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_tool_error_handling():
    """工具调用抛出异常，agent 应返回兜底回复，不崩溃。"""
    tool_resp = _make_llm_response(
        tool_calls=[ToolCall(id="tc6", name="get_employee", input={"emp_id": "999"})]
    )
    final_resp = _make_llm_response(content="抱歉，查询失败，请稍后重试。")

    mock_llm = AsyncMock()
    mock_llm.chat.side_effect = [tool_resp, final_resp]

    with patch("app.services.agent.get_llm_client", return_value=mock_llm), \
         patch("app.services.agent.get_history", return_value=[]), \
         patch("app.services.agent.save_history"), \
         patch("app.services.agent._log"), \
         patch("app.tools.internal_api.get_employee", side_effect=Exception("连接超时")):

        from app.services import agent
        # 不应抛异常
        result = await agent.run(user_msg="查999号员工", session_id="s6")

    assert isinstance(result, ChatResponse)
    assert result.content  # 有兜底回复


@pytest.mark.asyncio
async def test_llm_unavailable_returns_fallback():
    """LLM 完全不可用时，agent 返回友好提示而非 500。"""
    mock_llm = AsyncMock()
    mock_llm.chat.side_effect = Exception("API key invalid")

    with patch("app.services.agent.get_llm_client", return_value=mock_llm), \
         patch("app.services.agent.get_history", return_value=[]), \
         patch("app.services.agent.save_history"), \
         patch("app.services.agent._log"):

        from app.services import agent
        result = await agent.run(user_msg="任意问题", session_id="s7")

    assert "抱歉" in result.content or "无法" in result.content
    assert result.session_id == "s7"
