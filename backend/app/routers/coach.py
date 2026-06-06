"""AI coach chat endpoint — the honest accountability coach.

WORKSTREAM C owns this file (with patterns.py). Foundation ships a working chat
loop that persists conversations and injects the coach persona + a lightweight
data summary. C should enrich context (recent blocks/logs/goals/patterns), make
the coach blunt and goal-aware, and add the "ask AI about your life" Q&A.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.ai import llm_chat
from app.ai.prompts import COACH_SYSTEM
from app.auth import get_current_user
from app.database import get_session
from app.models import CoachMessage, Conversation, User
from app.schemas import ChatMessage, ChatRequest, ChatResponse

router = APIRouter(prefix="/api/coach", tags=["coach"])


def _build_context(session: Session, user: User) -> str:
    """Summarize the user's recent reality for the coach. WORKSTREAM C: expand."""
    from app.models import AccountabilityLog, CalendarBlock

    blocks = list(
        session.exec(
            select(CalendarBlock)
            .where(CalendarBlock.user_id == user.id)
            .order_by(CalendarBlock.start.desc())
            .limit(10)
        ).all()
    )
    logs = list(
        session.exec(
            select(AccountabilityLog)
            .where(AccountabilityLog.user_id == user.id)
            .order_by(AccountabilityLog.created_at.desc())
            .limit(10)
        ).all()
    )
    lines = [f"User: {user.name}"]
    if blocks:
        lines.append("Recent planned blocks:")
        lines += [f"- {b.title} ({b.category}, {b.planned_minutes}m) [{b.status}]" for b in blocks]
    if logs:
        lines.append("Recently logged reality:")
        lines += [f"- {log.what_happened} ({log.category})" for log in logs]
    return "\n".join(lines)


@router.post("/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ChatResponse:
    if body.conversation_id is not None:
        conv = session.get(Conversation, body.conversation_id)
        if conv is None or conv.user_id != user.id:
            raise HTTPException(404, "Conversation not found")
    else:
        conv = Conversation(user_id=user.id)
        session.add(conv)
        session.commit()
        session.refresh(conv)

    history = list(
        session.exec(
            select(CoachMessage)
            .where(CoachMessage.conversation_id == conv.id)
            .order_by(CoachMessage.created_at)
        ).all()
    )

    user_msg = CoachMessage(conversation_id=conv.id, role="user", content=body.message)
    session.add(user_msg)

    llm_messages = [
        {"role": "system", "content": COACH_SYSTEM},
        {"role": "system", "content": "Context about the user:\n" + _build_context(session, user)},
    ]
    llm_messages += [{"role": m.role, "content": m.content} for m in history]
    llm_messages.append({"role": "user", "content": body.message})

    reply_text = llm_chat(llm_messages)
    assistant_msg = CoachMessage(conversation_id=conv.id, role="assistant", content=reply_text)
    session.add(assistant_msg)
    session.commit()

    full = history + [user_msg, assistant_msg]
    return ChatResponse(
        conversation_id=conv.id,
        reply=reply_text,
        history=[ChatMessage(role=m.role, content=m.content) for m in full],
    )


@router.get("/conversations/{conversation_id}", response_model=ChatResponse)
def get_conversation(
    conversation_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ChatResponse:
    conv = session.get(Conversation, conversation_id)
    if conv is None or conv.user_id != user.id:
        raise HTTPException(404, "Conversation not found")
    msgs = list(
        session.exec(
            select(CoachMessage)
            .where(CoachMessage.conversation_id == conv.id)
            .order_by(CoachMessage.created_at)
        ).all()
    )
    last = next((m.content for m in reversed(msgs) if m.role == "assistant"), "")
    return ChatResponse(
        conversation_id=conv.id,
        reply=last,
        history=[ChatMessage(role=m.role, content=m.content) for m in msgs],
    )
