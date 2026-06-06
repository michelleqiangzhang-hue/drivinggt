"""Auth endpoints (passwordless demo login + current user)."""
from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlmodel import Session

from app.auth import create_access_token, get_current_user, get_or_create_user
from app.database import get_session
from app.models import User
from app.schemas import LoginRequest, Token, UserRead

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login", response_model=Token)
def login(body: LoginRequest, session: Session = Depends(get_session)) -> Token:
    user = get_or_create_user(session, body.email or "you@bogi.app")
    return Token(access_token=create_access_token(user.email))


@router.get("/me", response_model=UserRead)
def me(user: User = Depends(get_current_user)) -> User:
    return user
