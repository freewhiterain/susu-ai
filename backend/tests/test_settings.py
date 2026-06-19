"""设置接口 + MCP 工具暴露测试"""
import pytest


def test_settings_returns_runtime_config(client):
    resp = client.get("/api/settings")
    assert resp.status_code == 200
    data = resp.json()
    # 关键字段齐全
    for key in (
        "llm_provider",
        "llm_model",
        "embedding_provider",
        "embedding_model",
        "input_price_per_m",
        "output_price_per_m",
        "max_tool_rounds",
        "langfuse_enabled",
        "redis_connected",
        "document_count",
        "vector_count",
    ):
        assert key in data, f"缺少字段 {key}"


def test_settings_never_leaks_secrets(client):
    """设置接口绝不能下发任何 API Key。"""
    resp = client.get("/api/settings")
    body = resp.text.lower()
    assert "sk-" not in body
    assert "api_key" not in body
    assert "secret" not in body


def test_settings_doc_count_is_int(client):
    data = client.get("/api/settings").json()
    assert isinstance(data["document_count"], int)
    assert isinstance(data["vector_count"], int)


# ── MCP Server ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_mcp_lists_all_tools():
    """MCP 暴露的工具应与内部注册表一致。"""
    import mcp_server
    from app.tools.registry import TOOLS

    tools = await mcp_server.list_tools()
    names = {t.name for t in tools}
    assert names == {t.name for t in TOOLS}
    # 每个工具都带 schema
    for t in tools:
        assert t.inputSchema.get("type") == "object"


@pytest.mark.asyncio
async def test_mcp_call_time_tool():
    """通过 MCP 调用 get_current_time，应返回文本结果。"""
    import mcp_server

    result = await mcp_server.call_tool("get_current_time", {})
    assert len(result) == 1
    assert result[0].type == "text"
    assert "年" in result[0].text
