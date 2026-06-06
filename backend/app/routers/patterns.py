"""Behavioral pattern endpoints (BETA) — train on how the user actually works.

WORKSTREAM C owns this file (with coach.py). Foundation ships a working baseline
analyzer that detects categories the user repeatedly fails to complete. C should
make this richer (time-of-day patterns, over-estimation factors per category) and
feed warnings back into planning.
"""
from __future__ import annotations

from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.auth import get_current_user
from app.database import get_session
from app.models import BlockStatus, CalendarBlock, User, UserPattern
from app.schemas import PatternRead

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
    """Recompute behavioral patterns from the user's history.

    Baseline: for each category, what fraction of planned blocks were completed?
    If a category is consistently missed/partial, record a pattern + suggestion.
    """
    blocks = list(
        session.exec(
            select(CalendarBlock).where(CalendarBlock.user_id == user.id)
        ).all()
    )

    by_cat: dict[str, list[CalendarBlock]] = defaultdict(list)
    for b in blocks:
        if b.status in (BlockStatus.completed, BlockStatus.partial, BlockStatus.missed):
            by_cat[b.category].append(b)

    # Clear previous machine-generated patterns for a clean recompute.
    for old in session.exec(select(UserPattern).where(UserPattern.user_id == user.id)).all():
        session.delete(old)

    patterns: list[UserPattern] = []
    for category, items in by_cat.items():
        if len(items) < 2:
            continue
        completed = sum(1 for b in items if b.status == BlockStatus.completed)
        rate = completed / len(items)
        if rate < 0.6:
            avg_planned = sum(b.planned_minutes for b in items) // len(items)
            pattern = UserPattern(
                user_id=user.id,
                category=category,
                summary=(
                    f"You complete only {round(rate * 100)}% of your planned "
                    f"'{category}' blocks (avg {avg_planned} min)."
                ),
                confidence=round(min(0.95, 0.5 + len(items) * 0.05), 2),
                sample_size=len(items),
                suggestion=(
                    f"Try shorter '{category}' blocks (~{max(30, avg_planned // 2)} min) "
                    "and check in halfway through."
                ),
            )
            session.add(pattern)
            patterns.append(pattern)

    session.commit()
    for p in patterns:
        session.refresh(p)
    return patterns
