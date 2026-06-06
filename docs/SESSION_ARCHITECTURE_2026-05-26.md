# SyncMaster + Dakol-AI-OS — Research & Architecture Session
**Date:** 2026-05-26  
**Type:** Research, Architecture, Strategy  
**Next session:** Claude Code — Build Mode  
**Branch:** `claude/claude-md-docs-wqfhL`

---

## How to Use This Document

This is a continuity document for Claude Code. It captures the full thinking process, every pivot, every decision made, and the exact state of the architecture as designed. Read it fully before writing a single line of code. The build priorities are at the bottom.

---

## Starting State

When this session began, the codebase was in the following state:

| File | Status |
|---|---|
| `scripts/router.py` | Broken — calls `analyze_task`, `run_claude`, `run_codex`, `run_local`, `Orchestrator`, `log_event` without importing any of them |
| `agents/orchestrator.py` | Fusion brain uses the shared model fallback router — cloud-safe |
| `memory/log.py` | Canonical 4-argument logger — correct, do not touch |
| `scripts/memory.py` | Superseded — 3-argument logger, delete in Stage 2 migration |
| `memory/logs.json` | 13 real log entries from prior testing |

**The fix for `router.py` is three lines. Nothing else in the system runs until these are added:**

```python
from skills.router_skills import analyze_task, run_claude, run_codex, run_local
from agents.orchestrator import Orchestrator
from memory.log import log_event
```

---

## The Thinking Journey — In Order

This section documents every step of reasoning, including the pivots. This is not just what was decided — it is how and why.

---

### Step 1 — The Original Question: Can AI Generate Tracks and Have Agents Listen?

The first architectural question raised was:

> "Can we build something where AI generates tracks, agents listen to them, and the feedback becomes the moat for adaptive learning?"

The instinct was correct. This is a real and validated strategy. The question was whether it was ethical and whether it added to the moat.

**Ethical verdict reached:**
- Generating synthetic content for internal system calibration: fully ethical, standard ML practice
- Every synthetic entry must carry `"synthetic": true` in the database
- Never aggregate synthetic entries with real user data in any external metric
- The business case does not require misrepresentation — synthetic training data has genuine commercial value on its own terms

---

### Step 2 — Finding the Precedent: Musiio

Research surfaced the most relevant acquisition:

**Musiio → SoundCloud (2022)**
- Founded in Singapore, 2018
- AI that "listened to music at scale" — automated tagging, playlisting, B2B search
- By acquisition: 400 million track analyses, 75 B2B clients, 11 countries
- SoundCloud's stated reason: *"to understand how music is moving in a proprietary way"*

**Key insight from this:** The dataset was the acquisition target. The technology was the means. SoundCloud was not buying the code — they were buying the 400 million evaluations that could not be recreated from scratch without running the same operation for years.

**Also relevant:**
- Echo Nest → Spotify (2014, €49.7M) — 30M song intelligence database, music understanding infrastructure
- Gracenote → Nielsen → TiVo ($400M+ journey) — music metadata taxonomy at scale
- Tunigo → Spotify (2013) — playlist curation intelligence

---

### Step 3 — First Pivot: Generation Farm vs Listening Farm

The original idea was **generation + listening** (create tracks, have agents evaluate them).

The question was raised: does generating actual audio change the infrastructure significantly?

**Infrastructure delta surfaced:**

| | Metadata Only | Real Audio |
|---|---|---|
| Generation cost/track | ~$0.001 | ~$0.01–0.05 (Suno/Udio) |
| Generation time | ~1 second | 30–90 seconds |
| File storage | None | S3/Supabase Storage |
| Listener agent | Reads JSON | Downloads + processes audio |
| At 10k tracks | ~$15 | ~$200–600 |

**Decision made:** Listen first, generate later. The listening pipeline is cheaper, faster to build, and can be validated before committing to audio generation infrastructure. Generation becomes Phase 2 once the schema is proven.

---

### Step 4 — Second Pivot: Artist Uploads as the Input

The question was raised: instead of synthetic or open source tracks, what if the listening farm processes tracks uploaded by real artists through SyncMaster?

**This was the correct instinct.** It changes the architecture from a pure internal research pipeline to a product that generates moat data through normal usage.

**What this unlocks:**
- Real music with real commercial intent (artists want their tracks licensed — that signal is more valuable than synthetic)
- Product and moat are the same thing — every subscription contributes evaluation records
- The artist gets immediate value (metadata + brief matches); the farm gets the log entry
- This is exactly what Musiio was doing at scale

---

### Step 5 — Clarifying: Is This The Same As a Metadata Tagger?

Important architectural clarification reached:

**A metadata tagger does NOT read embedded MP3 tags.** That is stripping, not tagging. Three genuine approaches exist:

| Approach | What It Does | Moat Value |
|---|---|---|
| Strip embedded tags | Reads what artist already wrote | Zero — commodity |
| DSP extraction (librosa) | Analyses audio signal — BPM, key, energy, spectral | Low alone — Layer 1 foundation |
| LLM multimodal (Gemini 1.5 Pro) | Passes audio directly, returns contextual judgment | High — this is Layer 2, the actual listener |
| Trained classifier (farm output) | DSP features in → sync fitness out, no LLM | Maximum — this is the moat made operational |

**The tagger is Layer 1. The farm trains Layer 3. Layer 3 makes the tagger sync-aware.**

Without the farm, the tagger just knows BPM. With the farm, it knows that tracks like this get placed in automotive campaigns 84% of the time.

---

### Step 6 — The Architecture That Emerged: Three-Layer Intelligence Stack

The final architecture is called the **Three-Layer Intelligence Stack**. It is domain-agnostic. SyncMaster is the first deployment.

```
INPUT
  Open Source Catalogue (FMA, ccMixter, Jamendo) — bootstrap phase
  Artist Uploads (SyncMaster) — production phase
        ↓
LAYER 1 — SIGNAL EXTRACTION
  Tool: librosa (DSP pipeline)
  Output: BPM, key, energy, spectral, timbre, instrumentation, vocal presence
  Cost: ~$0.001/track | Speed: <5 seconds | No AI API needed
  NOTE: This is audio signal analysis, NOT reading embedded file tags
        ↓
LAYER 2 — SEMANTIC EVALUATION (THE LISTENER)
  Tool: Gemini 1.5 Pro (multimodal — audio passed directly)
  Input: audio file + Layer 1 features + sync placement brief
  Output: fit_score, reasoning, strengths, weaknesses, recommendation
  Cost: ~$0.02/evaluation | Speed: 5–30 seconds
  This is expensive at scale — Layer 3 classifier reduces LLM dependency over time
        ↓
        ├── Returns to artist: metadata tags + top 5 brief matches
        ↓
EVALUATION LOG — THE MOAT
  Table: evaluation_log (Supabase, separate from task_log)
  Every track × brief evaluation with full reasoning
  Grows with every upload and every brief run
  Synthetic entries flagged: synthetic: true
        ↓
LAYER 3 — CLASSIFIER TRAINING (THE TEACHING LOOP)
  Input: Layer 1 DSP features from evaluation_log
  Trains: scikit-learn classifier on accumulated data
  Output: sync fitness scores at DSP speed, no LLM needed
  Reduces LLM calls by 60–70% as log grows
        ↑
  Teaching loop arrow back to Layer 1 — classifier makes tagger sync-aware
```

---

### Step 7 — The Hybrid Input Strategy

Two input sources, in sequence:

**Phase 1 (Bootstrap — Months 1–2):** Open source catalogues
- FMA (Free Music Archive), ccMixter, Jamendo
- No artist relationships needed
- Proves pipeline, refines brief library
- Target: 10,000 evaluation records
- Cost: ~$200
- All entries marked `synthetic: true` or `source: open_catalogue`

**Phase 2 (Production — Month 3+):** Artist uploads via SyncMaster
- Real music, real commercial intent
- Artist gets immediate value: metadata + brief matches
- Farm gets evaluation records
- Real data marks the start of the genuine moat

---

### Step 8 — Domain Replication: Film

The architecture was verified to replicate directly to the film domain:

| Component | Music (SyncMaster) | Film (ScriptMaster) |
|---|---|---|
| Layer 1 Tool | librosa (audio DSP) | spaCy (script NLP) |
| Layer 1 Features | BPM, key, energy | Scene type, INT/EXT, character count, tone |
| Layer 2 Model | Gemini 1.5 Pro (audio) | Claude (text reasoning) |
| Evaluation Context | Sync placement brief | Production brief / budget |
| Layer 2 Output | Track fit score + reasoning | Scene complexity + call sheet elements |
| Moat Table | `evaluation_log` | `scene_evaluation_log` |
| Layer 3 Output | Sync fitness classifier | Production complexity classifier |

**The underlying Dakol-AI-OS infrastructure (router, orchestrator, memory layer) is identical for all domains.** New domains are new agents, new feature extractors, and new evaluation prompts. Nothing else changes.

---

### Step 9 — What the Original Idea Became

The user started with: *generate tracks + agents listen = moat.*

What that became:
- **Generation farm (Phase 1):** Bootstrap with synthetic/open source content before real users arrive
- **Listening farm (Phase 2):** The actual SyncMaster product — real artists, real tracks, real evaluations
- **These are not either/or. They are Phase 1 and Phase 2 of the same strategy.**

The person originally referenced (the acquisition story) almost certainly ran both: generated to bootstrap, then real tracks as the product scaled. The two phases were mistakenly treated as competing approaches during this session — they are sequential.

---

### Step 10 — What Was Confirmed NOT Needed Yet

| Rejected For Now | Reason |
|---|---|
| Stem separation (Spleeter/Demucs) | Expensive and slow. Layer 2 LLM gives richer signal than stem analysis alone. Revisit post-Series A. |
| Audio generation (Suno/Udio API) | Phase 2 — validate schema first with open source tracks. |
| LangGraph / CrewAI / AutoGen migration | Post-first-revenue. Hand-rolled architecture is sufficient and more readable. |
| Supabase multi-tenant isolation | Post-50 customers. Design for single tenant first. |

---

## The Moat — Precise Definition

The moat is **not** the routing system.  
The moat is **not** the metadata tagger.  
The moat is **not** the SyncMaster product.

**The moat is the `evaluation_log` table — accumulated contextual sync fitness judgments with full reasoning, at a scale no human team can produce and no competitor can replicate quickly.**

Three layers of defensibility:

| Layer | What It Is | Why It Holds |
|---|---|---|
| Volume | Raw count of track × brief evaluations | Time to replicate. Competitor needs months to catch up. |
| Schema depth | Natural language reasoning, not just scores | Proprietary ontology. Not replicable by copying the code. |
| Pattern intelligence | Statistical relationships extracted by Layer 3 classifier | Cannot be derived without the underlying evaluations. Steps 8 & 9 applied to music data. |

---

## Database Architecture

Two separate tables. Do not conflate them.

```sql
-- ROUTING MOAT — what Dakol-AI-OS accumulates
CREATE TABLE task_log (
  id SERIAL PRIMARY KEY,
  timestamp TIMESTAMPTZ DEFAULT NOW(),
  task TEXT,
  model_used TEXT,
  output TEXT,
  agent_result JSONB
);

-- DOMAIN EXPERTISE MOAT — what the listening farm accumulates
CREATE TABLE evaluation_log (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  track_id UUID,
  track_source TEXT,           -- 'open_catalogue' | 'artist_upload' | 'generated'
  brief_id TEXT,
  placement_type TEXT,
  brief JSONB,                 -- full brief object
  fit_score FLOAT,
  strengths TEXT[],
  weaknesses TEXT[],
  recommendation TEXT,         -- 'approve' | 'reject' | 'modify'
  reasoning TEXT,              -- full natural language judgment — critical field
  bpm_estimate FLOAT,
  key_estimate TEXT,
  energy_level FLOAT,
  mood_tags TEXT[],
  listener_model TEXT,         -- 'gemini-1.5-pro' | classifier version
  synthetic BOOLEAN DEFAULT FALSE,
  evaluated_at TIMESTAMPTZ DEFAULT NOW()
);

-- TRACKS — artist-facing, separate from evaluation data
CREATE TABLE tracks (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  artist_id UUID,
  audio_url TEXT,
  filename TEXT,
  duration_secs FLOAT,
  uploaded_at TIMESTAMPTZ DEFAULT NOW()
);
```

---

## New Agents Required

### `ListenerAgent` — new file: `agents/listener_agent.py`

```python
from agents.base_agent import BaseAgent

class ListenerAgent(BaseAgent):
    def __init__(self):
        super().__init__("listener_agent", domain_weight=1.4)
        # Higher than SyncAgent — this is the primary commercial pipeline

    def analyze_task(self, task: str) -> dict:
        t = task.lower()
        if any(w in t for w in ["upload", "listen", "evaluate", "brief", "sync fit"]):
            return {"intent": "sync_evaluation", "confidence": 0.95}
        if any(w in t for w in ["tag", "bpm", "metadata", "key", "tempo"]):
            return {"intent": "metadata_extraction", "confidence": 0.85}
        return {"intent": "general_audio", "confidence": 0.5}
```

Register in `agents/orchestrator.py`:
```python
from agents.listener_agent import ListenerAgent
self.agents = [SyncAgent(), AudioAgent(), CodeAgent(), ListenerAgent()]
```

### New pipeline file: `farm/listener_pipeline.py`

```python
def process_uploaded_track(track_id: str, audio_url: str) -> dict:
    metadata = extract_metadata(audio_url)           # Layer 1 — librosa
    evaluations = []
    for brief in get_active_briefs():
        result = evaluate_track_against_brief(audio_url, brief, metadata)  # Layer 2 — Gemini
        write_to_evaluation_log(track_id, brief, result)                   # Moat
        evaluations.append(result)
    top_matches = sorted(evaluations, key=lambda x: x["fit_score"], reverse=True)[:5]
    return {"metadata": metadata, "top_brief_matches": top_matches}
```

---

## `memory/log.py` — One Backward-Compatible Change Required

Add `synthetic` flag:

```python
# Current:
def log_event(task, model, output, agent_result):

# New (backward compatible — synthetic defaults to False):
def log_event(task, model, output, agent_result, synthetic=False):
    entry = {
        "timestamp": ...,
        "task": task,
        "model_used": model,
        "output": output[:800],
        "agent_result": agent_result,
        "synthetic": synthetic
    }
```

---

## `agents/orchestrator.py` — Replace Fusion Brain

Remove the local subprocess fallback. Replace `_run_llm` entirely:

```python
def _run_llm(self, prompt: str) -> str:
    import os
    import google.generativeai as genai

    genai.configure(api_key=os.environ["GEMINI_API_KEY"])

    # Primary: Gemini 2.0 Flash
    try:
        model = genai.GenerativeModel("gemini-2.0-flash")
        return model.generate_content(prompt).text
    except Exception as e:
        print(f"[orchestrator] Gemini Flash failed: {e}. Falling back.")

    # Fallback: Gemini Flash 8B
    try:
        model = genai.GenerativeModel("gemini-1.5-flash-8b")
        return model.generate_content(prompt).text
    except Exception as e:
        print(f"[orchestrator] Gemini 8B failed: {e}. Returning empty.")

    return '{"final_intent": "unknown", "reasoning": "all LLM backends failed", "best_agent": "unknown", "confidence": 0.0}'
```

New dependency:
```bash
pip install google-generativeai
```

New `.env` key:
```
GEMINI_API_KEY=your-key-here
```

---

## Build Priorities — Exact Order

### Priority 1 — Fix `scripts/router.py` (5 minutes)

Add three lines to the top:
```python
from skills.router_skills import analyze_task, run_claude, run_codex, run_local
from agents.orchestrator import Orchestrator
from memory.log import log_event
```

Test:
```python
from scripts.router import route_task
route_task("tag the BPM for this track")
route_task("build a FastAPI endpoint")
route_task("describe your task here")
```
Confirm all three routes fire. Confirm `logs.json` receives entries with valid `agent_result`.

---

### Priority 2 — Replace local fusion fallback (30 minutes)

Replace `_run_llm` in `agents/orchestrator.py` as shown above.
Install `google-generativeai`. Set `GEMINI_API_KEY` in `.env`.
Re-run the three test tasks. Confirm `_safe_parse` succeeds.

---

### Priority 3 — FastAPI Wrapper (1 hour)

New file `api/main.py`:
```python
from fastapi import FastAPI
from pydantic import BaseModel
from scripts.router import route_task

app = FastAPI()

class TaskRequest(BaseModel):
    task: str

@app.post("/task")
def handle_task(payload: TaskRequest):
    if not payload.task or len(payload.task) > 2000:
        return {"error": "invalid task"}
    result = route_task(payload.task)
    return {"output": result}
```

Run: `uvicorn api.main:app --reload`
Test: `curl -X POST http://localhost:8000/task -H "Content-Type: application/json" -d '{"task": "tag the BPM for this track"}'`

---

### Priority 4 — `memory/log.py` Synthetic Flag (10 minutes)

Add `synthetic=False` parameter as shown above. Backward compatible. No migration needed.

---

### Priority 5 — `ListenerAgent` Skeleton (30 minutes)

Create `agents/listener_agent.py` as shown above. Register in orchestrator. Run test tasks to confirm it wins on music evaluation tasks.

---

### Priority 6 — Brief Library (1–2 hours)

Create `farm/briefs.py` with a minimum of 20 placement type templates:
```python
BRIEF_LIBRARY = [
    {"brief_id": "b001", "placement_type": "automotive_ad", "tone": "powerful, aspirational", "energy": "high", "vocal": "instrumental_preferred"},
    {"brief_id": "b002", "placement_type": "romantic_drama", "tone": "tender, emotional", "energy": "low", "vocal": "vocal_preferred"},
    {"brief_id": "b003", "placement_type": "sports_highlight", "tone": "aggressive, triumphant", "energy": "very_high", "vocal": "either"},
    # ... 17 more
]
```

---

### Priority 7 — `evaluation_log` Supabase Table

Create the table as defined in the database architecture section above. Verify writes from the listener pipeline.

---

### Priority 8 — Deploy to Railway

- Add `Procfile`: `web: uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- Set environment variables in Railway: `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, `GEMINI_API_KEY`, `SUPABASE_URL`, `SUPABASE_KEY`
- Deploy from `claude/claude-md-docs-wqfhL` branch
- Test live HTTPS endpoint

---

## What This Session Confirmed Is NOT Priorities Yet

- Stem separation (Spleeter/Demucs) — post-Series A
- Audio generation (Suno API) — Phase 2, after schema is validated
- Layer 3 classifier training — needs 10,000+ evaluation records first
- Film domain agent (ScriptMaster) — after SyncMaster has paying users
- Multi-tenant config — after 50+ customers
- Framework migration (LangGraph etc.) — after first revenue

---

## Files That Must Not Be Touched

| File | Reason |
|---|---|
| `scripts/memory.py` | Superseded 3-argument logger. Do not reference. Delete in Stage 2 migration PR. |
| `memory/log.py` | Canonical — only change is adding `synthetic=False` parameter |
| `agents/base_agent.py` | Do not modify. All agents subclass this. |
| `agents/orchestrator.py` | Only change is `_run_llm` replacement. Nothing else. |

---

## Conventions to Maintain

- All agents subclass `BaseAgent`. Override only `analyze_task()`. Never override `run()`.
- `domain_weight > 1.0` only for primary commercial domain agents.
- Intent values are snake_case action strings: `sync_evaluation`, `metadata_extraction`, `threat_detection`.
- Gemini work order: Flash 2.0 (fusion brain) → 2.5 Pro (fallback) → 1.5 Pro (multimodal listener) → Flash 8B (cheap fallback).
- Every synthetic log entry carries `synthetic: true`.
- `task_log` = routing intelligence moat. `evaluation_log` = domain expertise moat. Never conflate them.

---

## The Honest Statement to Carry Into the Build Session

The architecture is complete. The moat thesis is validated. The precedents are real. The cofounder document is written.

**None of this matters until the first evaluation record is written to `evaluation_log`.**

The moat cannot accumulate from a planning document. Start with Priority 1. Do not open a new architecture conversation until Priorities 1–3 are done and a live endpoint exists.

---

*Session type: Research and Architecture — no code written*  
*Next session type: Build — code only*  
*Document status: Complete as of 2026-05-26*
