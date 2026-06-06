"""Bogi FastAPI application entrypoint."""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.database import init_db
from app.routers import (
    accountability,
    auth,
    calendar,
    coach,
    databank,
    goals,
    patterns,
)
from app.seed import seed_demo_data


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    seed_demo_data()
    yield


app = FastAPI(title="Bogi API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(calendar.router)
app.include_router(accountability.router)
app.include_router(databank.router)
app.include_router(coach.router)
app.include_router(patterns.router)
app.include_router(goals.router)


@app.get("/api/health")
def health() -> dict[str, object]:
    return {"status": "ok", "ai_enabled": settings.ai_enabled}
