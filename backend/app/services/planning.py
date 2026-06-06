"""AI day-planning service — turns natural-language intentions into blocks.

WORKSTREAM A owns this module. The calendar router delegates the heavy lifting of
``POST /api/blocks/plan`` here so the endpoint stays a thin HTTP shell.

Responsibilities:
- Parse the user's free text into concrete ``{title, minutes, category, start_hint}``
  specs via :func:`app.ai.llm_json` with the ``PLANNER_SYSTEM`` prompt. When the
  model output is degenerate (the deterministic mock used in tests/CI cannot split
  multi-task text or read plural units), repair it with a local parser so the app
  produces useful, checkable blocks with NO API key.
- Place each block in an open gap on the requested day, never overlapping the
  user's EXISTING blocks or other freshly-planned blocks. Honor ``start_hint``
  (HH:MM) when present, otherwise pack sequentially from 09:00.
- Nudge vague intentions ("be productive") toward concrete, checkable blocks.
- Surface pattern-aware warnings by reading (never writing) ``UserPattern`` rows.
"""
from __future__ import annotations

import re
from datetime import datetime, time, timedelta, timezone
from typing import Any

from sqlmodel import Session, select

from app.ai import llm_json
from app.ai.prompts import PLANNER_SYSTEM
from app.models import BlockStatus, CalendarBlock, User, UserPattern
from app.schemas import BlockRead, PlanRequest, PlanResponse

DEFAULT_MINUTES = 60
DEFAULT_CATEGORY = "Work"
DAY_START = time(9, 0)

# Detects an explicit duration like "for 2 hours" / "for 30 min" in the raw text.
_DURATION_RE = re.compile(r"\bfor\s+\d", re.IGNORECASE)
# Pulls a whole-number percentage out of a pattern summary, e.g. "only 33%".
_PERCENT_RE = re.compile(r"(\d{1,3})\s*%")
# "<title> for <n> <unit>" — handles singular AND plural units the mock misses.
_INTENTION_RE = re.compile(
    r"(?P<title>[a-zA-Z][\w '\-]*?)\s+for\s+(?P<num>\d+(?:\.\d+)?)\s*"
    r"(?P<unit>hours?|hrs?|h|minutes?|mins?|m)\b",
    re.IGNORECASE,
)
# Optional "at HH:MM" time hint within a clause.
_AT_HINT_RE = re.compile(r"\bat\s+(\d{1,2}):(\d{2})\b", re.IGNORECASE)

_CATEGORY_KEYWORDS: dict[str, tuple[str, ...]] = {
    "Work": ("edit", "email", "code", "build", "write", "record", "meeting", "call",
             "design", "client"),
    "Study": ("study", "lesson", "read", "homework", "lecture", "revise", "learn"),
    "Health": ("gym", "run", "workout", "walk", "exercise", "yoga", "meditate"),
    "Social": ("friend", "family", "hang", "dinner", "party", "date"),
    "Chores": ("laundry", "clean", "cook", "shop", "groceries", "vacuum", "errand"),
    "Rest": ("rest", "nap", "relax", "break"),
}


def _as_utc(dt: datetime) -> datetime:
    """Normalize a datetime to tz-aware UTC (SQLite returns naive datetimes)."""
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _day_bounds(day: datetime) -> tuple[datetime, datetime]:
    start = datetime.combine(day.date(), time.min, tzinfo=timezone.utc)
    return start, start + timedelta(days=1)


def _guess_category(title: str) -> str:
    lowered = title.lower()
    for category, words in _CATEGORY_KEYWORDS.items():
        if any(w in lowered for w in words):
            return category
    return DEFAULT_CATEGORY


def _unit_to_minutes(num: float, unit: str) -> int:
    return int(num * 60) if unit.lower().startswith("h") else int(num)


def _parse_hint(start_hint: object, day: datetime) -> datetime | None:
    """Parse an "HH:MM" hint into a tz-aware datetime on ``day`` (or None)."""
    if not isinstance(start_hint, str):
        return None
    match = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", start_hint)
    if not match:
        return None
    hour, minute = int(match.group(1)), int(match.group(2))
    if not (0 <= hour < 24 and 0 <= minute < 60):
        return None
    return datetime.combine(day.date(), time(hour, minute), tzinfo=timezone.utc)


def _local_parse(text: str) -> list[dict[str, Any]]:
    """Deterministically split free text into block specs with explicit durations."""
    specs: list[dict[str, Any]] = []
    for match in _INTENTION_RE.finditer(text):
        raw_title = match.group("title").strip()
        # Drop leading conjunctions left over from clause boundaries.
        raw_title = re.sub(r"^(?:and|then|also|plus)\s+", "", raw_title, flags=re.I)
        title = raw_title.capitalize() if raw_title else "Untitled block"
        minutes = _unit_to_minutes(float(match.group("num")), match.group("unit"))

        clause = text[match.start():]
        end = clause.find(" and ")
        hint_match = _AT_HINT_RE.search(clause if end == -1 else clause[:end])
        start_hint = (
            f"{int(hint_match.group(1)):02d}:{int(hint_match.group(2)):02d}"
            if hint_match
            else None
        )
        specs.append(
            {
                "title": title,
                "minutes": max(1, minutes),
                "category": _guess_category(title),
                "start_hint": start_hint,
            }
        )
    return specs


def _spec_is_degenerate(spec: dict[str, Any]) -> bool:
    """A spec is degenerate if its title still embeds an unparsed duration phrase."""
    return bool(_DURATION_RE.search(str(spec.get("title", ""))))


def _resolve_specs(result: dict[str, Any], text: str) -> list[dict[str, Any]]:
    """Prefer the model's specs, repairing with a local parse when they fall short."""
    specs = result.get("blocks") or []
    local = _local_parse(text)
    if local and (len(local) > len(specs) or any(_spec_is_degenerate(s) for s in specs)):
        return local
    return list(specs)


def _find_slot(
    occupied: list[tuple[datetime, datetime]],
    candidate: datetime,
    minutes: int,
) -> datetime:
    """Earliest start >= ``candidate`` where a ``minutes``-long block fits.

    Walks forward past any occupied interval it would overlap, so blocks land in
    open gaps between the user's existing commitments.
    """
    duration = timedelta(minutes=minutes)
    ordered = sorted(occupied)
    start = candidate
    moved = True
    while moved:
        moved = False
        for busy_start, busy_end in ordered:
            # Overlap test for [start, start + duration) vs [busy_start, busy_end)
            if start < busy_end and busy_start < start + duration:
                start = busy_end
                moved = True
    return start


def _build_warning(pattern: UserPattern) -> str:
    """Render a pattern row into a concrete, actionable planning warning."""
    category = pattern.category or "these"
    match = _PERCENT_RE.search(pattern.summary or "")
    if match:
        return (
            f"You usually only finish {match.group(1)}% of your '{category}' "
            "blocks — consider a shorter block."
        )
    if pattern.suggestion:
        return f"{pattern.summary} {pattern.suggestion}".strip()
    return pattern.summary


def _pattern_warnings(
    session: Session, user: User, blocks: list[CalendarBlock]
) -> list[str]:
    """Warn for any planned category that matches a known failed pattern."""
    patterns = list(
        session.exec(select(UserPattern).where(UserPattern.user_id == user.id)).all()
    )
    by_cat: dict[str, UserPattern] = {}
    for p in patterns:
        if p.category and p.category not in by_cat:
            by_cat[p.category] = p

    warnings: list[str] = []
    seen: set[str] = set()
    for block in blocks:
        pattern = by_cat.get(block.category)
        if pattern is not None and block.category not in seen:
            warnings.append(_build_warning(pattern))
            seen.add(block.category)
    return warnings


def plan_day(session: Session, user: User, body: PlanRequest) -> PlanResponse:
    """Convert natural-language intentions into concrete, placed calendar blocks."""
    day = body.date or datetime.now(timezone.utc)

    result = llm_json(
        [
            {"role": "system", "content": PLANNER_SYSTEM},
            {"role": "user", "content": body.text},
        ]
    )
    specs = _resolve_specs(result, body.text or "")

    # Seed occupied intervals with the user's existing blocks for that day so new
    # blocks never overlap prior commitments.
    day_start, day_end = _day_bounds(day)
    existing = list(
        session.exec(
            select(CalendarBlock)
            .where(CalendarBlock.user_id == user.id)
            .where(CalendarBlock.start >= day_start)
            .where(CalendarBlock.start < day_end)
        ).all()
    )
    occupied: list[tuple[datetime, datetime]] = [
        (_as_utc(b.start), _as_utc(b.end)) for b in existing
    ]

    pack_cursor = datetime.combine(day.date(), DAY_START, tzinfo=timezone.utc)
    created: list[CalendarBlock] = []
    for spec in specs:
        try:
            minutes = int(spec.get("minutes", DEFAULT_MINUTES))
        except (TypeError, ValueError):
            minutes = DEFAULT_MINUTES
        minutes = max(1, minutes)

        hint = _parse_hint(spec.get("start_hint"), day)
        candidate = hint if hint is not None else pack_cursor
        start = _find_slot(occupied, candidate, minutes)
        end = start + timedelta(minutes=minutes)

        block = CalendarBlock(
            user_id=user.id,
            title=spec.get("title") or "Untitled block",
            category=spec.get("category") or DEFAULT_CATEGORY,
            start=start,
            end=end,
            status=BlockStatus.planned,
        )
        session.add(block)
        created.append(block)

        occupied.append((start, end))
        # Sequential packing continues from the latest placed block.
        pack_cursor = max(pack_cursor, end)

    session.commit()
    for b in created:
        session.refresh(b)

    message = result.get("message") or "Planned your day into concrete blocks."
    if not _DURATION_RE.search(body.text or ""):
        message = (
            f"{message} Tip: vague goals can't be checked — name a concrete, "
            "timed block like 'edit videos for 1 hour' so we can hold you to it."
        )

    return PlanResponse(
        blocks=[BlockRead.model_validate(b) for b in created],
        message=message,
        pattern_warnings=_pattern_warnings(session, user, created),
    )
