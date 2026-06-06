"""Service layer for behavioral pattern analysis (BETA).

Detects:
- Per-category completion rate (fraction of completed blocks).
- Over-estimation factor (planned minutes vs actual minutes when logs exist).
- Writes UserPattern rows with summary, confidence, sample_size, suggestion.
"""
from __future__ import annotations

from collections import defaultdict

from sqlmodel import Session, select

from app.models import (
    AccountabilityLog,
    BlockStatus,
    CalendarBlock,
    User,
    UserPattern,
)


def analyze_patterns(session: Session, user: User) -> list[UserPattern]:
    """Recompute all behavioral patterns from the user's block/log history.

    Deletes previous machine-generated patterns and creates fresh ones.
    Returns the list of newly created patterns.
    """
    blocks = list(
        session.exec(
            select(CalendarBlock).where(CalendarBlock.user_id == user.id)
        ).all()
    )

    # Pre-load logs keyed by block_id for over-estimation analysis
    logs = list(
        session.exec(
            select(AccountabilityLog).where(AccountabilityLog.user_id == user.id)
        ).all()
    )
    log_by_block: dict[int, AccountabilityLog] = {}
    for lg in logs:
        if lg.block_id is not None:
            log_by_block[lg.block_id] = lg

    # Group resolved blocks by category
    by_cat: dict[str, list[CalendarBlock]] = defaultdict(list)
    for b in blocks:
        if b.status in (BlockStatus.completed, BlockStatus.partial, BlockStatus.missed):
            by_cat[b.category].append(b)

    # Clear previous machine-generated patterns for a clean recompute
    for old in session.exec(
        select(UserPattern).where(UserPattern.user_id == user.id)
    ).all():
        session.delete(old)

    patterns: list[UserPattern] = []

    for category, items in by_cat.items():
        if len(items) < 2:
            continue

        # --- Completion rate ---
        completed = sum(1 for b in items if b.status == BlockStatus.completed)
        rate = completed / len(items)

        # --- Over-estimation factor ---
        paired: list[tuple[int, int]] = []  # (planned, actual)
        for b in items:
            if b.id is not None and b.id in log_by_block:
                lg = log_by_block[b.id]
                if lg.actual_minutes is not None and lg.actual_minutes > 0:
                    paired.append((b.planned_minutes, lg.actual_minutes))

        overestimation_factor: float | None = None
        if paired:
            total_planned = sum(p for p, _ in paired)
            total_actual = sum(a for _, a in paired)
            if total_actual > 0:
                overestimation_factor = round(total_planned / total_actual, 2)

        # --- Build pattern when completion rate is low ---
        if rate < 0.6:
            avg_planned = sum(b.planned_minutes for b in items) // len(items)
            summary_parts = [
                f"You complete only {round(rate * 100)}% of your planned "
                f"'{category}' blocks (avg {avg_planned} min)."
            ]
            if overestimation_factor is not None and overestimation_factor > 1.2:
                summary_parts.append(
                    f" You over-estimate by {overestimation_factor}x "
                    f"(plan {avg_planned}m, do less)."
                )

            suggestion_parts = [
                f"Try shorter '{category}' blocks (~{max(30, avg_planned // 2)} min) "
                "and check in halfway through."
            ]
            if overestimation_factor is not None and overestimation_factor > 1.2:
                suggested_mins = max(15, int(avg_planned / overestimation_factor))
                suggestion_parts.append(
                    f" Or plan only ~{suggested_mins} min based on your real pace."
                )

            pattern = UserPattern(
                user_id=user.id,
                category=category,
                summary="".join(summary_parts),
                confidence=round(min(0.95, 0.5 + len(items) * 0.05), 2),
                sample_size=len(items),
                suggestion="".join(suggestion_parts),
            )
            session.add(pattern)
            patterns.append(pattern)

        # --- Over-estimation pattern even when completion rate is OK ---
        elif overestimation_factor is not None and overestimation_factor > 1.5:
            avg_planned = sum(b.planned_minutes for b in items) // len(items)
            suggested_mins = max(15, int(avg_planned / overestimation_factor))
            pattern = UserPattern(
                user_id=user.id,
                category=category,
                summary=(
                    f"Your '{category}' blocks take {overestimation_factor}x less time "
                    f"than planned (avg plan {avg_planned} min)."
                ),
                confidence=round(min(0.95, 0.5 + len(paired) * 0.05), 2),
                sample_size=len(items),
                suggestion=(
                    f"Plan ~{suggested_mins} min for '{category}' blocks to match reality."
                ),
            )
            session.add(pattern)
            patterns.append(pattern)

    session.commit()
    for p in patterns:
        session.refresh(p)
    return patterns
