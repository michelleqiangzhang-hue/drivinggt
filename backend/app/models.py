"""SQLModel database models — the persisted Bogi domain.

Core idea:
- CalendarBlock  = INTENTION (what you said you'd do)
- AccountabilityLog = REALITY (what you actually did)
- The gap between them is the product.
"""
from datetime import datetime, timezone
from enum import Enum
from typing import Optional

from sqlmodel import Field, Relationship, SQLModel


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class BlockStatus(str, Enum):
    planned = "planned"          # in the future, not yet checked
    completed = "completed"      # user did what they planned
    partial = "partial"         # did some of it
    missed = "missed"           # did not do it
    unlogged = "unlogged"       # block ended, not yet accounted for


class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(index=True, unique=True)
    name: str = "You"
    hashed_password: str | None = None
    created_at: datetime = Field(default_factory=utcnow)

    blocks: list["CalendarBlock"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    logs: list["AccountabilityLog"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    goals: list["Goal"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )
    patterns: list["UserPattern"] = Relationship(
        back_populates="user", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class CalendarBlock(SQLModel, table=True):
    """A planned block of time = the user's INTENTION."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str
    category: str = "Uncategorized"
    subcategory: str | None = None
    notes: str | None = None
    start: datetime = Field(index=True)
    end: datetime
    status: BlockStatus = Field(default=BlockStatus.planned)
    created_at: datetime = Field(default_factory=utcnow)

    user: Optional["User"] = Relationship(back_populates="blocks")
    log: Optional["AccountabilityLog"] = Relationship(
        back_populates="block", sa_relationship_kwargs={"uselist": False}
    )

    @property
    def planned_minutes(self) -> int:
        return int((self.end - self.start).total_seconds() // 60)


class AccountabilityLog(SQLModel, table=True):
    """What ACTUALLY happened in a block (or in blank time)."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    block_id: int | None = Field(default=None, foreign_key="calendarblock.id", index=True)

    # Reality
    what_happened: str
    category: str = "Uncategorized"
    subcategory: str | None = None
    description: str | None = None  # the "sub-sub" detail
    productive: bool = True
    actual_minutes: int | None = None
    reason: str | None = None  # why it differed from the plan

    # For standalone "where did my time go" logs (no block)
    start: datetime | None = Field(default=None, index=True)
    end: datetime | None = None

    created_at: datetime = Field(default_factory=utcnow)

    user: Optional["User"] = Relationship(back_populates="logs")
    block: Optional["CalendarBlock"] = Relationship(back_populates="log")


class Goal(SQLModel, table=True):
    """A goal the honest coach can hold you to (week/month/year)."""

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str
    horizon: str = "month"  # week | month | year
    target_category: str | None = None
    created_at: datetime = Field(default_factory=utcnow)
    achieved: bool | None = None

    user: Optional["User"] = Relationship(back_populates="goals")


class UserPattern(SQLModel, table=True):
    """BETA: learned behavioral pattern used to adjust future planning.

    Example: "Repeatedly fails to complete 3h editing blocks."
    """

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    category: str | None = None
    summary: str
    confidence: float = 0.5  # 0..1
    sample_size: int = 0
    suggestion: str | None = None
    updated_at: datetime = Field(default_factory=utcnow)

    user: Optional["User"] = Relationship(back_populates="patterns")


class Conversation(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    title: str = "Chat with Bogi"
    created_at: datetime = Field(default_factory=utcnow)

    messages: list["CoachMessage"] = Relationship(
        back_populates="conversation", sa_relationship_kwargs={"cascade": "all, delete-orphan"}
    )


class CoachMessage(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    conversation_id: int = Field(foreign_key="conversation.id", index=True)
    role: str  # "user" | "assistant" | "system"
    content: str
    created_at: datetime = Field(default_factory=utcnow)

    conversation: Optional["Conversation"] = Relationship(back_populates="messages")
