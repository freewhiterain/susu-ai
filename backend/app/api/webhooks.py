from fastapi import APIRouter, Request, BackgroundTasks, HTTPException
from loguru import logger
from app.services.im.dingtalk import get_dingtalk
from app.services import agent
from app.services.session import new_session_id

router = APIRouter(prefix="/api/webhook", tags=["webhook"])


async def _process_dingtalk(event_body: dict) -> None:
    """后台任务：调用 Agent 并回复（钉钉要求 5s 内返回 HTTP 200，此处异步处理）。"""
    adapter = get_dingtalk()
    try:
        event = adapter.parse_event(event_body)

        if not event.text:
            return   # 空消息忽略（如撤回通知等系统消息）

        # session key：按平台+用户+会话维度隔离，不同人的上下文不互串
        session_id = f"dingtalk:{event.sender_id}:{event.conversation_id}"

        logger.info(f"DingTalk msg | user={event.sender_nick} | text={event.text[:50]}")

        result = await agent.run(
            user_msg=event.text,
            session_id=session_id,
            platform="dingtalk",
            user_id=event.sender_id,
        )
        await adapter.send_message(event, result.content, result.references)

    except Exception as e:
        logger.error(f"DingTalk process error: {e}")
        try:
            await adapter.send_error(adapter.parse_event(event_body))
        except Exception:
            pass   # 连兜底都发不出去，至少不崩


@router.post("/dingtalk")
async def dingtalk_webhook(request: Request, background_tasks: BackgroundTasks):
    """
    钉钉企业内部机器人 Webhook 端点。
    立即返回 200，后台异步处理并回复。
    """
    # 验签（请求头携带 timestamp 和 sign）
    timestamp = request.headers.get("timestamp", "")
    sign = request.headers.get("sign", "")
    if timestamp and sign:
        if not get_dingtalk().verify_request(timestamp, sign):
            raise HTTPException(status_code=403, detail="签名验证失败")

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="无效的 JSON body")

    # 钉钉消息类型过滤，只处理文本消息
    if body.get("msgtype") not in ("text",):
        return {"code": 0, "msg": "ignored"}

    background_tasks.add_task(_process_dingtalk, body)
    return {"code": 0, "msg": "ok"}
