"""Tests for behavioral pattern analysis (Workstream C).

All tests run in MOCK mode (no OpenAI key). They verify:
- Seeded mostly-missed 'Work' blocks produce a pattern with suggestion + sample_size.
- Re-running analyze is idempotent (same result count).
- Over-estimation detection works when logs have actual_minutes.
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
    User,
)
from app.services.patterns import analyze_patterns  # noqa: E402

init_db()
client = TestClient(app)


# ------------------------------------------------------------------ #
# Helper: seed blocks with mostly-missed status
# ------------------------------------------------------------------ #

def _seed_work_blocks(session: Session, user: User) -> None:
    """Create 5 Work blocks: 1 completed, 4 missed."""
    now = datetime.now(timezone.utc)
    statuses = [
        BlockStatus.completed,
        BlockStatus.missed,
        BlockStatus.missed,
        BlockStatus.missed,
        BlockStatus.missed,
    ]
    for i, status in enumerate(statuses):
        block = CalendarBlock(
            user_id=user.id,  # type: ignore[arg-type]
            title=f"Work task {i}",
            category="Work",
            start=now - timedelta(days=5 - i, hours=2),
            end=now - timedelta(days=5 - i),
            status=status,
        )
        session.add(block)
    session.commit()


def _seed_overestimation_blocks(session: Session, user: User) -> None:
    """Create blocks with logs that show over-estimation."""
    now = datetime.now(timezone.utc)
    for i in range(4):
        block = CalendarBlock(
            user_id=user.id,  # type: ignore[arg-type]
            title=f"Study session {i}",
            category="Study",
            start=now - timedelta(days=4 - i, hours=3),
            end=now - timedelta(days=4 - i),  # 3 hours = 180 min planned
            status=BlockStatus.completed,
        )
        session.add(block)
        session.commit()
        session.refresh(block)

        log = AccountabilityLog(
            user_id=user.id,  # type: ignore[arg-type]
            block_id=block.id,
            what_happened=f"Studied for {i}",
            category="Study",
            productive=True,
            actual_minutes=60,  # only 60 min actual vs 180 planned = 3x overestimate
        )
        session.add(log)
    session.commit()


# ------------------------------------------------------------------ #
# Tests: pattern analysis via service
# ------------------------------------------------------------------ #

def test_analyze_produces_pattern_for_missed_category():
    """Mostly-missed 'Work' blocks should produce a pattern with suggestion."""
    with Session(engine) as session:
        user = User(email="pat-test1@bogi.app", name="PatTest1")
        session.add(user)
        session.commit()
        session.refresh(user)
        _seed_work_blocks(session, user)

        patterns = analyze_patterns(session, user)

    assert len(patterns) >= 1
    work_pattern = next((p for p in patterns if p.category == "Work"), None)
    assert work_pattern is not None
    assert work_pattern.sample_size == 5
    assert work_pattern.suggestion
    assert work_pattern.confidence > 0
    assert "20%" in work_pattern.summary  # 1/5 = 20%


def test_analyze_is_idempotent():
    """Running analyze twice produces the same number of patterns."""
    with Session(engine) as session:
        user = User(email="pat-test2@bogi.app", name="PatTest2")
        session.add(user)
        session.commit()
        session.refresh(user)
        _seed_work_blocks(session, user)

        patterns1 = analyze_patterns(session, user)
        patterns2 = analyze_patterns(session, user)

    assert len(patterns1) == len(patterns2)
    assert patterns1[0].category == patterns2[0].category
    assert patterns1[0].sample_size == patterns2[0].sample_size


def test_overestimation_detection():
    """Blocks with logs showing over-estimation should be detected."""
    with Session(engine) as session:
        user = User(email="pat-test3@bogi.app", name="PatTest3")
        session.add(user)
        session.commit()
        session.refresh(user)
        _seed_overestimation_blocks(session, user)

        patterns = analyze_patterns(session, user)

    # All Study blocks are completed (rate=1.0) but over-estimated by 3x.
    # Over-estimation threshold is 1.5x, so a pattern should be generated.
    study_pattern = next((p for p in patterns if p.category == "Study"), None)
    assert study_pattern is not None
    assert "3.0x" in study_pattern.summary
    assert study_pattern.suggestion
    assert study_pattern.sample_size == 4


# ------------------------------------------------------------------ #
# Tests: pattern endpoint (integration)
# ------------------------------------------------------------------ #

def test_analyze_endpoint():
    """POST /api/patterns/analyze returns patterns via HTTP."""
    # First seed some data via the blocks endpoint
    for i in range(4):
        client.post(
            "/api/blocks",
            json={
                "title": f"Chores {i}",
                "category": "Chores",
                "start": f"2025-02-0{i + 1}T09:00:00+00:00",
                "end": f"2025-02-0{i + 1}T11:00:00+00:00",
            },
        )
    # Mark 3 of them as missed via status update
    blocks_r = client.get("/api/blocks")
    chore_blocks = [b for b in blocks_r.json() if b["category"] == "Chores"]
    for b in chore_blocks[:3]:
        client.patch(f"/api/blocks/{b['id']}", json={"status": "missed"})

    r = client.post("/api/patterns/analyze")
    assert r.status_code == 200


def test_list_patterns_endpoint():
    """GET /api/patterns returns stored patterns."""
    r = client.get("/api/patterns")
    assert r.status_code == 200
    assert isinstance(r.json(), list)
