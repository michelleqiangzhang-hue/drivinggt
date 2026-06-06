"""Data bank / analytics endpoints — the long-term moat.

WORKSTREAM B owns this file (with accountability.py). Foundation ships working
day/week/month/year gap summaries and category breakdowns. B should expand with
streaks, trends over time, and per-category adherence history.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlmodel import Session, select

from app.auth import get_current_user
from app.database import get_session
from app.models import AccountabilityLog, BlockStatus, CalendarBlock, User
from app.schemas import CategoryTotal, GapSummary

router = APIRouter(prefix="/api/databank", tags=["databank"])


def _period_bounds(period: str, anchor: datetime) -> tuple[datetime, datetime]:
    anchor = anchor.astimezone(timezone.utc)
    day_start = datetime.combine(anchor.date(), time.min, tzinfo=timezone.utc)
    if period == "day":
        return day_start, day_start + timedelta(days=1)
    if period == "week":
        start = day_start - timedelta(days=anchor.weekday())
        return start, start + timedelta(days=7)
    if period == "month":
        start = day_start.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        return start, end
    if period == "year":
        start = day_start.replace(month=1, day=1)
        return start, start.replace(year=start.year + 1)
    raise ValueError(f"Unknown period: {period}")


@router.get("/summary", response_model=GapSummary)
def summary(
    period: str = "day",
    anchor: datetime | None = None,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> GapSummary:
    start, end = _period_bounds(period, anchor or datetime.now(timezone.utc))

    blocks = list(
        session.exec(
            select(CalendarBlock)
            .where(CalendarBlock.user_id == user.id)
            .where(CalendarBlock.start >= start)
            .where(CalendarBlock.start < end)
        ).all()
    )
    logs = list(
        session.exec(
            select(AccountabilityLog)
            .where(AccountabilityLog.user_id == user.id)
            .where(AccountabilityLog.created_at >= start)
            .where(AccountabilityLog.created_at < end)
        ).all()
    )

    planned_by_cat: dict[str, int] = defaultdict(int)
    planned_minutes = 0
    status_counts = {s: 0 for s in BlockStatus}
    for b in blocks:
        planned_minutes += b.planned_minutes
        planned_by_cat[b.category] += b.planned_minutes
        status_counts[b.status] += 1

    actual_by_cat: dict[str, int] = defaultdict(int)
    logged_minutes = productive = unproductive = 0
    for log in logs:
        mins = log.actual_minutes or 0
        logged_minutes += mins
        actual_by_cat[log.category] += mins
        if log.productive:
            productive += mins
        else:
            unproductive += mins

    completed = status_counts[BlockStatus.completed]
    adherence = completed / len(blocks) if blocks else 0.0

    return GapSummary(
        period=period,
        start=start,
        end=end,
        planned_minutes=planned_minutes,
        logged_minutes=logged_minutes,
        productive_minutes=productive,
        unproductive_minutes=unproductive,
        completed_blocks=completed,
        partial_blocks=status_counts[BlockStatus.partial],
        missed_blocks=status_counts[BlockStatus.missed],
        unlogged_blocks=status_counts[BlockStatus.planned] + status_counts[BlockStatus.unlogged],
        adherence_rate=round(adherence, 3),
        planned_by_category=[
            CategoryTotal(category=c, minutes=m) for c, m in sorted(planned_by_cat.items())
        ],
        actual_by_category=[
            CategoryTotal(category=c, minutes=m) for c, m in sorted(actual_by_cat.items())
        ],
    )
