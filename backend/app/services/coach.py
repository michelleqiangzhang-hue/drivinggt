"""Service layer for the AI coach — builds rich context and delegates to LLM.

Owns all business logic for the honest accountability coach and the
"ask AI about your life" Q&A. The router is a thin HTTP shell around these
functions.
"""
from __future__ import annotations

from sqlmodel import Session, select

from app.ai import llm_chat
from app.ai.prompts import COACH_SYSTEM
from app.models import (
    AccountabilityLog,
    BlockStatus,
    CalendarBlock,
    CoachMessage,
    Conversation,
    Goal,
    User,
    UserPattern,
)


def build_context(session: Session, user: User) -> str:
    """Build a rich context string from the user's recent data.

    Includes:
    - recent blocks with status (plan vs reality)
    - recent accountability logs
    - active goals
    - learned behavioral patterns
    - aggregate stats (planned vs actual minutes this week)
    """
    lines: list[str] = [f"User: {user.name}"]

    # --- Recent blocks (intention) with status ---
    blocks = list(
        session.exec(
            select(CalendarBlock)
            .where(CalendarBlock.user_id == user.id)
            .order_by(CalendarBlock.start.desc())
            .limit(15)
        ).all()
    )
    if blocks:
        lines.append("\nRecent planned blocks (plan vs reality):")
        for b in blocks:
            status_tag = b.status.value
            lines.append(
                f"- {b.title} ({b.category}, {b.planned_minutes}m) [{status_tag}]"
            )

    # --- Recent accountability logs ---
    logs = list(
        session.exec(
            select(AccountabilityLog)
            .where(AccountabilityLog.user_id == user.id)
            .order_by(AccountabilityLog.created_at.desc())
            .limit(15)
        ).all()
    )
    if logs:
        lines.append("\nRecent accountability logs (what actually happened):")
        for log in logs:
            actual = f", {log.actual_minutes}m actual" if log.actual_minutes else ""
            productive_tag = "productive" if log.productive else "unproductive"
            reason_tag = f" — reason: {log.reason}" if log.reason else ""
            lines.append(
                f"- {log.what_happened} ({log.category}, {productive_tag}{actual}){reason_tag}"
            )

    # --- Active goals ---
    goals = list(
        session.exec(
            select(Goal)
            .where(Goal.user_id == user.id, Goal.achieved.is_(None))  # type: ignore[arg-type]
        ).all()
    )
    if goals:
        lines.append("\nActive goals the coach should hold the user to:")
        for g in goals:
            cat = f" [{g.target_category}]" if g.target_category else ""
            lines.append(f"- {g.title} (horizon: {g.horizon}){cat}")

    # --- Learned patterns ---
    patterns = list(
        session.exec(
            select(UserPattern).where(UserPattern.user_id == user.id)
        ).all()
    )
    if patterns:
        lines.append("\nLearned behavioral patterns:")
        for p in patterns:
            lines.append(f"- {p.summary} (confidence: {p.confidence}, n={p.sample_size})")

    # --- Aggregate stats ---
    if blocks:
        total_planned = sum(b.planned_minutes for b in blocks)
        completed_blocks = [b for b in blocks if b.status == BlockStatus.completed]
        missed_blocks = [b for b in blocks if b.status == BlockStatus.missed]
        total_actual = sum(
            lg.actual_minutes for lg in logs if lg.actual_minutes is not None
        )
        lines.append(
            f"\nAggregate (recent): {total_planned}m planned, {total_actual}m actually logged, "
            f"{len(completed_blocks)} completed, {len(missed_blocks)} missed out of {len(blocks)} blocks."
        )

    return "\n".join(lines)


def get_or_create_conversation(
    session: Session, user: User, conversation_id: int | None
) -> Conversation:
    """Return an existing conversation or create a new one."""
    if conversation_id is not None:
        conv = session.get(Conversation, conversation_id)
        if conv is None or conv.user_id != user.id:
            return None  # type: ignore[return-value]
        return conv
    conv = Conversation(user_id=user.id)
    session.add(conv)
    session.commit()
    session.refresh(conv)
    return conv


def get_conversation_history(session: Session, conversation_id: int) -> list[CoachMessage]:
    """Load all messages in a conversation, ordered by creation time."""
    return list(
        session.exec(
            select(CoachMessage)
            .where(CoachMessage.conversation_id == conversation_id)
            .order_by(CoachMessage.created_at)
        ).all()
    )


def generate_reply(
    session: Session,
    user: User,
    conversation: Conversation,
    user_message: str,
    history: list[CoachMessage],
) -> str:
    """Persist the user message, call the LLM, persist and return the reply."""
    user_msg = CoachMessage(
        conversation_id=conversation.id, role="user", content=user_message
    )
    session.add(user_msg)

    context = build_context(session, user)

    llm_messages: list[dict[str, str]] = [
        {"role": "system", "content": COACH_SYSTEM},
        {"role": "system", "content": "Context about the user:\n" + context},
    ]
    llm_messages += [{"role": m.role, "content": m.content} for m in history]
    llm_messages.append({"role": "user", "content": user_message})

    reply_text = llm_chat(llm_messages)

    assistant_msg = CoachMessage(
        conversation_id=conversation.id, role="assistant", content=reply_text
    )
    session.add(assistant_msg)
    session.commit()

    return reply_text
