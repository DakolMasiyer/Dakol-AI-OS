# Technical Architecture

## Request Lifecycle

A complete end-to-end trace of what happens when `route_task("tag the BPM for this track")` is called:

1. `scripts/router.py:route_task(task)` is called — the single entry point
2. `analyze_task(task)` in `skills/router_skills.py` lowercases the task and keyword-matches it to a model family (`claude`, `codex`, or `local`)
3. The matched runner (`run_claude`, `run_codex`, or `run_local`) calls the corresponding LLM API and returns a string output
4. `Orchestrator()` is instantiated; `orchestrator.route(task)` runs
5. Inside `route()`, every agent in `self.agents` calls `agent.run(task)` — all three run sequentially (parallel execution is an architectural upgrade, not yet implemented)
6. Each `agent.run()` calls `self.analyze_task(task)` to get a raw `{intent, confidence}` dict, then multiplies `confidence` by `self.domain_weight` to produce the adjusted score
7. The Orchestrator calls `_build_fusion_prompt(task, results)` to construct a structured prompt containing all agent outputs
8. `_run_llm(prompt)` fires `subprocess.run(["ollama", "run", "coder-pro:latest", prompt])` and returns stdout — **this is the local dependency that must be replaced before cloud deployment**
9. `_safe_parse(output)` attempts `json.loads()`; on failure returns a fallback dict with `parse_status: "failed"`
10. `route()` returns `{fusion_output: {...}, all_results: [...]}`
11. Back in `router.py`, `log_event(task, model, output, agent_result)` in `memory/log.py` appends the full event to `memory/logs.json`
12. `route_task()` returns the model output string

## Model Routing Table

Defined in `skills/router_skills.py:analyze_task()`:

| Keywords in task (lowercase) | Routed to | LLM used |
|---|---|---|
| `code`, `api`, `fastapi`, `build`, `implement`, `function` | `codex` | OpenAI `gpt-4o-mini` |
| `design`, `architecture`, `pipeline`, `licensing`, `fusion` | `claude` | Anthropic `claude-3-5-sonnet-20241022` |
| Anything else | `local` | Ollama `coder-pro:latest` |

The codex branch is evaluated first, so a task containing both `build` and `design` routes to `codex`.

## Agent Scoring Mechanics

`agents/base_agent.py` provides the scoring formula:

```
adjusted_confidence = raw_confidence * domain_weight
```

`BaseAgent.__init__` accepts `domain_weight` (default `1.0`). Subclasses set it in their own `__init__`. Current values:

| Agent | `domain_weight` | Effect |
|---|---|---|
| `SyncAgent` | 1.3 | All scores boosted 30% — wins tie-breakers in music tasks |
| `AudioAgent` | 1.0 | No boost |
| `CodeAgent` | 1.0 | No boost |

**SyncAgent keyword tiers** (in `agents/sync_agent.py:analyze_task()`):

| Tier | Keywords | Raw confidence | Adjusted |
|---|---|---|---|
| High | `tag`, `bpm`, `metadata`, `tempo`, `key` | 0.9 | **1.17** |
| Medium | `music`, `audio`, `sound`, `track`, `song` | 0.8 | **1.04** |
| Fallback | (none matched) | 0.6 | **0.78** |

Adjusted scores can exceed 1.0. The fusion brain is given all scores and picks the highest — no clamping is needed.

## Orchestrator Fusion Flow

`agents/orchestrator.py:_build_fusion_prompt()` constructs:

```
You are a multi-agent AI fusion engine.
You combine outputs into a single structured decision.

TASK: {task}

AGENT OUTPUTS:
{json.dumps(results, indent=2)}

Return ONLY valid JSON:
{
  "final_intent": "string",
  "reasoning": "string",
  "best_agent": "string",
  "confidence": number
}
```

Expected response fields:

| Field | Type | Meaning |
|---|---|---|
| `final_intent` | string | What the task is actually about, e.g. `metadata_analysis` |
| `reasoning` | string | The fusion brain's explanation |
| `best_agent` | string | Name of the winning agent, e.g. `sync_agent` |
| `confidence` | float | Fusion brain's overall confidence in the decision |

`_safe_parse()` wraps `json.loads()` in a try/except. On failure, it returns `{"final_intent": "unknown", "reasoning": raw_text, "best_agent": "unknown", "confidence": 0.0, "parse_status": "failed"}`.

## Memory Schema

Each entry in `memory/logs.json`:

```json
{
  "timestamp": "2026-05-26T14:23:01.123456",
  "task": "tag the BPM for this track",
  "model_used": "local",
  "output": "BPM stands for... (capped at 800 characters)",
  "agent_result": {
    "fusion_output": {
      "final_intent": "metadata_analysis",
      "reasoning": "...",
      "best_agent": "sync_agent",
      "confidence": 0.9
    },
    "all_results": [
      {"agent": "sync_agent", "intent": "metadata_analysis", "confidence": 1.17, "input": "...", "status": "processed"},
      ...
    ]
  }
}
```

- `output` is hard-capped at 800 characters in `memory/log.py`
- `agent_result` is `None` in older log entries written before this field was added
- `scripts/memory.py` is a superseded 3-argument version that does not store `agent_result` — it should not be used

## Known Issues and Technical Debt

- **Broken imports in `router.py`** — `analyze_task`, `run_claude`, `run_codex`, `run_local`, `Orchestrator`, and `log_event` are called but never imported. Fix: 3 import lines (see `SYSTEM_OVERVIEW.md`).
- **Ollama subprocess coupling** — the fusion brain calls `subprocess.run(["ollama", "run", ...])`. This requires Ollama installed locally. It will fail on any cloud server. Replacement: Gemini 2.0 Flash API (see `GEMINI_INTEGRATION.md`).
- **No concurrent write safety** — `memory/log.py` reads the full JSON array, appends, and rewrites the file. Concurrent requests will corrupt the log. Fix: replace with a database before multi-user deployment.
- **No tests** — there is no test suite. All verification is manual.
- **`scripts/memory.py` is superseded** — it is a 3-argument version of the logger that predates `agent_result`. It should be deleted.

## Steps 8 and 9 — Hooks for Self-Improvement

Both are architectural placeholders. Neither is implemented yet.

**Step 8 — Learning from Feedback:**
Scan `memory/logs.json` for entries where `fusion_output.confidence` is below a threshold (e.g., 0.6). Use those low-confidence tasks to identify gaps in the keyword routing heuristics in `analyze_task()` and add new keyword triggers. This makes the router smarter over time without manual tuning.

**Step 9 — Dynamic Agent Weighting:**
After each task, compare the `best_agent` declared by the fusion brain against the `model_used` routing decision. If they consistently disagree for a given domain, adjust the relevant agent's `domain_weight` upward. `Orchestrator.__init__` already has a `self.model_learning = {}` dict reserved as the hook for this.

## Diagrams Reference

All generated by `diagrams/generate_diagrams.py` using the `graphviz` Python library:

| File | Shows |
|---|---|
| `diagrams/output/1_core_architecture.png` | Full end-to-end pipeline: user → router → model layer → orchestrator → agents → fusion → memory |
| `diagrams/output/2_syncmaster_agent.png` | SyncAgent keyword tiers, domain_weight boost, and how it wins the agent panel |
| `diagrams/output/3_tech_domain.png` | Tech domain case: CodeAgent wins, GPT handles code generation |
| `diagrams/output/4_film_domain.png` | Film domain case: FilmAgent wins, Claude handles licensing pipeline |
| `diagrams/output/5_media_domain.png` | Media domain case: MediaAgent wins, Claude handles content strategy |
| `diagrams/output/6_defense_domain.png` | Defense domain case: DefenseAgent wins with 0.95 confidence, Claude handles threat modeling |
