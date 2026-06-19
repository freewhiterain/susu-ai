from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from app.db.database import get_session
from app.models.log import ConversationLog, ConversationLogRead

router = APIRouter(prefix="/api/logs", tags=["logs"])


@router.get("", response_model=list[ConversationLogRead])
def list_logs(
    platform: str | None = Query(None),
    session_id: str | None = Query(None),
    limit: int = Query(50, le=200),
    offset: int = Query(0),
    session: Session = Depends(get_session),
):
    q = select(ConversationLog).order_by(ConversationLog.created_at.desc())
    if platform:
        q = q.where(ConversationLog.platform == platform)
    if session_id:
        q = q.where(ConversationLog.session_id == session_id)
    q = q.offset(offset).limit(limit)
    return session.exec(q).all()


@router.get("/stats")
def log_stats(session: Session = Depends(get_session)):
    from sqlmodel import func
    from datetime import datetime, date
    today = date.today().isoformat()
    rows = session.exec(select(ConversationLog)).all()
    today_rows = [r for r in rows if r.created_at.date().isoformat() == today]
    return {
        "total_conversations": len(rows),
        "today_conversations": len(today_rows),
        "today_input_tokens": sum(r.input_tokens for r in today_rows),
        "today_output_tokens": sum(r.output_tokens for r in today_rows),
        "today_cost_usd": round(sum(r.cost_usd for r in today_rows), 4),
    }
