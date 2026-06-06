"""Data bank / analytics endpoints — the long-term moat.

WORKSTREAM B owns this file (with accountability.py). Foundation ships working
day/week/month/year gap summaries and category breakdowns. B should expand with
streaks, trends over time, and per-category adherence history.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import and_, or_
from sqlmodel import Session, select

from app.auth import get_current_user
from app.database import get_session
from app.models import AccountabilityLog, CalendarBlock, User
from app.schemas import GapSummary
from app.services.analytics import aggregate_gap_summary, period_bounds

router = APIRouter(prefix="/api/databank", tags=["databank"])


@router.get("/summary", response_model=GapSummary)
def summary(
    period: str = "day",
    anchor: datetime | None = None,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> GapSummary:
    start, end = period_bounds(period, anchor or datetime.now(timezone.utc))

    blocks = list(
        session.exec(
            select(CalendarBlock)
            .where(CalendarBlock.user_id == user.id)
            .where(CalendarBlock.start >= start)
            .where(CalendarBlock.start < end)
        ).all()
    )

    block_ids = [b.id for b in blocks if b.id is not None]

    # Logs selection:
    #   - Block-attached logs: include when their block is in the window
    #   - Blank-time logs (no block, has start): include by log.start
    #   - Other logs: include by created_at
    conditions = [
        and_(
            AccountabilityLog.block_id.is_not(None),
            AccountabilityLog.block_id.in_(block_ids),
        )
        if block_ids
        else False,
        and_(
            AccountabilityLog.block_id.is_(None),
            AccountabilityLog.start.is_not(None),
            AccountabilityLog.start >= start,
            AccountabilityLog.start < end,
        ),
        and_(
            AccountabilityLog.block_id.is_(None),
            AccountabilityLog.start.is_(None),
            AccountabilityLog.created_at >= start,
            AccountabilityLog.created_at < end,
        ),
    ]

    logs = list(
        session.exec(
            select(AccountabilityLog)
            .where(AccountabilityLog.user_id == user.id)
            .where(or_(*[c for c in conditions if c is not False]))
        ).all()
    )

    return aggregate_gap_summary(period, start, end, blocks, logs)
