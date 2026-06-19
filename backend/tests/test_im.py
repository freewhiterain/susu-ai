"""IM 适配器测试"""
import hmac
import hashlib
import base64
import pytest
from unittest.mock import AsyncMock, patch
from app.services.im.dingtalk import DingTalkAdapter
from app.services.im.base import IMEvent

SECRET = "test_secret_key"


def _make_sign(timestamp: str, secret: str) -> str:
    msg = f"{timestamp}\n{secret}"
    return base64.b64encode(
        hmac.new(secret.encode(), msg.encode(), digestmod=hashlib.sha256).digest()
    ).decode()


@pytest.fixture
def adapter(monkeypatch):
    monkeypatch.setenv("DINGTALK_APP_SECRET", SECRET)
    # 重新加载 settings 缓存
    from app.core.config import get_settings
    get_settings.cache_clear()
    a = DingTalkAdapter()
    yield a
    get_settings.cache_clear()


# ── 验签测试 ───────────────────────────────────────────────

def test_verify_valid_signature(adapter):
    timestamp = "1718700000000"
    sign = _make_sign(timestamp, SECRET)
    assert adapter.verify_request(timestamp, sign) is True


def test_verify_invalid_signature(adapter):
    assert adapter.verify_request("1718700000000", "fake_sign") is False


def test_verify_no_secret_skips(monkeypatch):
    monkeypatch.setenv("DINGTALK_APP_SECRET", "")
    from app.core.config import get_settings
    get_settings.cache_clear()
    a = DingTalkAdapter()
    assert a.verify_request("any", "any") is True
    get_settings.cache_clear()


# ── 消息解析测试 ────────────────────────────────────────────

def test_parse_private_text(adapter):
    body = {
        "msgtype": "text",
        "text": {"content": "年假几天"},
        "senderNick": "张三",
        "senderId": "user001",
        "conversationId": "cid001",
        "conversationType": "1",
        "sessionWebhook": "https://oapi.dingtalk.com/robot/xxx",
    }
    event = adapter.parse_event(body)
    assert event.text == "年假几天"
    assert event.sender_id == "user001"
    assert event.platform == "dingtalk"


def test_parse_group_message_strips_at(adapter):
    """群聊消息应去除 @机器人 前缀。"""
    body = {
        "msgtype": "text",
        "text": {"content": "@小苏 帮我查一下年假"},
        "senderNick": "李四",
        "senderId": "user002",
        "conversationId": "cid_group",
        "conversationType": "2",
        "sessionWebhook": "https://oapi.dingtalk.com/robot/xxx",
    }
    event = adapter.parse_event(body)
    assert "@小苏" not in event.text
    assert "年假" in event.text


def test_parse_multiple_at_stripped(adapter):
    body = {
        "msgtype": "text",
        "text": {"content": "@小苏 @张三 帮我看看报销流程"},
        "senderNick": "王五",
        "senderId": "user003",
        "conversationId": "cid_group2",
        "conversationType": "2",
        "sessionWebhook": "https://example.com",
    }
    event = adapter.parse_event(body)
    assert event.text == "帮我看看报销流程"


# ── 消息发送测试 ────────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_message_posts_to_session_webhook(adapter):
    event = IMEvent(
        platform="dingtalk",
        sender_id="user001",
        sender_nick="张三",
        conversation_id="cid001",
        conversation_type="1",
        text="年假几天",
        raw={"sessionWebhook": "https://oapi.dingtalk.com/robot/test"},
    )
    with patch("httpx.AsyncClient") as mock_client:
        mock_resp = AsyncMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = lambda: None
        mock_client.return_value.__aenter__.return_value.post = AsyncMock(return_value=mock_resp)
        await adapter.send_message(event, "每年10天年假", [])
    mock_client.return_value.__aenter__.return_value.post.assert_called_once()


@pytest.mark.asyncio
async def test_send_message_no_webhook_does_not_crash(adapter):
    event = IMEvent(
        platform="dingtalk",
        sender_id="u1",
        sender_nick="张三",
        conversation_id="c1",
        conversation_type="1",
        text="test",
        raw={},  # 没有 sessionWebhook
    )
    # 不应抛异常
    await adapter.send_message(event, "回复内容", [])
