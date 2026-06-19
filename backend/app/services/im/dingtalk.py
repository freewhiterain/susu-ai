import hmac
import hashlib
import base64
import re
import httpx
from loguru import logger
from app.core.config import get_settings
from app.services.im.base import IMAdapter, IMEvent


class DingTalkAdapter(IMAdapter):
    """
    钉钉企业内部机器人 Webhook 适配器。
    消息接收：POST /api/webhook/dingtalk
    消息回复：POST sessionWebhook（钉钉动态下发的临时 URL）
    """

    def verify_request(self, timestamp: str, sign: str) -> bool:
        """
        验签：HMAC-SHA256(f"{timestamp}\n{secret}") → Base64
        钉钉在请求头带 timestamp 和 sign，需对比。
        """
        secret = get_settings().dingtalk_app_secret
        if not secret:
            return True   # 未配置 secret 时跳过验签（开发环境）
        try:
            string_to_sign = f"{timestamp}\n{secret}"
            sig = base64.b64encode(
                hmac.new(
                    secret.encode("utf-8"),
                    string_to_sign.encode("utf-8"),
                    digestmod=hashlib.sha256,
                ).digest()
            ).decode()
            return hmac.compare_digest(sig, sign)
        except Exception as e:
            logger.warning(f"DingTalk verify error: {e}")
            return False

    def parse_event(self, body: dict) -> IMEvent:
        raw_text = body.get("text", {}).get("content", "").strip()
        # 去掉 @机器人 mention（钉钉群里用户消息前缀）
        clean_text = re.sub(r"@\S+", "", raw_text).strip()
        return IMEvent(
            platform="dingtalk",
            sender_id=body.get("senderId", ""),
            sender_nick=body.get("senderNick", ""),
            conversation_id=body.get("conversationId", ""),
            conversation_type=body.get("conversationType", "1"),
            text=clean_text,
            raw=body,
        )

    async def send_message(
        self, event: IMEvent, content: str, references: list[dict]
    ) -> None:
        session_webhook = event.raw.get("sessionWebhook", "")
        if not session_webhook:
            logger.warning("DingTalk: no sessionWebhook in event")
            return

        # 构造 Markdown 消息（引用来源附在末尾）
        md_text = content
        if references:
            ref_lines = []
            for i, ref in enumerate(references[:3], 1):  # 最多展示 3 条
                snippet = ref.get("snippet", "")
                # 提取来源行
                source_match = re.search(r"【来源：(.+?)】", snippet)
                if source_match:
                    ref_lines.append(f"> {i}. {source_match.group(1)}")
            if ref_lines:
                md_text += "\n\n**参考来源：**\n" + "\n".join(ref_lines)

        payload: dict = {
            "msgtype": "markdown",
            "markdown": {
                "title": "小苏",
                "text": f"**小苏**\n\n{md_text}",
            },
        }
        # 群聊时 @ 提问者
        if event.conversation_type == "2" and event.sender_id:
            payload["at"] = {"atUserIds": [event.sender_id]}

        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(session_webhook, json=payload)
                resp.raise_for_status()
                logger.info(f"DingTalk reply sent: {resp.status_code}")
        except Exception as e:
            logger.error(f"DingTalk send_message error: {e}")

    async def send_error(self, event: IMEvent, msg: str = "服务暂时不可用，请稍后重试") -> None:
        """发送错误兜底消息。"""
        await self.send_message(event, msg, [])


_adapter: DingTalkAdapter | None = None


def get_dingtalk() -> DingTalkAdapter:
    global _adapter
    if _adapter is None:
        _adapter = DingTalkAdapter()
    return _adapter
