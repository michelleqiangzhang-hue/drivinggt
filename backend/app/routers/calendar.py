"""Calendar / planning endpoints — the user's INTENTION.

WORKSTREAM A owns this file. Foundation ships working CRUD plus a baseline
natural-language planning endpoint; A should deepen the AI planning, time-slot
placement, conflict handling, and pattern-aware warnings.
"""
from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.auth import get_current_user
from app.database import get_session
from app.models import CalendarBlock, User
from app.schemas import BlockCreate, BlockRead, BlockUpdate, PlanRequest, PlanResponse
from app.services.planning import plan_day

router = APIRouter(prefix="/api/blocks", tags=["calendar"])


def _naive(dt: datetime) -> datetime:
    """Drop tzinfo so naive (SQLite-stored) and aware datetimes compare cleanly."""
    return dt.replace(tzinfo=None) if dt.tzinfo is not None else dt


@router.get("", response_model=list[BlockRead])
def list_blocks(
    start: datetime | None = None,
    end: datetime | None = None,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[CalendarBlock]:
    stmt = select(CalendarBlock).where(CalendarBlock.user_id == user.id)
    if start is not None:
        stmt = stmt.where(CalendarBlock.start >= start)
    if end is not None:
        stmt = stmt.where(CalendarBlock.start < end)
    return list(session.exec(stmt.order_by(CalendarBlock.start)).all())


@router.post("", response_model=BlockRead, status_code=201)
def create_block(
    body: BlockCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> CalendarBlock:
    if body.end <= body.start:
        raise HTTPException(422, "Block end must be after start")
    block = CalendarBlock(user_id=user.id, **body.model_dump())
    session.add(block)
    session.commit()
    session.refresh(block)
    return block


@router.get("/{block_id}", response_model=BlockRead)
def get_block(
    block_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> CalendarBlock:
    block = session.get(CalendarBlock, block_id)
    if block is None or block.user_id != user.id:
        raise HTTPException(404, "Block not found")
    return block


@router.patch("/{block_id}", response_model=BlockRead)
def update_block(
    block_id: int,
    body: BlockUpdate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> CalendarBlock:
    block = session.get(CalendarBlock, block_id)
    if block is None or block.user_id != user.id:
        raise HTTPException(404, "Block not found")
    updates = body.model_dump(exclude_unset=True)
    new_start = updates.get("start", block.start)
    new_end = updates.get("end", block.end)
    if _naive(new_end) <= _naive(new_start):
        raise HTTPException(422, "Block end must be after start")
    for field, value in updates.items():
        setattr(block, field, value)
    session.add(block)
    session.commit()
    session.refresh(block)
    return block


@router.delete("/{block_id}", status_code=204)
def delete_block(
    block_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> None:
    block = session.get(CalendarBlock, block_id)
    if block is None or block.user_id != user.id:
        raise HTTPException(404, "Block not found")
    session.delete(block)
    session.commit()


@router.post("/plan", response_model=PlanResponse)
def plan(
    body: PlanRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> PlanResponse:
    """Turn natural-language intentions into concrete, well-placed calendar blocks.

    Delegates planning (AI parsing, gap-aware time placement that avoids existing
    blocks, concreteness nudges, and pattern-aware warnings) to
    :func:`app.services.planning.plan_day`.
    """
    return plan_day(session, user, body)
