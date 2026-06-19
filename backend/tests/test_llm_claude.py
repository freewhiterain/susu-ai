"""Claude 适配层测试 —— 覆盖此前被遗漏的多模型路径。

回归点：
- get_llm_client(provider=claude) 不再抛 NameError（曾因未 import ClaudeClient 而崩溃）
- system 角色被剥离为顶层参数，不会以 role=system 混进 messages（否则 Anthropic 返回 400）
"""
import pytest
from app.core.config import get_settings
from app.services.llm.claude import _split_system, _to_claude_messages


def test_split_system_extracts_system():
    msgs = [
        {"role": "system", "content": "你是小苏"},
        {"role": "user", "content": "你好"},
        {"role": "assistant", "content": "你好，有什么可以帮你"},
    ]
    system, rest = _split_system(msgs)
    assert system == "你是小苏"
    assert all(m["role"] != "system" for m in rest)
    assert len(rest) == 2


def test_split_system_merges_multiple():
    msgs = [
        {"role": "system", "content": "规则一"},
        {"role": "user", "content": "hi"},
        {"role": "system", "content": "规则二"},
    ]
    system, rest = _split_system(msgs)
    assert "规则一" in system and "规则二" in system
    assert len(rest) == 1


def test_claude_messages_never_contains_system():
    """先 split_system 再转换，结果里不允许出现 role=system。"""
    msgs = [
        {"role": "system", "content": "你是小苏"},
        {"role": "user", "content": "查一下年假"},
    ]
    _, rest = _split_system(msgs)
    converted = _to_claude_messages(rest)
    assert all(m["role"] in ("user", "assistant") for m in converted)


def test_tool_result_converted_to_user_block():
    msgs = [
        {"role": "user", "content": "查工号001"},
        {"role": "assistant", "content": "", "tool_calls": [
            {"id": "t1", "type": "function",
             "function": {"name": "get_employee", "arguments": '{"emp_id": "001"}'}}
        ]},
        {"role": "tool", "tool_call_id": "t1", "tool_name": "get_employee", "content": "张三"},
    ]
    converted = _to_claude_messages(msgs)
    # 最后一条应是带 tool_result block 的 user 消息
    assert converted[-1]["role"] == "user"
    assert converted[-1]["content"][0]["type"] == "tool_result"
    assert converted[-1]["content"][0]["tool_use_id"] == "t1"
    # assistant 轮次应含 tool_use block
    assert converted[1]["role"] == "assistant"
    assert converted[1]["content"][-1]["type"] == "tool_use"


def test_get_llm_client_claude_no_nameerror(monkeypatch):
    """provider=claude 时工厂应能正常返回 ClaudeClient（回归 Bug 1）。"""
    from app.services.llm import openai_client as oc

    monkeypatch.setenv("LLM_PROVIDER", "claude")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
    get_settings.cache_clear()
    oc.get_llm_client.cache_clear()
    try:
        client = oc.get_llm_client()
        from app.services.llm.claude import ClaudeClient
        assert isinstance(client, ClaudeClient)
    finally:
        get_settings.cache_clear()
        oc.get_llm_client.cache_clear()
