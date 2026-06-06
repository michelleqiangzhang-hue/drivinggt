"""Behavioral pattern endpoints (BETA) — train on how the user actually works.

WORKSTREAM C owns this file (with coach.py). Logic lives in
app/services/patterns.py; this router is a thin HTTP shell.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.auth import get_current_user
from app.database import get_session
from app.models import User, UserPattern
from app.schemas import PatternRead
from app.services.patterns import analyze_patterns

router = APIRouter(prefix="/api/patterns", tags=["patterns"])


@router.get("", response_model=list[PatternRead])
def list_patterns(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[UserPattern]:
    return list(
        session.exec(select(UserPattern).where(UserPattern.user_id == user.id)).all()
    )


@router.post("/analyze", response_model=list[PatternRead])
def analyze(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[UserPattern]:
    """Recompute behavioral patterns from the user's history."""
    return analyze_patterns(session, user)
