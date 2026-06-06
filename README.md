# Bogi

> Bogi helps you plan your day (your **intention**), then makes you account for the
> gap between what you said you'd do and what you **actually** did — turning that
> gap into a private, long-term behavioral data bank that helps you plan better
> over time.

**Calendar planning = only your intention. Accountability logs = the reality of
what you actually did.** The product is the gap between them.

## Why it's not a screen-time app
Screen-time apps block you. Bogi makes you *face* what you did. The friction is the
point: a real accountability coach asks "what did you just spend that hour on?",
and the moment you answer in your own words, you become mindful. That mindfulness
is the product — not blocking.

## The core loop
A calendar block ends → you tell the coach what actually happened → the gap is
computed → it feeds your data bank → Bogi learns your real patterns → your next
plan gets smarter.

## Architecture

Monorepo with two apps:

| Path        | Stack                                              | Purpose |
|-------------|----------------------------------------------------|---------|
| `backend/`  | FastAPI · SQLModel · SQLite · OpenAI               | API, data model, AI coach/planner/patterns |
| `frontend/` | React · Vite · TypeScript · Tailwind · Recharts    | Mobile-first PWA UI |

The AI coach works in a **deterministic mock mode** with no API key, and uses
OpenAI when `OPENAI_API_KEY` is set.

### Domain model (the shared contract)
- `CalendarBlock` — INTENTION (what you planned)
- `AccountabilityLog` — REALITY (what actually happened)
- `Goal` — what the honest coach holds you to
- `UserPattern` — BETA: learned behavioral patterns for smarter future planning
- `Conversation` / `CoachMessage` — chat with Bogi

API contracts live in `backend/app/schemas.py` and mirror in `frontend/src/api/types.ts`.

## Running locally

### Backend
```bash
cd backend
uv venv .venv && source .venv/bin/activate
uv pip install -e ".[dev]"
export OPENAI_API_KEY=sk-...        # optional; omit for mock mode
uvicorn app.main:app --reload --port 8000
```
API docs at http://localhost:8000/docs. Demo data is seeded on first run.

### Frontend
```bash
cd frontend
npm install
npm run dev    # http://localhost:5173 (proxies /api -> :8000)
```

## Tests / checks
```bash
# backend
cd backend && source .venv/bin/activate && ruff check . && pytest
# frontend
cd frontend && npm run lint && npm run typecheck && npm run build
```
