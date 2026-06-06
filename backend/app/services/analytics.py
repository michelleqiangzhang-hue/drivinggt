"""Analytics helpers — pure functions for aggregating blocks and logs.

Extracted from the databank router so the logic is unit-testable without HTTP.
"""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, time, timedelta, timezone

from app.models import AccountabilityLog, BlockStatus, CalendarBlock
from app.schemas import CategoryTotal, GapSummary

# --------------------------------------------------------------------------- #
# Status inference
# --------------------------------------------------------------------------- #


def infer_status(block: CalendarBlock, log: AccountabilityLog) -> BlockStatus:
    """Determine block outcome by comparing plan vs reality.

    Rules (evaluated in order):
    1. Not productive AND different category => missed.
    2. Same category AND actual >= 80% planned => completed.
    3. Actual <= 20% planned OR different category => missed.
    4. Otherwise => partial.
    """
    same_category = (log.category or "").lower() == (block.category or "").lower()

    if not log.productive and not same_category:
        return BlockStatus.missed

    planned = block.planned_minutes
    actual = log.actual_minutes if log.actual_minutes is not None else planned

    if same_category and actual >= 0.8 * planned:
        return BlockStatus.completed
    if actual <= 0.2 * planned or not same_category:
        return BlockStatus.missed
    return BlockStatus.partial


def derive_actual_minutes(log_start: datetime | None, log_end: datetime | None) -> int | None:
    """Compute minutes from start/end when actual_minutes is not provided."""
    if log_start is not None and log_end is not None:
        delta = (log_end - log_start).total_seconds()
        return max(int(delta // 60), 0)
    return None


# --------------------------------------------------------------------------- #
# Period helpers
# --------------------------------------------------------------------------- #


def period_bounds(period: str, anchor: datetime) -> tuple[datetime, datetime]:
    """Return (start, end) datetimes for a given period around *anchor*."""
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


# --------------------------------------------------------------------------- #
# Aggregation
# --------------------------------------------------------------------------- #


def aggregate_gap_summary(
    period: str,
    start: datetime,
    end: datetime,
    blocks: list[CalendarBlock],
    logs: list[AccountabilityLog],
) -> GapSummary:
    """Build a GapSummary from pre-fetched blocks and logs."""

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
        planned_by_category=sorted(
            [CategoryTotal(category=c, minutes=m) for c, m in planned_by_cat.items()],
            key=lambda ct: ct.minutes,
            reverse=True,
        ),
        actual_by_category=sorted(
            [CategoryTotal(category=c, minutes=m) for c, m in actual_by_cat.items()],
            key=lambda ct: ct.minutes,
            reverse=True,
        ),
    )
