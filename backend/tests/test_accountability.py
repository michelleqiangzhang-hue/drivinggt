"""Tests for the accountability loop — status inference, blank-time logging, unaccounted blocks."""
from __future__ import annotations

import os
import tempfile

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mktemp(suffix='.db')}")

from fastapi.testclient import TestClient  # noqa: E402

from app.database import init_db  # noqa: E402
from app.main import app  # noqa: E402

init_db()
client = TestClient(app)


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def _create_block(
    title: str = "Work",
    category: str = "Work",
    start: str = "2025-06-01T09:00:00+00:00",
    end: str = "2025-06-01T11:00:00+00:00",
) -> dict:
    r = client.post(
        "/api/blocks",
        json={"title": title, "category": category, "start": start, "end": end},
    )
    assert r.status_code == 201, r.text
    return r.json()


def _create_log(**kwargs) -> dict:
    r = client.post("/api/logs", json=kwargs)
    assert r.status_code == 201, r.text
    return r.json()


def _get_block(block_id: int) -> dict:
    r = client.get(f"/api/blocks/{block_id}")
    assert r.status_code == 200, r.text
    return r.json()


# --------------------------------------------------------------------------- #
# Status inference
# --------------------------------------------------------------------------- #

class TestStatusInference:
    """Logging a block updates its status — completed/partial/missed."""

    def test_completed_same_category_full_time(self):
        block = _create_block(category="Study", start="2025-06-02T08:00:00+00:00", end="2025-06-02T10:00:00+00:00")
        _create_log(
            block_id=block["id"],
            what_happened="Read textbook",
            category="Study",
            productive=True,
            actual_minutes=120,
        )
        updated = _get_block(block["id"])
        assert updated["status"] == "completed"

    def test_completed_when_over_80_percent(self):
        block = _create_block(category="Work", start="2025-06-02T10:00:00+00:00", end="2025-06-02T12:00:00+00:00")
        _create_log(
            block_id=block["id"],
            what_happened="Coding",
            category="Work",
            productive=True,
            actual_minutes=100,  # 83% of 120 planned
        )
        updated = _get_block(block["id"])
        assert updated["status"] == "completed"

    def test_partial_same_category_moderate_time(self):
        block = _create_block(category="Exercise", start="2025-06-02T14:00:00+00:00", end="2025-06-02T16:00:00+00:00")
        _create_log(
            block_id=block["id"],
            what_happened="Short jog",
            category="Exercise",
            productive=True,
            actual_minutes=60,  # 50% of 120
        )
        updated = _get_block(block["id"])
        assert updated["status"] == "partial"

    def test_missed_different_category_unproductive(self):
        block = _create_block(category="Work", start="2025-06-03T09:00:00+00:00", end="2025-06-03T11:00:00+00:00")
        _create_log(
            block_id=block["id"],
            what_happened="Scrolled social media",
            category="Social media",
            productive=False,
            actual_minutes=30,
        )
        updated = _get_block(block["id"])
        assert updated["status"] == "missed"

    def test_missed_very_low_time(self):
        block = _create_block(category="Writing", start="2025-06-03T12:00:00+00:00", end="2025-06-03T14:00:00+00:00")
        _create_log(
            block_id=block["id"],
            what_happened="Barely started",
            category="Writing",
            productive=True,
            actual_minutes=20,  # ~17% of 120 => <=20% => missed
        )
        updated = _get_block(block["id"])
        assert updated["status"] == "missed"

    def test_overrunning_a_block_still_completed(self):
        block = _create_block(category="Study", start="2025-06-04T09:00:00+00:00", end="2025-06-04T10:00:00+00:00")
        _create_log(
            block_id=block["id"],
            what_happened="Deep study",
            category="Study",
            productive=True,
            actual_minutes=90,  # over the 60 planned
        )
        updated = _get_block(block["id"])
        assert updated["status"] == "completed"

    def test_no_actual_minutes_defaults_to_planned(self):
        block = _create_block(category="Work", start="2025-06-04T11:00:00+00:00", end="2025-06-04T13:00:00+00:00")
        log = _create_log(
            block_id=block["id"],
            what_happened="Did the work",
            category="Work",
            productive=True,
        )
        assert log["actual_minutes"] == 120  # defaulted to planned
        updated = _get_block(block["id"])
        assert updated["status"] == "completed"


# --------------------------------------------------------------------------- #
# Blank-time logging
# --------------------------------------------------------------------------- #

class TestBlankTimeLogging:
    """Logs with no block_id but with start/end compute minutes automatically."""

    def test_blank_time_computes_minutes(self):
        log = _create_log(
            what_happened="Watched YouTube",
            category="Entertainment",
            productive=False,
            start="2025-06-05T14:00:00+00:00",
            end="2025-06-05T17:30:00+00:00",
        )
        assert log["actual_minutes"] == 210  # 3.5 hours
        assert log["block_id"] is None

    def test_blank_time_with_explicit_minutes_uses_explicit(self):
        log = _create_log(
            what_happened="Commute",
            category="Transport",
            productive=False,
            start="2025-06-05T08:00:00+00:00",
            end="2025-06-05T09:00:00+00:00",
            actual_minutes=45,  # explicitly set even though start/end = 60
        )
        assert log["actual_minutes"] == 45

    def test_blank_time_no_start_end_no_minutes(self):
        log = _create_log(
            what_happened="Quick errand",
            category="Personal",
            productive=True,
        )
        assert log["actual_minutes"] is None
        assert log["block_id"] is None


# --------------------------------------------------------------------------- #
# Unaccounted blocks
# --------------------------------------------------------------------------- #

class TestUnaccountedBlocks:
    """GET /api/logs/unaccounted only returns ended, unlogged blocks."""

    def test_only_ended_unlogged_blocks_appear(self):
        # Block in the far past, no log => should appear
        past_block = _create_block(
            title="Old task",
            category="Admin",
            start="2024-01-01T09:00:00+00:00",
            end="2024-01-01T10:00:00+00:00",
        )
        # Block in the far future => should NOT appear (hasn't ended)
        _create_block(
            title="Future task",
            category="Admin",
            start="2099-01-01T09:00:00+00:00",
            end="2099-01-01T11:00:00+00:00",
        )

        r = client.get("/api/logs/unaccounted", params={"now": "2025-06-10T00:00:00+00:00"})
        assert r.status_code == 200
        ids = [b["id"] for b in r.json()]
        assert past_block["id"] in ids

    def test_logged_block_does_not_appear(self):
        block = _create_block(
            title="Logged task",
            category="Work",
            start="2024-02-01T09:00:00+00:00",
            end="2024-02-01T10:00:00+00:00",
        )
        _create_log(
            block_id=block["id"],
            what_happened="Did it",
            category="Work",
            productive=True,
            actual_minutes=60,
        )
        r = client.get("/api/logs/unaccounted", params={"now": "2025-06-10T00:00:00+00:00"})
        ids = [b["id"] for b in r.json()]
        assert block["id"] not in ids
