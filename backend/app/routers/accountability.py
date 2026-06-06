"""Accountability loop endpoints — what ACTUALLY happened.

WORKSTREAM B owns this file (with databank.py). The accountability loop is the
core feature: when a block ends, the user accounts for it. Foundation ships
working log CRUD + status inference + an "unaccounted blocks" feed. B should add
richer categorization, blank-time logging, and coach-driven check-in flows.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.auth import get_current_user
from app.database import get_session
from app.models import AccountabilityLog, BlockStatus, CalendarBlock, User
from app.schemas import BlockRead, LogCreate, LogRead
from app.services.analytics import derive_actual_minutes, infer_status

router = APIRouter(prefix="/api/logs", tags=["accountability"])


@router.get("", response_model=list[LogRead])
def list_logs(
    start: datetime | None = None,
    end: datetime | None = None,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[AccountabilityLog]:
    stmt = select(AccountabilityLog).where(AccountabilityLog.user_id == user.id)
    if start is not None:
        stmt = stmt.where(AccountabilityLog.created_at >= start)
    if end is not None:
        stmt = stmt.where(AccountabilityLog.created_at < end)
    return list(session.exec(stmt.order_by(AccountabilityLog.created_at.desc())).all())


@router.post("", response_model=LogRead, status_code=201)
def create_log(
    body: LogCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> AccountabilityLog:
    log = AccountabilityLog(user_id=user.id, **body.model_dump())

    # Derive actual_minutes from start/end for blank-time logs (no block).
    if log.actual_minutes is None and log.block_id is None:
        derived = derive_actual_minutes(log.start, log.end)
        if derived is not None:
            log.actual_minutes = derived

    # If this log accounts for a planned block, update that block's status.
    if log.block_id is not None:
        block = session.get(CalendarBlock, log.block_id)
        if block is None or block.user_id != user.id:
            raise HTTPException(404, "Block not found")
        if log.actual_minutes is None:
            log.actual_minutes = block.planned_minutes
        block.status = infer_status(block, log)
        session.add(block)

    session.add(log)
    session.commit()
    session.refresh(log)
    return log


@router.get("/unaccounted", response_model=list[BlockRead])
def unaccounted_blocks(
    now: datetime | None = None,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[CalendarBlock]:
    """Blocks that have ended but haven't been accounted for yet — the check-in feed."""
    current = now or datetime.now(timezone.utc)
    stmt = (
        select(CalendarBlock)
        .where(CalendarBlock.user_id == user.id)
        .where(CalendarBlock.end <= current)
        .where(CalendarBlock.status.in_([BlockStatus.planned, BlockStatus.unlogged]))
        .order_by(CalendarBlock.start)
    )
    return list(session.exec(stmt).all())
