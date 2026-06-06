"""Lightweight auth.

Bogi is a private, single-user-per-account product. To keep v1 simple we support
a passwordless demo login that returns a JWT, plus a dependency that resolves the
current user from the token. A default demo user is auto-provisioned on startup.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlmodel import Session, select

from app.config import settings
from app.database import get_session
from app.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)

DEMO_EMAIL = "you@bogi.app"


def create_access_token(subject: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {"sub": subject, "exp": expire}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def get_or_create_user(session: Session, email: str, name: str = "You") -> User:
    user = session.exec(select(User).where(User.email == email)).first()
    if user is None:
        user = User(email=email, name=name)
        session.add(user)
        session.commit()
        session.refresh(user)
    return user


def get_current_user(
    token: str | None = Depends(oauth2_scheme),
    session: Session = Depends(get_session),
) -> User:
    """Resolve the current user.

    For a frictionless private app, if no/invalid token is supplied we fall back
    to the demo user so the app is immediately usable. Tighten this for multi-user.
    """
    email = DEMO_EMAIL
    if token:
        try:
            payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
            email = payload.get("sub") or DEMO_EMAIL
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )
    return get_or_create_user(session, email)
