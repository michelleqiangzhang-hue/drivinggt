"""Goal endpoints — what the honest coach holds you to."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlmodel import Session, select

from app.auth import get_current_user
from app.database import get_session
from app.models import Goal, User
from app.schemas import GoalCreate, GoalRead

router = APIRouter(prefix="/api/goals", tags=["goals"])


@router.get("", response_model=list[GoalRead])
def list_goals(
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> list[Goal]:
    return list(session.exec(select(Goal).where(Goal.user_id == user.id)).all())


@router.post("", response_model=GoalRead, status_code=201)
def create_goal(
    body: GoalCreate,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> Goal:
    goal = Goal(user_id=user.id, **body.model_dump())
    session.add(goal)
    session.commit()
    session.refresh(goal)
    return goal


@router.delete("/{goal_id}", status_code=204)
def delete_goal(
    goal_id: int,
    session: Session = Depends(get_session),
    user: User = Depends(get_current_user),
) -> None:
    goal = session.get(Goal, goal_id)
    if goal is None or goal.user_id != user.id:
        raise HTTPException(404, "Goal not found")
    session.delete(goal)
    session.commit()
