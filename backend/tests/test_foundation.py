"""Smoke tests for the Bogi foundation. Workstreams should add their own tests."""
from __future__ import annotations

import os
import tempfile

os.environ.setdefault("DATABASE_URL", f"sqlite:///{tempfile.mktemp(suffix='.db')}")

from fastapi.testclient import TestClient  # noqa: E402

from app.database import init_db  # noqa: E402
from app.main import app  # noqa: E402

init_db()
client = TestClient(app)


def test_health():
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def test_block_crud_and_log_loop():
    # Create a block (intention)
    r = client.post(
        "/api/blocks",
        json={
            "title": "Edit videos",
            "category": "Work",
            "start": "2025-01-01T09:00:00+00:00",
            "end": "2025-01-01T11:00:00+00:00",
        },
    )
    assert r.status_code == 201, r.text
    block = r.json()
    assert block["planned_minutes"] == 120

    # Account for it (reality) — did something else
    r = client.post(
        "/api/logs",
        json={
            "block_id": block["id"],
            "what_happened": "Scrolled instead",
            "category": "Social media",
            "productive": False,
            "actual_minutes": 30,
        },
    )
    assert r.status_code == 201, r.text

    # Block status should now reflect the gap
    r = client.get(f"/api/blocks/{block['id']}")
    assert r.json()["status"] in ("missed", "partial")


def test_databank_summary():
    r = client.get("/api/databank/summary", params={"period": "day", "anchor": "2025-01-01T12:00:00+00:00"})
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["period"] == "day"
    assert body["planned_minutes"] >= 120


def test_plan_endpoint():
    r = client.post("/api/blocks/plan", json={"text": "edit videos for 2 hours and email clients for 30 minutes"})
    assert r.status_code == 200, r.text
    assert len(r.json()["blocks"]) >= 1


def test_coach_chat():
    r = client.post("/api/coach/chat", json={"message": "Help me plan my day"})
    assert r.status_code == 200, r.text
    assert r.json()["reply"]
