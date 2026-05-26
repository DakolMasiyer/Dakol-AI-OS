# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**Dakol-AI-OS** is a multi-agent AI task router built for the *SyncMaster* music platform. It intelligently routes user tasks to one of three LLM backends (Claude API, OpenAI/Codex, or local Ollama), runs a parallel multi-agent consensus layer, fuses the results, and logs everything to a JSON memory store for future reinforcement learning.

## Running the Router

There is no build step. The project is pure Python with these required dependencies (install in a venv):

```bash
pip install anthropic openai python-dotenv
```

The local Ollama model must also be available:

```bash
ollama pull coder-pro:latest   # based on qwen2.5-coder:7b
```

Create a `.env` file at the project root before running:

```
ANTHROPIC_API_KEY=your-key-here
OPENAI_API_KEY=your-key-here
OLLAMA_API_BASE=http://localhost:11434
```

To invoke the router from a Python session:

```python
from scripts.router import route_task
route_task("describe your task here")
```

There are no tests and no linter configuration.

## Architecture

### Request Flow

1. `scripts/router.py` → `route_task(task)` is the single entry point
2. **Model selection**: `analyze_task(task)` classifies the task into `claude`, `codex`, or `local` via keyword matching
3. **Model execution**: `run_claude()` / `run_codex()` / `run_local()` call the respective LLM backend
4. **Multi-agent fusion**: `Orchestrator.route(task)` runs all three domain agents in parallel, collects their confidence scores, then queries `coder-pro:latest` via Ollama subprocess to synthesize a single `final_intent` + `best_agent` JSON decision
5. **Memory logging**: `memory/log.py:log_event()` appends the full event (task, model used, output, agent_result) to `memory/logs.json`

### Known Broken State

`scripts/router.py` is **currently broken** — it calls `analyze_task`, `run_claude`, `run_codex`, `run_local`, `Orchestrator`, and `log_event` without importing any of them. The complete, correct implementations live in `skills/router_skills.py` and `memory/log.py`. The fix is to add these imports to the top of `scripts/router.py`:

```python
from skills.router_skills import analyze_task, run_claude, run_codex, run_local
from agents.orchestrator import Orchestrator
from memory.log import log_event
```

Note: `scripts/memory.py` is a superseded older version of the memory logger with a 3-argument `log_event` signature. The canonical version is `memory/log.py`, which takes a 4th `agent_result` argument for learning data.

### Agent Layer (`agents/`)

- `BaseAgent` — defines `domain_weight` (float multiplier applied to raw confidence) and the `run()` method that returns a standardized result dict
- `SyncAgent` — `domain_weight=1.3`; specializes in music metadata keywords (`tag`, `bpm`, `metadata`, `tempo`, `key`)
- `AudioAgent` — detects audio/sound/track intents
- `CodeAgent` — detects code/api/fastapi/build/implement intents
- `Orchestrator` — collects results from all three agents, builds a fusion prompt, and calls Ollama via `subprocess.run(["ollama", "run", "coder-pro:latest", prompt])`

### Model Routing Logic (`skills/router_skills.py`)

| Condition | Routed to |
|---|---|
| Task contains: `code`, `api`, `fastapi`, `build`, `implement`, `function` | `codex` (OpenAI `gpt-4o-mini`) |
| Task contains: `design`, `architecture`, `pipeline`, `licensing`, `fusion` | `claude` (`claude-3-5-sonnet-20241022`) |
| Everything else | `local` (Ollama `coder-pro:latest`) |

### Memory / Learning (`memory/`)

`logs.json` is the append-only event store. Each entry has: `timestamp`, `task`, `model_used`, `output` (capped at 800 chars), and `agent_result` (the full orchestrator output including all agent confidence scores). This `agent_result` field is the hook for Steps 8 & 9 (feedback-based learning and dynamic agent weight adjustment).

## Roadmap (from `progress.md`)

- **Step 8**: Read `memory/logs.json` for low-confidence entries; use them to tune `analyze_task` keyword heuristics
- **Step 9**: Dynamically update `agent.domain_weight` in `Orchestrator` based on historical accuracy in `logs.json`
