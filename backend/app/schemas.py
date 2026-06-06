"""Pydantic API schemas — the shared contract between backend and frontend.

These define the stable request/response shapes every workstream builds against.
Keep these in sync with frontend/src/api/types.ts.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.models import BlockStatus


class ORMModel(BaseModel):
    """Base for response models read directly from SQLModel/ORM objects."""

    model_config = ConfigDict(from_attributes=True)

# --------------------------------------------------------------------------- #
# Auth
# --------------------------------------------------------------------------- #


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"


class UserRead(ORMModel):
    id: int
    email: str
    name: str


class LoginRequest(BaseModel):
    email: str
    password: str | None = None


# --------------------------------------------------------------------------- #
# Calendar blocks (INTENTION)
# --------------------------------------------------------------------------- #


class BlockCreate(BaseModel):
    title: str
    category: str = "Uncategorized"
    subcategory: str | None = None
    notes: str | None = None
    start: datetime
    end: datetime


class BlockUpdate(BaseModel):
    title: str | None = None
    category: str | None = None
    subcategory: str | None = None
    notes: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    status: BlockStatus | None = None


class BlockRead(ORMModel):
    id: int
    title: str
    category: str
    subcategory: str | None = None
    notes: str | None = None
    start: datetime
    end: datetime
    status: BlockStatus
    planned_minutes: int
    log: "LogRead | None" = None


# --------------------------------------------------------------------------- #
# Accountability logs (REALITY)
# --------------------------------------------------------------------------- #


class LogCreate(BaseModel):
    block_id: int | None = None
    what_happened: str
    category: str = "Uncategorized"
    subcategory: str | None = None
    description: str | None = None
    productive: bool = True
    actual_minutes: int | None = None
    reason: str | None = None
    start: datetime | None = None
    end: datetime | None = None


class LogRead(ORMModel):
    id: int
    block_id: int | None = None
    what_happened: str
    category: str
    subcategory: str | None = None
    description: str | None = None
    productive: bool
    actual_minutes: int | None = None
    reason: str | None = None
    start: datetime | None = None
    end: datetime | None = None
    created_at: datetime


# --------------------------------------------------------------------------- #
# AI planning (natural language -> blocks)
# --------------------------------------------------------------------------- #


class PlanRequest(BaseModel):
    text: str
    date: datetime | None = None  # the day being planned


class PlanResponse(BaseModel):
    blocks: list[BlockRead]
    message: str  # coach's reply about the plan
    pattern_warnings: list[str] = []


# --------------------------------------------------------------------------- #
# Coach chat
# --------------------------------------------------------------------------- #


class ChatMessage(BaseModel):
    role: str
    content: str


class ChatRequest(BaseModel):
    conversation_id: int | None = None
    message: str


class ChatResponse(BaseModel):
    conversation_id: int
    reply: str
    history: list[ChatMessage] = []


# --------------------------------------------------------------------------- #
# Data bank / analytics
# --------------------------------------------------------------------------- #


class CategoryTotal(BaseModel):
    category: str
    minutes: int


class GapSummary(BaseModel):
    """Plan vs reality for a time window."""

    period: str  # day | week | month | year
    start: datetime
    end: datetime
    planned_minutes: int
    logged_minutes: int
    productive_minutes: int
    unproductive_minutes: int
    completed_blocks: int
    partial_blocks: int
    missed_blocks: int
    unlogged_blocks: int
    adherence_rate: float  # 0..1: how much of the plan was actually done
    planned_by_category: list[CategoryTotal] = []
    actual_by_category: list[CategoryTotal] = []


# --------------------------------------------------------------------------- #
# Patterns (BETA)
# --------------------------------------------------------------------------- #


class PatternRead(ORMModel):
    id: int
    category: str | None = None
    summary: str
    confidence: float
    sample_size: int
    suggestion: str | None = None
    updated_at: datetime


# --------------------------------------------------------------------------- #
# Goals
# --------------------------------------------------------------------------- #


class GoalCreate(BaseModel):
    title: str
    horizon: str = "month"
    target_category: str | None = None


class GoalRead(ORMModel):
    id: int
    title: str
    horizon: str
    target_category: str | None = None
    achieved: bool | None = None


BlockRead.model_rebuild()
