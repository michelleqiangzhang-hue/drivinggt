"""Calendar / planning endpoints — the user's INTENTION.

WORKSTREAM A owns this file. Foundation ships working CRUD plus a baseline
natural-language planning endpoint; A should deepen the AI planning, time-slot
placement, conflict handling, and pattern-aware warnings.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.ai import llm_json
from app.ai.prompts import PLANNER_SYSTEM
from app.auth import get_current_user
from app.database import get_session
from app.models import BlockStatus, CalendarBlock, User
from app.schemas import BlockCreate, BlockRead, BlockUpdate, PlanRequest, PlanResponse

router = APIRouter(prefix="/api/blocks", tags=["calendar"])


def _day_bounds(day: datetime) -> tuple[datetime, datetime]:
    start = datetime.combine(day.date(), time.min, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


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
    for field, value in body.model_dump(exclude_unset=True).items():
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
def plan_day(
    body: PlanRequest,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> PlanResponse:
    """Turn natural-language intentions into concrete calendar blocks.

    Baseline implementation places blocks sequentially starting at 09:00.
    WORKSTREAM A: improve time placement, respect existing blocks, and add
    pattern-aware warnings (e.g. "you usually don't finish 3h editing blocks").
    """
    day = body.date or datetime.now(timezone.utc)
    cursor = datetime.combine(day.date(), time(9, 0), tzinfo=timezone.utc)

    result = llm_json(
        [
            {"role": "system", "content": PLANNER_SYSTEM},
            {"role": "user", "content": body.text},
        ]
    )

    created: list[CalendarBlock] = []
    for spec in result.get("blocks", []):
        minutes = int(spec.get("minutes", 60))
        block = CalendarBlock(
            user_id=user.id,
            title=spec.get("title", "Untitled block"),
            category=spec.get("category", "Work"),
            start=cursor,
            end=cursor + timedelta(minutes=minutes),
            status=BlockStatus.planned,
        )
        cursor = block.end
        session.add(block)
        created.append(block)
    session.commit()
    for b in created:
        session.refresh(b)

    return PlanResponse(
        blocks=[BlockRead.model_validate(b) for b in created],
        message=result.get("message", "Planned your day into concrete blocks."),
        pattern_warnings=[],
    )
