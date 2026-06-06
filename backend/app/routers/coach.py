"""AI coach chat endpoint — the honest accountability coach.

WORKSTREAM C owns this file (with patterns.py). Logic lives in
app/services/coach.py; this router is a thin HTTP shell.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session

from app.auth import get_current_user
from app.database import get_session
from app.models import User
from app.schemas import ChatMessage, ChatRequest, ChatResponse
from app.services.coach import (
    generate_reply,
    get_conversation_history,
    get_or_create_conversation,
)

router = APIRouter(prefix="/api/coach", tags=["coach"])


@router.post("/chat", response_model=ChatResponse)
def chat(
    body: ChatRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ChatResponse:
    conv = get_or_create_conversation(session, user, body.conversation_id)
    if conv is None:
        raise HTTPException(404, "Conversation not found")

    history = get_conversation_history(session, conv.id)  # type: ignore[arg-type]

    reply_text = generate_reply(session, user, conv, body.message, history)

    # Reload full history (now includes the new user + assistant messages)
    full = get_conversation_history(session, conv.id)  # type: ignore[arg-type]
    return ChatResponse(
        conversation_id=conv.id,  # type: ignore[arg-type]
        reply=reply_text,
        history=[ChatMessage(role=m.role, content=m.content) for m in full],
    )


@router.get("/conversations/{conversation_id}", response_model=ChatResponse)
def get_conversation(
    conversation_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> ChatResponse:
    conv = get_or_create_conversation(session, user, conversation_id)
    if conv is None:
        raise HTTPException(404, "Conversation not found")
    msgs = get_conversation_history(session, conv.id)  # type: ignore[arg-type]
    last = next((m.content for m in reversed(msgs) if m.role == "assistant"), "")
    return ChatResponse(
        conversation_id=conv.id,  # type: ignore[arg-type]
        reply=last,
        history=[ChatMessage(role=m.role, content=m.content) for m in msgs],
    )
