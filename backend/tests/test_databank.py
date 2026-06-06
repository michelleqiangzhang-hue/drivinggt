"""Tests for the data bank / analytics — gap summary across periods."""
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
# Fixed date for a known day: 2025-03-10 (Monday)
# --------------------------------------------------------------------------- #
DAY_ANCHOR = "2025-03-10T12:00:00+00:00"


def _create_block(
    title: str,
    category: str,
    start: str,
    end: str,
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


# --------------------------------------------------------------------------- #
# Seed a known day: 2025-03-10
#   Block 1: Work 09:00-11:00 (120 min) -> logged completed, 100 min productive
#   Block 2: Study 13:00-14:00 (60 min) -> logged partial, 30 min productive
#   Block 3: Exercise 16:00-17:00 (60 min) -> not logged (unlogged)
# --------------------------------------------------------------------------- #


def _seed_known_day():
    b1 = _create_block("Coding", "Work", "2025-03-10T09:00:00+00:00", "2025-03-10T11:00:00+00:00")
    _create_log(
        block_id=b1["id"],
        what_happened="Coded features",
        category="Work",
        productive=True,
        actual_minutes=100,
    )
    b2 = _create_block("Read papers", "Study", "2025-03-10T13:00:00+00:00", "2025-03-10T14:00:00+00:00")
    _create_log(
        block_id=b2["id"],
        what_happened="Read half a paper",
        category="Study",
        productive=True,
        actual_minutes=30,
    )
    b3 = _create_block("Gym", "Exercise", "2025-03-10T16:00:00+00:00", "2025-03-10T17:00:00+00:00")
    return b1, b2, b3


_b1, _b2, _b3 = _seed_known_day()


# --------------------------------------------------------------------------- #
# Day summary
# --------------------------------------------------------------------------- #


class TestDaySummary:
    def test_planned_minutes(self):
        r = client.get("/api/databank/summary", params={"period": "day", "anchor": DAY_ANCHOR})
        assert r.status_code == 200
        body = r.json()
        assert body["planned_minutes"] == 240  # 120 + 60 + 60

    def test_logged_minutes(self):
        r = client.get("/api/databank/summary", params={"period": "day", "anchor": DAY_ANCHOR})
        body = r.json()
        assert body["logged_minutes"] == 130  # 100 + 30

    def test_productive_minutes(self):
        r = client.get("/api/databank/summary", params={"period": "day", "anchor": DAY_ANCHOR})
        body = r.json()
        assert body["productive_minutes"] == 130

    def test_unproductive_minutes(self):
        r = client.get("/api/databank/summary", params={"period": "day", "anchor": DAY_ANCHOR})
        body = r.json()
        assert body["unproductive_minutes"] == 0

    def test_status_counts(self):
        r = client.get("/api/databank/summary", params={"period": "day", "anchor": DAY_ANCHOR})
        body = r.json()
        # b1 = completed (100 >= 0.8*120), b2 = partial (30 between 20-80% of 60), b3 = unlogged
        assert body["completed_blocks"] == 1
        assert body["partial_blocks"] == 1
        assert body["unlogged_blocks"] == 1
        assert body["missed_blocks"] == 0

    def test_adherence_rate(self):
        r = client.get("/api/databank/summary", params={"period": "day", "anchor": DAY_ANCHOR})
        body = r.json()
        # 1 completed / 3 total
        assert body["adherence_rate"] == round(1 / 3, 3)

    def test_category_breakdowns_sorted_desc(self):
        r = client.get("/api/databank/summary", params={"period": "day", "anchor": DAY_ANCHOR})
        body = r.json()
        planned_cats = body["planned_by_category"]
        assert len(planned_cats) == 3
        # Should be sorted by minutes descending: Work(120), Exercise(60)|Study(60)
        assert planned_cats[0]["category"] == "Work"
        assert planned_cats[0]["minutes"] == 120
        # Actual should be sorted desc too
        actual_cats = body["actual_by_category"]
        assert len(actual_cats) == 2  # Work + Study
        assert actual_cats[0]["category"] == "Work"
        assert actual_cats[0]["minutes"] == 100


# --------------------------------------------------------------------------- #
# Zero-block edge case
# --------------------------------------------------------------------------- #


class TestZeroBlocks:
    def test_adherence_rate_zero_blocks(self):
        r = client.get(
            "/api/databank/summary",
            params={"period": "day", "anchor": "2020-01-01T12:00:00+00:00"},
        )
        body = r.json()
        assert body["adherence_rate"] == 0.0
        assert body["planned_minutes"] == 0


# --------------------------------------------------------------------------- #
# Period window filtering
# --------------------------------------------------------------------------- #


class TestPeriodWindows:
    """Week/month/year windows include/exclude the right items."""

    def test_week_includes_known_day(self):
        # 2025-03-10 is a Monday; week = Mon 10 – Sun 16
        r = client.get(
            "/api/databank/summary",
            params={"period": "week", "anchor": "2025-03-12T12:00:00+00:00"},
        )
        body = r.json()
        assert body["planned_minutes"] >= 240
        assert body["start"] in ("2025-03-10T00:00:00+00:00", "2025-03-10T00:00:00Z")

    def test_week_excludes_different_week(self):
        r = client.get(
            "/api/databank/summary",
            params={"period": "week", "anchor": "2025-03-03T12:00:00+00:00"},
        )
        body = r.json()
        # This week (Mar 3-9) should have no blocks from our known day
        assert body["planned_minutes"] == 0

    def test_month_includes_known_day(self):
        r = client.get(
            "/api/databank/summary",
            params={"period": "month", "anchor": "2025-03-15T12:00:00+00:00"},
        )
        body = r.json()
        assert body["planned_minutes"] >= 240
        assert body["start"] in ("2025-03-01T00:00:00+00:00", "2025-03-01T00:00:00Z")

    def test_month_excludes_different_month(self):
        r = client.get(
            "/api/databank/summary",
            params={"period": "month", "anchor": "2025-04-15T12:00:00+00:00"},
        )
        body = r.json()
        assert body["planned_minutes"] == 0

    def test_year_includes_known_day(self):
        r = client.get(
            "/api/databank/summary",
            params={"period": "year", "anchor": "2025-06-01T12:00:00+00:00"},
        )
        body = r.json()
        assert body["planned_minutes"] >= 240
        assert body["start"] in ("2025-01-01T00:00:00+00:00", "2025-01-01T00:00:00Z")

    def test_year_excludes_different_year(self):
        r = client.get(
            "/api/databank/summary",
            params={"period": "year", "anchor": "2019-06-01T12:00:00+00:00"},
        )
        body = r.json()
        # No blocks in 2019
        assert body["planned_minutes"] == 0
