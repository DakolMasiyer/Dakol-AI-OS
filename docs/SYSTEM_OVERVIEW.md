# System Overview

## What Dakol-AI-OS Is

Dakol-AI-OS is a general-purpose, reusable multi-agent AI operating system. It accepts any user task in plain English, routes it to the most capable LLM backend, runs a panel of domain specialist agents in parallel to score intent, fuses their results via a second LLM brain, and logs the full decision trail for future learning.

It is not a product tied to any single domain. The music/SyncMaster agents in the repo are example implementations that demonstrate the pattern. The architecture is designed so that any domain — tech, film, media, defense, legal, finance — can be added by creating a new agent file and registering it in the orchestrator. Nothing else changes.

## The Three-Layer Model

```
Layer 1 — Model Router
Keyword-based classification routes the task to the best LLM backend:
Claude API (reasoning/design), OpenAI GPT (code generation), or local/cloud fallback (everything else)

Layer 2 — Multi-Agent Fusion
All registered domain agents run in parallel. Each scores the task with a confidence value.
A fusion LLM reads all scores and declares the final intent, best agent, and overall confidence.

Layer 3 — Memory Layer
Every task, routing decision, model output, and agent result is appended to an event log.
This log is the foundation for future self-improvement (Steps 8 and 9).
```

## What the System Is Not

- **Not LangGraph** — there is no graph of nodes with conditional edges. Routing is simpler: one classification function, one branch.
- **Not CrewAI** — agents do not have natural-language roles or backstories. They are Python classes with keyword lists.
- **Not AutoGen** — agents do not hold conversations with each other. They each score the task independently.
- **Not OpenAI Swarm** — there are no mid-conversation handoffs between agents.

The system is hand-rolled intentionally. It is lightweight, readable, and fully under your control. Migration to a framework is a post-revenue decision.

## Repo Map

| File | Role |
|---|---|
| `scripts/router.py` | Single entry point — `route_task(task)` orchestrates everything. **Currently broken: missing imports.** |
| `skills/router_skills.py` | Complete implementations of `analyze_task`, `run_claude`, `run_codex`, `run_local` |
| `agents/base_agent.py` | `BaseAgent` class — defines `domain_weight` and the standardised `run()` interface |
| `agents/sync_agent.py` | SyncMaster music metadata specialist — `domain_weight=1.3`, keyword tiers for BPM/tempo/tags |
| `agents/audio_agent.py` | Audio/sound/track intent specialist |
| `agents/code_agent.py` | Code/API/FastAPI development intent specialist |
| `agents/orchestrator.py` | Runs all agents, builds fusion prompt, calls fusion LLM, returns structured decision |
| `memory/log.py` | Canonical 4-argument `log_event()` — appends full event including `agent_result` to `logs.json` |
| `memory/logs.json` | Append-only event store — every task ever routed |
| `scripts/memory.py` | **Superseded** — older 3-argument version of the logger. Do not use. |
| `diagrams/generate_diagrams.py` | Generates the 6 PNG flowcharts using the `graphviz` library |
| `diagrams/output/` | 6 PNG flowcharts: core architecture, SyncMaster agent, Tech/Film/Media/Defense domain cases |

## Current Broken State

`scripts/router.py` calls `analyze_task`, `run_claude`, `run_codex`, `run_local`, `Orchestrator`, and `log_event` without importing any of them. The fix is three lines at the top of the file:

```python
from skills.router_skills import analyze_task, run_claude, run_codex, run_local
from agents.orchestrator import Orchestrator
from memory.log import log_event
```

Everything else in `router.py` is correct. This is the first task in any new session.

## Reading Order

For full situational awareness, read in this order:

1. `docs/SYSTEM_OVERVIEW.md` — this file
2. `docs/TECHNICAL_ARCHITECTURE.md` — code-level mechanics
3. `docs/AGENT_GUIDE.md` — how to extend the system with new domains
4. `docs/GEMINI_INTEGRATION.md` — where Gemini models fit and why
5. `docs/PRODUCTION_PLAN.md` — how to go from local to live HTTPS
6. `docs/BUSINESS_STRATEGY.md` — monetisation paths and exit strategy
7. `SESSION_LOG.md` — decisions made in the 2026-05-26 session
