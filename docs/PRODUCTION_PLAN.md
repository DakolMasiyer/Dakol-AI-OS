# Production Plan

## Current State Baseline

What exists today:
- Pure Python, no HTTP server, no API layer
- `scripts/router.py` is broken — missing 3 import lines
- Fusion brain runs via local Ollama subprocess — requires Ollama installed on host
- Memory is a flat JSON file (`memory/logs.json`) — no concurrent write safety
- API keys live in a local `.env` file — not safe for cloud deployment
- No tests, no CI, no Dockerfile
- Fully functional on a local machine once the import bug is fixed

---

## Stage 1 — Fix and Wrap (0–4 weeks)

**Goal:** A running local server that external tools can call over HTTP.

**Tasks:**

1. **Fix the broken imports** in `scripts/router.py`:
   ```python
   from skills.router_skills import analyze_task, run_claude, run_codex, run_local
   from agents.orchestrator import Orchestrator
   from memory.log import log_event
   ```

2. **Add a FastAPI wrapper** — new file `api/main.py`:
   ```python
   from fastapi import FastAPI
   from scripts.router import route_task

   app = FastAPI()

   @app.post("/task")
   def handle_task(payload: dict):
       result = route_task(payload["task"])
       return {"output": result}
   ```

3. **Basic input validation** — reject empty tasks, cap task length at 2000 chars.

**Deliverable:** `uvicorn api.main:app` runs locally. `POST /task` returns JSON. The entire existing codebase is unchanged.

**New dependencies:** `fastapi`, `uvicorn`

---

## Stage 2 — Replace Local Dependencies (4–8 weeks)

**Goal:** Zero local-process dependencies. Everything calls an API.

**Four substitutions:**

| Replace | With | Why |
|---|---|---|
| Ollama subprocess in `orchestrator.py` | Gemini 2.0 Flash API | Removes local install requirement; see `GEMINI_INTEGRATION.md` |
| `memory/logs.json` flat file | Supabase (PostgreSQL) | Concurrent writes, persistent across deploys, queryable |
| `.env` file on local machine | Railway environment variables | Secrets managed by the platform, not the developer's laptop |
| `scripts/memory.py` | Delete it | Superseded 3-argument logger; `memory/log.py` is canonical |

**Supabase schema for the memory log:**
```sql
CREATE TABLE task_log (
  id SERIAL PRIMARY KEY,
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  task TEXT,
  model_used TEXT,
  output TEXT,
  agent_result JSONB
);
```

**Deliverable:** Running the app requires no locally installed software beyond Python. All state is remote.

**New dependencies:** `google-generativeai`, `supabase`

---

## Stage 3 — Deploy on Railway (8–10 weeks)

**Goal:** Live HTTPS endpoint, 24/7 uptime, auto-deploys on git push.

**Steps:**

1. Add a `Procfile` or `nixpacks.toml` at repo root:
   ```
   web: uvicorn api.main:app --host 0.0.0.0 --port $PORT
   ```

2. In the Railway dashboard:
   - Create a new project from the GitHub repo
   - Set environment variables: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`
   - Add Supabase as a connected service

3. Point a custom domain (e.g., `api.dakol-ai-os.com`) to the Railway deployment.

**Deliverable:** A live HTTPS endpoint. `POST https://api.dakol-ai-os.com/task` works from anywhere. This is the URL you share with beta users.

FastAPI is stateless — Railway can run multiple instances automatically once traffic warrants it. No additional config needed for horizontal scaling.

---

## Stage 4 — Scale Layer (10–18 weeks)

**Goal:** Production-grade reliability under real user load.

**Three additions:**

### Redis Cache
Repeated or similar tasks should not burn API credits on a fresh LLM call every time.

```
Task comes in
    ↓
Hash the task string → check Redis
    ↓
Cache hit? Return cached result (TTL: 1 hour)
Cache miss? Call route_task(), store result, return
```

New dependency: `redis` (Railway has a Redis add-on)

### Task Queue
Long-running fusion calls (Orchestrator + LLM) should not block the HTTP response. Move them async:

```
POST /task → queue the job → return job_id immediately
GET /task/{job_id} → return result when ready
```

Use Celery with Redis as the broker, or Railway's native background workers.

### Fallback Chain
When a primary model fails or rate-limits, retry with the next best option automatically:

```
Claude API fails / rate-limits
    ↓
Retry with Gemini 2.5 Pro
    ↓
Gemini fails
    ↓
Retry with OpenAI GPT
    ↓
Log which model actually served the request
```

This is implemented in `skills/router_skills.py` with try/except blocks and a priority list per model family.

**Deliverable:** The system handles concurrent users, does not burn API credits on repeated tasks, and self-heals when any single LLM provider has issues.

---

## Industry Framework Evaluation

**Recommendation: do not migrate to LangGraph, CrewAI, AutoGen, or OpenAI Swarm before first paying customers.**

The hand-rolled architecture is readable, debuggable, and fast to change. Framework migrations have a high upfront cost and introduce abstractions that can obscure bugs. Evaluate only after the current architecture hits a genuine ceiling.

When to re-evaluate:

| Framework | Migrate when... |
|---|---|
| **LangGraph** | Workflows become non-linear — a task needs to loop back for clarification, branch conditionally, or span multiple LLM calls with shared state |
| **CrewAI** | You want agents to have natural-language roles and goals rather than keyword lists — useful when onboarding non-technical domain experts to configure agents |
| **AutoGen** | You need agents to debate or refine answers through multi-turn conversation before returning a result |
| **OpenAI Swarm** | You want mid-conversation handoffs — one agent starts a response and passes control to a specialist mid-stream |

Dakol-AI-OS today is functionally equivalent to the lightweight end of this spectrum. The architecture is worth keeping as long as it is sufficient.

---

## Dependencies by Stage

| Stage | New packages |
|---|---|
| Stage 1 | `fastapi`, `uvicorn` |
| Stage 2 | `google-generativeai`, `supabase` |
| Stage 3 | None (platform config only) |
| Stage 4 | `redis`, `celery` |
