"""
Dakol AI OS — World Cup Skill
Chains: FootballDataAgent → WorldCupContentAgent → LLM → structured output

LLM routing strategy:
  Short content (twitter, instagram, linkedin)  → Groq first (fast) → Gemini → Ollama
  Long content  (preview, spotlight, youtube)   → Gemini first      → Groq   → Ollama
"""

import os
import time
import requests
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from agents.football_data_agent import FootballDataAgent, get_match_by_id, get_matches, get_historical_h2h
from agents.worldcup_content_agent import WorldCupContentAgent

_football_agent = FootballDataAgent()
_content_agent = WorldCupContentAgent()

# Content types that are short — route to fast APIs first
_SHORT_CONTENT = {"twitter_thread", "instagram_caption", "linkedin_post"}
_LLM_TIMEOUT = 30  # seconds per model attempt


# ─── Groq ────────────────────────────────────────────────────────────────────

def _run_groq(system_prompt: str, user_prompt: str, max_tokens: int = 800) -> Optional[dict]:
    """Call Groq API (free tier, very fast). Returns None on any failure."""
    api_key = os.environ.get("GROQ_API_KEY", "")
    if not api_key:
        return None

    try:
        resp = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
            json={
                "model": "llama-3.1-70b-versatile",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "max_tokens": max_tokens,
                "temperature": 0.8,
            },
            timeout=_LLM_TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            text = data["choices"][0]["message"]["content"]
            tokens = data.get("usage", {}).get("total_tokens", len(text.split()))
            return {"text": text, "tokens": tokens, "model": "groq/llama-3.1-70b"}
        print(f"[worldcup_skill] Groq {resp.status_code}: {resp.text[:200]}")
    except Exception as e:
        print(f"[worldcup_skill] Groq failed: {e}")
    return None


# ─── Gemini ───────────────────────────────────────────────────────────────────

def _run_gemini(system_prompt: str, user_prompt: str, max_tokens: int = 800) -> Optional[dict]:
    """Call Gemini via quota manager. Tries all available keys before giving up."""
    try:
        from google import genai
        from farm.quota_manager import get_available_key, record_call
    except ImportError as e:
        print(f"[worldcup_skill] Gemini import failed: {e}")
        return None

    full_prompt = f"{system_prompt}\n\n{user_prompt}"
    tried_keys = set()

    for model_name in ("gemini-2.5-flash", "gemini-1.5-flash-8b"):
        for _ in range(7):  # max 7 keys
            api_key = get_available_key()
            if not api_key or api_key in tried_keys:
                break
            tried_keys.add(api_key)
            try:
                client = genai.Client(api_key=api_key)

                def _call():
                    return client.models.generate_content(
                        model=model_name, contents=full_prompt
                    )

                with ThreadPoolExecutor(max_workers=1) as ex:
                    future = ex.submit(_call)
                    response = future.result(timeout=_LLM_TIMEOUT)

                text = response.text or ""
                record_call(api_key)
                tokens = len(full_prompt.split()) + len(text.split())
                return {"text": text, "tokens": tokens, "model": model_name}

            except FuturesTimeout:
                print(f"[worldcup_skill] Gemini {model_name} timed out after {_LLM_TIMEOUT}s")
                break  # try next model
            except Exception as e:
                msg = str(e).lower()
                if "429" in msg or "quota" in msg or "rate" in msg:
                    print(f"[worldcup_skill] Gemini key rate-limited, rotating…")
                    continue  # try next key
                print(f"[worldcup_skill] Gemini {model_name} error: {e}")
                break  # non-rate-limit error, try next model

    return None


# ─── Ollama (local fallback) ──────────────────────────────────────────────────

def _run_ollama(system_prompt: str, user_prompt: str, max_tokens: int = 800) -> Optional[dict]:
    """Call local Ollama instance. Zero API cost, slower."""
    ollama_base = os.environ.get("OLLAMA_API_BASE", "http://127.0.0.1:11434")
    model = os.environ.get("OLLAMA_MODEL", "coder-pro:latest")

    try:
        resp = requests.post(
            f"{ollama_base}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "options": {"num_predict": max_tokens},
            },
            timeout=_LLM_TIMEOUT,
        )
        if resp.status_code == 200:
            data = resp.json()
            text = data.get("message", {}).get("content", "")
            tokens = len(user_prompt.split()) + len(text.split())
            return {"text": text, "tokens": tokens, "model": f"ollama/{model}"}
        print(f"[worldcup_skill] Ollama {resp.status_code}")
    except Exception as e:
        print(f"[worldcup_skill] Ollama failed: {e}")
    return None


# ─── Dispatcher ──────────────────────────────────────────────────────────────

def _generate(system_prompt: str, user_prompt: str, content_type: str, max_tokens: int) -> dict:
    """
    Route to the right LLM based on content type.
    Short → Groq first (fast, free). Long → Gemini first (quality).
    Ollama is always the last resort.
    """
    if content_type in _SHORT_CONTENT:
        chain = [_run_groq, _run_gemini, _run_ollama]
    else:
        chain = [_run_gemini, _run_groq, _run_ollama]

    for fn in chain:
        result = fn(system_prompt, user_prompt, max_tokens)
        if result and result.get("text"):
            return result

    return {
        "text": "Content generation temporarily unavailable. Please try again.",
        "tokens": 0,
        "model": "none",
    }


# ─── Main entry point ─────────────────────────────────────────────────────────

def generate_worldcup_content(
    match_id: str,
    content_type: str = "twitter_thread",
    user_id: str = "anonymous",
) -> dict:
    start = time.time()

    match = get_match_by_id(match_id)
    if not match:
        return {
            "content": "", "match": None, "content_type": content_type,
            "model": "none", "tokens": 0, "generation_time_ms": 0,
            "user_id": user_id, "status": "error",
            "error": f"Match '{match_id}' not found.",
        }

    h2h_summary = None
    home_team = match.get("home_team")
    away_team = match.get("away_team")
    if home_team and away_team:
        h2h_result = get_historical_h2h(home_team, away_team)
        if h2h_result:
            h2h_summary = h2h_result.get("summary")

    system_prompt, user_prompt = _content_agent.build_prompt(content_type, match, h2h_summary)
    max_tokens = _content_agent.get_max_tokens(content_type)

    llm_result = _generate(system_prompt, user_prompt, content_type, max_tokens)
    elapsed_ms = int((time.time() - start) * 1000)

    return {
        "content": llm_result["text"],
        "match": match,
        "content_type": content_type,
        "model": llm_result["model"],
        "tokens": llm_result["tokens"],
        "generation_time_ms": elapsed_ms,
        "user_id": user_id,
        "status": "ok",
    }


def list_available_matches() -> list[dict]:
    return get_matches()


def list_content_types() -> list[str]:
    from agents.worldcup_content_agent import CONTENT_PROMPTS
    return list(CONTENT_PROMPTS.keys())
