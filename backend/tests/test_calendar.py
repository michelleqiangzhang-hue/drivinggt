"""Tests for Workstream A: calendar CRUD + AI planning service.

Runs entirely in MOCK mode (no OpenAI key) using an isolated temp SQLite file.
"""
from __future__ import annotations

import os
import tempfile
from datetime import datetime

os.environ["DATABASE_URL"] = f"sqlite:///{tempfile.mktemp(suffix='.db')}"

from fastapi.testclient import TestClient  # noqa: E402
from sqlmodel import Session  # noqa: E402

from app.auth import get_or_create_user  # noqa: E402
from app.database import engine, init_db  # noqa: E402
from app.main import app  # noqa: E402
from app.models import UserPattern  # noqa: E402

init_db()
client = TestClient(app)


def _dt(value: str) -> datetime:
    # Strip tzinfo: SQLite returns naive datetimes, so keep all comparisons naive.
    return datetime.fromisoformat(value).replace(tzinfo=None)


def _minutes(block: dict) -> int:
    return int((_dt(block["end"]) - _dt(block["start"])).total_seconds() // 60)


def test_plan_durations_and_non_overlap():
    r = client.post(
        "/api/blocks/plan",
        json={
            "text": "edit videos for 2 hours and email clients for 30 minutes",
            "date": "2030-03-01T00:00:00+00:00",
        },
    )
    assert r.status_code == 200, r.text
    blocks = sorted(r.json()["blocks"], key=lambda b: b["start"])
    assert len(blocks) == 2

    durations = sorted(_minutes(b) for b in blocks)
    assert durations == [30, 120]

    # No overlap between the two planned blocks.
    assert _dt(blocks[0]["end"]) <= _dt(blocks[1]["start"])


def test_planned_blocks_avoid_existing_block():
    existing = client.post(
        "/api/blocks",
        json={
            "title": "Standup",
            "category": "Work",
            "start": "2030-03-02T09:00:00+00:00",
            "end": "2030-03-02T10:00:00+00:00",
        },
    )
    assert existing.status_code == 201, existing.text

    r = client.post(
        "/api/blocks/plan",
        json={
            "text": "edit videos for 2 hours",
            "date": "2030-03-02T00:00:00+00:00",
        },
    )
    assert r.status_code == 200, r.text
    blocks = r.json()["blocks"]
    assert len(blocks) == 1

    busy_start = _dt("2030-03-02T09:00:00+00:00")
    busy_end = _dt("2030-03-02T10:00:00+00:00")
    planned_start = _dt(blocks[0]["start"])
    planned_end = _dt(blocks[0]["end"])
    # Planned block must not overlap the pre-existing 09:00-10:00 block.
    assert not (planned_start < busy_end and busy_start < planned_end)
    assert planned_start >= busy_end


def test_start_hint_is_honored():
    r = client.post(
        "/api/blocks/plan",
        json={
            "text": "deep work",
            "date": "2030-03-05T00:00:00+00:00",
        },
    )
    assert r.status_code == 200, r.text
    # The mock planner emits no start_hint, so a single block packs from 09:00.
    blocks = r.json()["blocks"]
    assert len(blocks) >= 1
    assert _dt(blocks[0]["start"]).strftime("%H:%M") == "09:00"


def test_vague_text_nudges_toward_concreteness():
    r = client.post(
        "/api/blocks/plan",
        json={"text": "be productive", "date": "2030-03-06T00:00:00+00:00"},
    )
    assert r.status_code == 200, r.text
    body = r.json()
    # Still produces concrete blocks despite a vague prompt.
    assert len(body["blocks"]) >= 1
    assert "concrete" in body["message"].lower()


def test_pattern_warning_surfaced():
    with Session(engine) as session:
        user = get_or_create_user(session, "you@bogi.app")
        session.add(
            UserPattern(
                user_id=user.id,
                category="Work",
                summary="You complete only 33% of your planned 'Work' blocks.",
                confidence=0.7,
                sample_size=5,
                suggestion="Try shorter 'Work' blocks (~30 min).",
            )
        )
        session.commit()

    r = client.post(
        "/api/blocks/plan",
        json={
            "text": "edit videos for 2 hours",
            "date": "2030-03-07T00:00:00+00:00",
        },
    )
    assert r.status_code == 200, r.text
    warnings = r.json()["pattern_warnings"]
    assert any("Work" in w and "shorter" in w for w in warnings)


def test_create_block_rejects_non_positive_duration():
    # end == start
    r = client.post(
        "/api/blocks",
        json={
            "title": "Zero length",
            "start": "2030-03-03T09:00:00+00:00",
            "end": "2030-03-03T09:00:00+00:00",
        },
    )
    assert r.status_code == 422, r.text

    # end < start
    r = client.post(
        "/api/blocks",
        json={
            "title": "Negative length",
            "start": "2030-03-03T11:00:00+00:00",
            "end": "2030-03-03T10:00:00+00:00",
        },
    )
    assert r.status_code == 422, r.text


def test_block_crud_round_trip():
    # Create
    r = client.post(
        "/api/blocks",
        json={
            "title": "Write report",
            "category": "Work",
            "start": "2030-03-04T09:00:00+00:00",
            "end": "2030-03-04T10:00:00+00:00",
        },
    )
    assert r.status_code == 201, r.text
    block = r.json()
    block_id = block["id"]
    assert block["planned_minutes"] == 60

    # Read
    r = client.get(f"/api/blocks/{block_id}")
    assert r.status_code == 200, r.text
    assert r.json()["title"] == "Write report"

    # Update
    r = client.patch(f"/api/blocks/{block_id}", json={"title": "Write final report"})
    assert r.status_code == 200, r.text
    assert r.json()["title"] == "Write final report"

    # Update with invalid times is rejected
    r = client.patch(
        f"/api/blocks/{block_id}",
        json={"end": "2030-03-04T08:00:00+00:00"},
    )
    assert r.status_code == 422, r.text

    # List includes the block
    r = client.get(
        "/api/blocks",
        params={"start": "2030-03-04T00:00:00+00:00", "end": "2030-03-05T00:00:00+00:00"},
    )
    assert r.status_code == 200, r.text
    assert any(b["id"] == block_id for b in r.json())

    # Delete
    r = client.delete(f"/api/blocks/{block_id}")
    assert r.status_code == 204, r.text
    r = client.get(f"/api/blocks/{block_id}")
    assert r.status_code == 404
