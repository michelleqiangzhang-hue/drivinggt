"""Seed demo data so Bogi is immediately explorable.

Idempotent: only seeds when the demo user has no blocks yet.
"""
from __future__ import annotations

from datetime import datetime, time, timedelta, timezone

from sqlmodel import Session, select

from app.auth import DEMO_EMAIL, get_or_create_user
from app.database import engine
from app.models import (
    AccountabilityLog,
    BlockStatus,
    CalendarBlock,
    Goal,
)


def seed_demo_data() -> None:
    with Session(engine) as session:
        user = get_or_create_user(session, DEMO_EMAIL, name="Håkan")
        existing = session.exec(
            select(CalendarBlock).where(CalendarBlock.user_id == user.id)
        ).first()
        if existing is not None:
            return

        today = datetime.now(timezone.utc)
        midnight = datetime.combine(today.date(), time.min, tzinfo=timezone.utc)

        def block(hour: int, minutes: int, title: str, category: str) -> CalendarBlock:
            start = midnight + timedelta(hours=hour)
            return CalendarBlock(
                user_id=user.id,
                title=title,
                category=category,
                start=start,
                end=start + timedelta(minutes=minutes),
                status=BlockStatus.planned,
            )

        b_record = block(9, 120, "Record podcast", "Work")
        b_edit = block(11, 180, "Edit videos", "Work")
        b_email = block(14, 60, "Email co-manufacturers", "Work")
        b_gym = block(17, 60, "Gym session", "Health")
        blocks = [b_record, b_edit, b_email, b_gym]
        for b in blocks:
            session.add(b)
        session.commit()
        for b in blocks:
            session.refresh(b)

        # Reality: the classic gap. Recording went fine; editing ran long; the email
        # hour evaporated into scrolling.
        b_record.status = BlockStatus.completed
        b_edit.status = BlockStatus.partial
        b_email.status = BlockStatus.missed
        for b in (b_record, b_edit, b_email):
            session.add(b)

        logs = [
            AccountabilityLog(
                user_id=user.id,
                block_id=b_record.id,
                what_happened="Recorded the full podcast episode",
                category="Work",
                subcategory="Recording",
                productive=True,
                actual_minutes=120,
            ),
            AccountabilityLog(
                user_id=user.id,
                block_id=b_edit.id,
                what_happened="Edited ~1h, then got distracted reorganizing the desk",
                category="Work",
                subcategory="Editing",
                description="Editing + tidying",
                productive=True,
                actual_minutes=90,
                reason="Easily distracted; the distractions felt productive",
            ),
            AccountabilityLog(
                user_id=user.id,
                block_id=b_email.id,
                what_happened="Opened phone 'for a second', scrolled instead of emailing",
                category="Social media",
                subcategory="Instagram",
                description="Doomscrolling",
                productive=False,
                actual_minutes=45,
                reason="Phone pickup spiralled",
            ),
        ]
        for log in logs:
            session.add(log)

        session.add(
            Goal(
                user_id=user.id,
                title="Ship the app this month",
                horizon="month",
                target_category="Work",
            )
        )
        session.commit()
