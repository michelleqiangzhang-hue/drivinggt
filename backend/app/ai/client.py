"""LLM client wrapper.

Provides two entry points used across the app:
- ``llm_chat(messages)`` -> free-text reply (string)
- ``llm_json(messages, schema_hint)`` -> parsed JSON object (dict)

If no ``OPENAI_API_KEY`` is configured, both fall back to a deterministic mock so
the entire product is usable in demo mode without any external dependency.
"""
from __future__ import annotations

import json
import re
from typing import Any

from app.config import settings


class AIClient:
    def __init__(self) -> None:
        self._client = None
        self.enabled = settings.ai_enabled
        if self.enabled:
            try:
                from openai import OpenAI

                self._client = OpenAI(api_key=settings.openai_api_key)
            except Exception:
                # If the SDK fails to initialise, degrade gracefully to mock mode.
                self.enabled = False

    def chat(self, messages: list[dict[str, str]], temperature: float = 0.6) -> str:
        if not self.enabled or self._client is None:
            return _mock_reply(messages)
        try:
            resp = self._client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                temperature=temperature,
            )
            return (resp.choices[0].message.content or "").strip()
        except Exception:
            return _mock_reply(messages)

    def json(
        self, messages: list[dict[str, str]], temperature: float = 0.2
    ) -> dict[str, Any]:
        if not self.enabled or self._client is None:
            return _mock_json(messages)
        try:
            resp = self._client.chat.completions.create(
                model=settings.openai_model,
                messages=messages,
                temperature=temperature,
                response_format={"type": "json_object"},
            )
            content = resp.choices[0].message.content or "{}"
            return json.loads(content)
        except Exception:
            return _mock_json(messages)


# --------------------------------------------------------------------------- #
# Deterministic mock fallback
# --------------------------------------------------------------------------- #


def _last_user_text(messages: list[dict[str, str]]) -> str:
    for m in reversed(messages):
        if m.get("role") == "user":
            return m.get("content", "")
    return ""


def _mock_reply(messages: list[dict[str, str]]) -> str:
    text = _last_user_text(messages).lower()
    if not text:
        return "I'm here. Tell me what you planned and what actually happened."
    if any(w in text for w in ("plan", "schedule", "tomorrow", "today")):
        return (
            "[mock coach] Got it. I've turned that into concrete, checkable blocks. "
            "Remember: 'be productive' can't be checked — 'edit videos for 1 hour' can."
        )
    if any(w in text for w in ("did", "actually", "happened", "instead")):
        return (
            "[mock coach] Thanks for being honest. I've logged what actually happened. "
            "Awareness is the first step to improvement."
        )
    return (
        "[mock coach] I'm your accountability coach. I help you plan concrete blocks, "
        "then hold you to what you said you'd do. (Set OPENAI_API_KEY for the full coach.)"
    )


def _mock_json(messages: list[dict[str, str]]) -> dict[str, Any]:
    """Best-effort structured planning fallback.

    Parses simple patterns like 'edit videos for 2 hours' into block specs.
    """
    text = _last_user_text(messages)
    blocks: list[dict[str, Any]] = []
    pattern = re.compile(
        r"(?P<title>[a-zA-Z][\w \-]+?)\s+for\s+(?P<num>\d+(?:\.\d+)?)\s*(?P<unit>hour|hr|h|minute|min|m)\b",
        re.IGNORECASE,
    )
    for match in pattern.finditer(text):
        num = float(match.group("num"))
        unit = match.group("unit").lower()
        minutes = int(num * 60) if unit.startswith(("h",)) else int(num)
        title = match.group("title").strip().capitalize()
        blocks.append({"title": title, "minutes": minutes, "category": _guess_category(title)})
    if not blocks and text.strip():
        blocks.append({"title": text.strip()[:60], "minutes": 60, "category": "Work"})
    return {
        "blocks": blocks,
        "message": "[mock planner] Broke your day into concrete, checkable blocks.",
    }


def _guess_category(title: str) -> str:
    t = title.lower()
    mapping = {
        "Work": ["edit", "email", "code", "build", "write", "record", "meeting", "call", "design"],
        "Study": ["study", "lesson", "read", "homework", "lecture", "revise"],
        "Health": ["gym", "run", "workout", "walk", "exercise"],
        "Social": ["friend", "family", "hang", "dinner", "party"],
        "Chores": ["laundry", "clean", "cook", "shop", "groceries", "vacuum"],
    }
    for cat, words in mapping.items():
        if any(w in t for w in words):
            return cat
    return "Work"


ai_client = AIClient()


def llm_chat(messages: list[dict[str, str]], temperature: float = 0.6) -> str:
    return ai_client.chat(messages, temperature=temperature)


def llm_json(messages: list[dict[str, str]], temperature: float = 0.2) -> dict[str, Any]:
    return ai_client.json(messages, temperature=temperature)
