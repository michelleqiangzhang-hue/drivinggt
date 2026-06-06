"""Tests for the AI coach (Workstream C).

All tests run in MOCK mode (no OpenAI key). They verify:
- Chat returns a non-empty reply and persists messages.
- Follow-up with conversation_id includes prior history.
- Context builder includes recent blocks/logs/goals (tested via service function).
"""
from __future__ import annotations

import os
import tempfile

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mktemp(suffix='.db')}")

from datetime import datetime, timedelta, timezone  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session  # noqa: E402

from app.database import engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import (  # noqa: E402
    AccountabilityLog,
    BlockStatus,
    CalendarBlock,
    Goal,
    User,
    UserPattern,
)
from app.services.coach import build_context  # noqa: E402

init_db()
client = TestClient(app)


# ------------------------------------------------------------------ #
# Helper: seed data for a user
# ------------------------------------------------------------------ #

def _seed_user_data(session: Session, user: User) -> None:
    """Seed blocks, logs, goals, and patterns for context-builder tests."""
    now = datetime.now(timezone.utc)

    # Blocks
    for i, (title, cat, status) in enumerate([
        ("Edit videos", "Work", BlockStatus.completed),
        ("Email clients", "Work", BlockStatus.missed),
        ("Email clients", "Work", BlockStatus.missed),
        ("Study math", "Study", BlockStatus.completed),
        ("Go for a run", "Health", BlockStatus.missed),
    ]):
        block = CalendarBlock(
            user_id=user.id,  # type: ignore[arg-type]
            title=title,
            category=cat,
            start=now - timedelta(days=5 - i, hours=2),
            end=now - timedelta(days=5 - i),
            status=status,
        )
        session.add(block)

    # Logs
    log = AccountabilityLog(
        user_id=user.id,  # type: ignore[arg-type]
        what_happened="Scrolled social media",
        category="Social media",
        productive=False,
        actual_minutes=30,
    )
    session.add(log)

    # Goals
    goal = Goal(
        user_id=user.id,  # type: ignore[arg-type]
        title="Send 5 client emails per week",
        horizon="week",
        target_category="Work",
    )
    session.add(goal)

    # Patterns
    pattern = UserPattern(
        user_id=user.id,  # type: ignore[arg-type]
        category="Work",
        summary="You complete only 33% of planned 'Work' blocks.",
        confidence=0.65,
        sample_size=3,
        suggestion="Try shorter blocks.",
    )
    session.add(pattern)

    session.commit()


# ------------------------------------------------------------------ #
# Tests: context builder (service-level, not LLM text)
# ------------------------------------------------------------------ #

def test_build_context_includes_blocks_logs_goals():
    """build_context should include blocks, logs, goals, and patterns."""
    with Session(engine) as session:
        user = User(email="ctx-test@bogi.app", name="CtxTest")
        session.add(user)
        session.commit()
        session.refresh(user)

        _seed_user_data(session, user)

        ctx = build_context(session, user)

    assert "Recent planned blocks" in ctx
    assert "Edit videos" in ctx
    assert "Email clients" in ctx
    assert "missed" in ctx

    assert "accountability logs" in ctx.lower() or "actually happened" in ctx.lower()
    assert "Scrolled social media" in ctx

    assert "Active goals" in ctx
    assert "Send 5 client emails" in ctx

    assert "Learned behavioral patterns" in ctx or "pattern" in ctx.lower()
    assert "33%" in ctx

    # Aggregate stats
    assert "planned" in ctx.lower()
    assert "completed" in ctx.lower()


# ------------------------------------------------------------------ #
# Tests: chat endpoint
# ------------------------------------------------------------------ #

def test_chat_returns_nonempty_reply():
    """POST /api/coach/chat returns a non-empty reply."""
    r = client.post("/api/coach/chat", json={"message": "Help me plan my day"})
    assert r.status_code == 200
    data = r.json()
    assert data["reply"]
    assert data["conversation_id"]
    assert len(data["history"]) >= 2  # user + assistant


def test_chat_persists_messages():
    """Messages are persisted and visible via GET conversation."""
    r1 = client.post("/api/coach/chat", json={"message": "What did I do today?"})
    assert r1.status_code == 200
    conv_id = r1.json()["conversation_id"]

    r2 = client.get(f"/api/coach/conversations/{conv_id}")
    assert r2.status_code == 200
    history = r2.json()["history"]
    assert any(m["role"] == "user" and "What did I do today" in m["content"] for m in history)
    assert any(m["role"] == "assistant" for m in history)


def test_followup_includes_prior_history():
    """A follow-up with conversation_id includes earlier messages."""
    r1 = client.post("/api/coach/chat", json={"message": "First message"})
    conv_id = r1.json()["conversation_id"]

    r2 = client.post(
        "/api/coach/chat",
        json={"conversation_id": conv_id, "message": "Second message"},
    )
    assert r2.status_code == 200
    history = r2.json()["history"]
    contents = [m["content"] for m in history]
    assert "First message" in contents
    assert "Second message" in contents
    # Should have 4 messages: user1, assistant1, user2, assistant2
    assert len(history) >= 4


def test_chat_nonexistent_conversation():
    """Using a bogus conversation_id returns 404."""
    r = client.post(
        "/api/coach/chat",
        json={"conversation_id": 999999, "message": "hello"},
    )
    assert r.status_code == 404
