# PRD: World Cup AI Content Generator
**Project:** Dakol AI OS — World Cup Module  
**Date:** 2026-06-06  
**Status:** In Production (Beta)

---

## 1. Product Overview

The World Cup AI Content Generator is a vertical feature built on top of the Dakol AI OS multi-agent platform. It enables creators, sports brands, and media accounts to generate publication-ready football content — Twitter threads, Instagram captions, match previews, post-match analyses, player spotlights, LinkedIn posts, and YouTube scripts — fully automatically and grounded in live match data.

**Core value proposition:** One click → data-grounded, tone-matched, platform-optimised football content in under 5 seconds.

---

## 2. Goals

| Goal | Metric |
|------|--------|
| Zero-prompt content generation | User selects match + content type; no copywriting required |
| Data-grounded output | All content enriched with H2H history, squad info, standings, top scorers |
| Tone control | 5 selectable tones (hype, analytical, casual, professional, editorial) per content type |
| Cost-zero first-tier | Groq free tier as primary LLM for short content; Gemini free tier for long |
| Resilience | 3-model fallback chain; no single point of LLM failure |
| Speed | < 5s end-to-end (target), including all parallel data fetches |

---

## 3. Architecture

### 3.1 System Overview

```
User Request (match_id + content_type + tone)
        │
        ▼
┌───────────────────────────────────────────────┐
│              FastAPI  (api/main.py)            │
│  POST /worldcup/generate                      │
│  GET  /worldcup/matches                        │
│  GET  /worldcup/content-types                 │
└───────────────┬───────────────────────────────┘
                │  asyncio.to_thread()
                ▼
┌───────────────────────────────────────────────┐
│         worldcup_skill.generate_worldcup_content│
│         (skills/worldcup_skill.py)            │
│                                               │
│  1. Match lookup (get_match_by_id)            │
│  2. Status guard (preview/analysis gating)    │
│  3. Parallel context fetch [5 threads]        │
│  4. Prompt assembly (build_prompt)            │
│  5. LLM dispatch (_generate)                  │
└──────┬──────────────┬────────────────┬────────┘
       │              │                │
       ▼              ▼                ▼
 FootballDataAgent  WorldCupContentAgent  LLM Chain
```

### 3.2 Agent Layer

#### FootballDataAgent (`agents/football_data_agent.py`)
- **Role:** Data ingestion and normalisation
- `domain_weight`: 1.4
- **Primary source:** football-data.org API (`FOOTBALL_DATA_API_KEY`)
- **Mock fallback:** 8 hardcoded WC2026 fixtures (no API key needed)
- **Cache:** In-memory, 12h TTL for matches/squads, 30min for standings/scorers
- **Backup APIs:** RapidAPI (api-football-v1) and a generic REST slot, both wired but opt-in via env vars
- **Parallel context fetches:**
  - `get_historical_h2h` → Supabase `historical_matches` table
  - `get_squad_context` (home) → football-data.org `/teams/{id}`
  - `get_squad_context` (away) → football-data.org `/teams/{id}`
  - `get_wc_standings_context` → football-data.org `/competitions/WC/standings`
  - `get_top_scorers_context` → football-data.org `/competitions/WC/scorers`

#### WorldCupContentAgent (`agents/worldcup_content_agent.py`)
- **Role:** Prompt engineering and content specification
- `domain_weight`: 1.5
- **Content types:** `twitter_thread`, `instagram_caption`, `match_preview`, `post_match_analysis`, `player_spotlight`, `linkedin_post`, `youtube_script`
- **Tone modes:** `hype`, `analytical`, `casual`, `professional`, `editorial`
- **Prompt assembly:**
  - System prompt = content-type persona + tone directive (MANDATORY override) + tone-matched few-shot example
  - User prompt = match template + all available enrichment blocks (H2H, squads, standings, scorers)
- **Few-shot coverage:** 25+ curated examples keyed by `(content_type, tone)` pairs
- **Token budgets:** 300 (Instagram) → 800 (Twitter thread) by content type

### 3.3 LLM Dispatch Chain (`skills/worldcup_skill.py`)

```
Short content (twitter / instagram / linkedin):
  Groq (llama-3.3-70b, free)  →  Gemini  →  Hugging Face Inference API

Long content (preview / spotlight / youtube / analysis):
  Gemini (2.5-flash → 1.5-flash-8b)  →  Groq  →  Hugging Face Inference API
```

| Model | Provider | Cost | Speed | Notes |
|-------|----------|------|-------|-------|
| llama-3.3-70b-versatile | Groq | Free | ~1–2s | Primary for short content |
| gemini-2.5-flash | Google | Free tier | ~2–4s | Primary for long content |
| gemini-1.5-flash-8b | Google | Free tier | ~1–3s | Gemini fallback model |
| mistralai/Mistral-7B-Instruct-v0.3 | Hugging Face Inference API | Free tier | ~2–5s | Last-resort fallback |

**LLM timeout:** 30s per model attempt  
**Gemini quota management:** `farm/quota_manager.py` — rotates across up to 7 API keys, 1400 calls/day/key, auto-resets at UTC midnight, state persisted in `memory/quota_state.json`

### 3.4 Data Layer

#### Live Match Data
- Source: football-data.org v4 API
- Normalised schema: `id`, `external_id`, `home_team`, `away_team`, `home_team_flag`, `away_team_flag`, `stage`, `status`, `date`, `venue`, `score`, `competition`
- Graceful mock fallback: 8 WC2026 fixtures served when `FOOTBALL_DATA_API_KEY` not set

#### Historical Head-to-Head
- Source: Supabase `historical_matches` table
- Fields: `year`, `tournament`, `home_team`, `away_team`, `home_score`, `away_score`, `city`, `neutral`
- Populated via `scripts/import_historical_matches.py`
- Summarised into natural-language paragraphs before injection into prompts

#### Evaluation / Logging
- Supabase `evaluation_log` table (shared with SyncMaster module)
- Per-generation: `track_id`, `fit_score`, `listener_model`, `evaluated_at`

### 3.5 API Endpoints

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/worldcup/generate` | Generate content for a match |
| `GET` | `/worldcup/matches` | List all available matches |
| `GET` | `/worldcup/content-types` | List supported content types |
| `GET` | `/health` | Health check |

**Generate request body:**
```json
{
  "match_id": "wc2026-001",
  "content_type": "twitter_thread",
  "user_id": "user_abc",
  "brand_profile": { "tone": "analytical" }
}
```

**Generate response:**
```json
{
  "content": "...",
  "match": { ... },
  "content_type": "twitter_thread",
  "model": "groq/llama-3.3-70b",
  "tokens": 412,
  "generation_time_ms": 1823,
  "user_id": "user_abc",
  "status": "ok"
}
```

---

## 4. Content Types Reference

| Type | Token Budget | Primary LLM | Status Constraint |
|------|-------------|-------------|-------------------|
| `twitter_thread` | 800 | Groq | None |
| `instagram_caption` | 300 | Groq | None |
| `linkedin_post` | 400 | Groq | None |
| `match_preview` | 600 | Gemini | `scheduled` matches only |
| `post_match_analysis` | 700 | Gemini | `finished` matches only |
| `player_spotlight` | 500 | Gemini | None |
| `youtube_script` | 600 | Gemini | None |

---

## 5. Tone System

Each tone overrides the base system prompt with mandatory directives AND a curated few-shot example. Tones are injected at the top of the system prompt to maximise model adherence.

| Tone | Voice | Format signals |
|------|-------|----------------|
| `hype` | Fan who can't breathe | UPPERCASE moments, emojis, short punchy sentences |
| `analytical` | Tactical journalist | xG, pressing triggers, half-space; max 1 emoji/tweet |
| `casual` | Funny self-aware fan | Lowercase, arrow lists, reaction format, 😭 |
| `professional` | Data-led analyst | Cited stats, no emojis, formal verdict |
| `editorial` | Literary narrator | Slow-burn, narrative arc, minimal hashtags |

---

## 6. Current Build Status

### What's Working
- Full generation pipeline: match lookup → parallel context fetch → prompt assembly → LLM dispatch → structured response
- All 7 content types with 5 tones each (25+ few-shot examples)
- Groq/Gemini/Hugging Face 3-tier fallback chain
- Gemini multi-key rotation and daily quota management
- Mock fixture fallback (no API key required to run)
- Historical H2H from Supabase with city/tournament/neutral context
- Squad + coach injection (home and away)
- Group standings + tournament top scorers injection
- Status guards (preview = scheduled only, analysis = finished only)
- `asyncio.to_thread` wrapper so generation doesn't block the event loop
- Parallel context fetch with 8s timeout per thread

### Known Gaps / Next Steps

| Gap | Priority | Notes |
|-----|----------|-------|
| Supabase H2H data population | High | `import_historical_matches.py` exists but data must be seeded |
| Real-time score updates (live match) | Medium | API currently only polls at request time; no WebSocket push |
| User brand profile storage | Medium | `brand_profile` accepted per-request but not persisted |
| Content history / library | Medium | Generated content not stored; no re-fetch or edit flow |
| Rate limit UX | Medium | Error message returned but no user-facing retry timer |
| Backup API #1 (RapidAPI) wiring | Low | Functions exist; needs `BACKUP_FOOTBALL_API_KEY_1` in env |
| Embedding-backed squad match | Low | Squad fetched by name → ID; fuzzy name matching not yet in place |
| `youtube_script` tone coverage | Low | Only `hype` few-shot defined; other tones use analytical fallback |

---

## 7. Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `FOOTBALL_DATA_API_KEY` | Recommended | Live match data from football-data.org |
| `GROQ_API_KEY` | Recommended | Primary LLM for short content |
| `GEMINI_API_KEY_1..N` | Recommended | Primary LLM for long content (multi-key rotation) |
| `SUPABASE_URL` | For H2H | Historical head-to-head database |
| `SUPABASE_KEY` | For H2H | Supabase service role key |
| `HF_API_TOKEN` | Optional | Hugging Face Inference API token for the free fallback model |
| `BACKUP_FOOTBALL_API_KEY_1` | Optional | RapidAPI football backup |
| `BACKUP_FOOTBALL_API_HOST_1` | Optional | RapidAPI host header |

---

## 8. Key Files

```
api/main.py                          — FastAPI routes (/worldcup/*)
skills/worldcup_skill.py             — Orchestration: data → prompt → LLM → response
agents/worldcup_content_agent.py     — Prompt templates, few-shot examples, tone directives
agents/football_data_agent.py        — Live data, mock fallback, H2H, squads, standings
farm/quota_manager.py                — Gemini multi-key rotation + daily quota state
farm/key_rotator.py                  — Key loading from env
db/supabase_schema.sql               — Database schema (evaluation_log, tracks)
scripts/import_historical_matches.py — Supabase H2H seeding script
memory/quota_state.json              — Runtime quota tracking (auto-generated)
```

---

## 9. Data Flow Sequence

```
POST /worldcup/generate
  │
  ├── 1. Validate match_id → get_match_by_id()
  │       ├── Search live API cache
  │       └── Fall back to MOCK_FIXTURES
  │
  ├── 2. Status guard
  │       ├── post_match_analysis → must be "finished"
  │       └── match_preview → must be "scheduled"
  │
  ├── 3. Parallel fetch (ThreadPoolExecutor, 5 workers, 8s timeout each)
  │       ├── get_historical_h2h(home, away)  → Supabase
  │       ├── get_squad_context(home)          → football-data.org
  │       ├── get_squad_context(away)          → football-data.org
  │       ├── get_wc_standings_context(home)   → football-data.org
  │       └── get_top_scorers_context()        → football-data.org
  │
  ├── 4. Prompt assembly (WorldCupContentAgent.build_prompt)
  │       ├── Base system prompt from CONTENT_PROMPTS
  │       ├── Tone directive (mandatory override)
  │       ├── Few-shot example (keyed by content_type + tone)
  │       └── User prompt = template + enrichment blocks
  │
  └── 5. LLM dispatch (_generate)
          ├── Short → Groq → Gemini (key rotation) → Hugging Face
          └── Long  → Gemini (key rotation) → Groq → Hugging Face
```

---

## 10. Deployment

- **Runtime:** FastAPI via `Procfile` / `Dockerfile`
- **Hosting:** Google Cloud Run (configured via `.gcloudignore`)
- **Local:** `uvicorn api.main:app` from repo root
- **Dependencies:** `requirements.txt` (fastapi, uvicorn, supabase, google-genai, requests, python-dotenv)
