# Gemini Integration

## Why Gemini

The current stack has three LLM backends: Claude (reasoning/design), OpenAI GPT (code), and Ollama local (fusion brain + fallback). This creates three problems at scale:

1. **Local dependency** — the fusion brain calls `subprocess.run(["ollama", ...])`. This requires Ollama installed on the host machine. It cannot run on a cloud server without bringing Ollama along.
2. **Single reasoner** — Claude is the only high-quality reasoning option. If it rate-limits or goes down, there is no fallback for complex tasks.
3. **No multimodal capability** — the Film and Media domains will eventually need to process video, images, and audio files. None of the current backends support this.

Gemini addresses all three gaps.

## Four Model Assignments

| Gemini Model | Role in Dakol-AI-OS | Priority |
|---|---|---|
| **Gemini 2.5 Pro** | Reasoning peer to Claude. Augments or replaces `claude-3-5-sonnet` for architecture, strategy, and pipeline tasks. Adds a fallback when Claude rate-limits. | Medium |
| **Gemini 2.0 Flash** | Replaces Ollama `coder-pro:latest` as the **fusion brain**. Removes the subprocess dependency entirely. Makes the system fully cloud-native. | **Highest** |
| **Gemini 1.5 Pro** | Multimodal capability for Film and Media domains. Processes video transcripts, audio analysis, image-based tasks. New capability class the current stack does not have. | Low (post-Film/Media scope) |
| **Gemini Flash 8B** | Cheap, fast fallback for simple tasks. Replaces Ollama `local` routing for general explanations and basic analysis. | Medium |

## Where These Touch the Code

### `agents/orchestrator.py` — Replace the fusion brain (highest priority)

Current:
```python
def _run_llm(self, prompt: str):
    return subprocess.run(
        ["ollama", "run", "coder-pro:latest", prompt],
        capture_output=True, text=True
    ).stdout.strip()
```

Replace with:
```python
def _run_llm(self, prompt: str):
    import google.generativeai as genai
    model = genai.GenerativeModel("gemini-2.0-flash")
    response = model.generate_content(prompt)
    return response.text
```

This is the single change that removes the local Ollama dependency from the fusion brain.

### `skills/router_skills.py` — Add Gemini routing branch

Add a new `run_gemini()` function and a new branch in `analyze_task()`:

```python
# In analyze_task():
if any(keyword in t for keyword in ["video", "image", "multimodal", "transcript", "document", "summarise"]):
    return "gemini"

# New function:
def run_gemini(task: str) -> str:
    import google.generativeai as genai
    model = genai.GenerativeModel("gemini-1.5-pro")
    response = model.generate_content(task)
    return response.text
```

### New dependency

```bash
pip install google-generativeai
```

New `.env` key:
```
GEMINI_API_KEY=your-key-here
```

## Integration Priority

**Do these in order:**

1. **Replace Ollama fusion brain with Gemini 2.0 Flash** — this is the blocker for cloud deployment. Until the subprocess is removed, the system cannot run on Railway or any other cloud host. One function replacement in `orchestrator.py`.

2. **Add Gemini 2.5 Pro as a routing option** — adds resilience. When Claude rate-limits (as seen in `memory/logs.json`), tasks fall through to local instead of retrying with a capable model. Gemini 2.5 Pro plugs that gap.

3. **Add multimodal agents** — only after the Film/Media domain is properly scoped. Gemini 1.5 Pro is the engine; a `FilmAgent` or `MediaAgent` subclass would direct appropriate tasks toward it.

## Open Questions

- **Cost model** — Gemini Flash is priced per token; Ollama is free locally. At what task volume does Gemini Flash become more expensive than hosting an Ollama VPS? This needs modelling before committing to the full replacement.
- **Film domain model choice** — Gemini 1.5 Pro vs Claude 3.5 Sonnet for film licensing strategy. Claude is stronger at long-form reasoning; Gemini 1.5 Pro adds multimodal. The answer may be: Gemini for media analysis tasks, Claude for strategy/pipeline tasks, with the fusion brain deciding.
- **API key management** — with four providers (Anthropic, OpenAI, Google, Railway env), a secrets management pattern is needed before production. Railway env vars handle this for deployment; local dev uses `.env`.
