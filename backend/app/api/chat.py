from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from app.models.chat import ChatRequest, ChatResponse
from app.services import agent
from app.services.session import new_session_id

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(req: ChatRequest):
    """非流式对话（IM 内部使用，或调试）。"""
    session_id = req.session_id or new_session_id()
    return await agent.run(
        user_msg=req.message,
        session_id=session_id,
    )


@router.get("/stream")
async def chat_stream(message: str, session_id: str = ""):
    """SSE 流式对话（Web 聊天页使用）。"""
    sid = session_id or new_session_id()

    return StreamingResponse(
        agent.run_stream(message, sid),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
