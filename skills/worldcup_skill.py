"""
Dakol AI OS — World Cup Skill
Chains: FootballDataAgent → WorldCupContentAgent → LLM → structured output

LLM routing strategy:
  Short content (twitter, instagram, linkedin)  → Groq first (fast) → Gemini → Hugging Face
  Long content  (preview, spotlight, youtube)   → Gemini first      → Groq   → Hugging Face
"""

import os
import time
import requests
from typing import Optional
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout
from agents.football_data_agent import (
    FootballDataAgent, get_match_by_id, get_matches,
    get_historical_h2h, get_squad_context,
    get_wc_standings_context, get_top_scorers_context,
)
from agents.worldcup_content_agent import WorldCupContentAgent
from app.core.logging import get_logger
from skills.model_router import generate_with_fallback

_football_agent = FootballDataAgent()
_content_agent = WorldCupContentAgent()
logger = get_logger(__name__)

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
                "model": "llama-3.3-70b-versatile",
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
            return {"text": text, "tokens": tokens, "model": "groq/llama-3.3-70b"}
        logger.warning(
            "Groq returned non-200 status",
            extra={"status_code": resp.status_code, "response_preview": resp.text[:200]},
        )
    except Exception as e:
        logger.error("Groq request failed", exc_info=True)
    return None


# ─── Gemini ───────────────────────────────────────────────────────────────────

def _run_gemini(system_prompt: str, user_prompt: str, max_tokens: int = 800) -> Optional[dict]:
    """Call Gemini via quota manager. Tries all available keys before giving up."""
    try:
        from google import genai
        from farm.quota_manager import get_available_key, record_call
    except ImportError as e:
        logger.error("Gemini import failed", exc_info=True)
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

                import contextvars
                ctx = contextvars.copy_context()
                with ThreadPoolExecutor(max_workers=1) as ex:
                    future = ex.submit(ctx.run, _call)
                    response = future.result(timeout=_LLM_TIMEOUT)

                text = response.text or ""
                record_call(api_key)
                tokens = len(full_prompt.split()) + len(text.split())
                return {"text": text, "tokens": tokens, "model": model_name}

            except FuturesTimeout:
                logger.warning(
                    "Gemini request timed out",
                    extra={"model": model_name, "timeout_seconds": _LLM_TIMEOUT},
                )
                break  # try next model
            except Exception as e:
                msg = str(e).lower()
                if "429" in msg or "quota" in msg or "rate" in msg:
                    logger.warning("Gemini key rate-limited; rotating", extra={"model": model_name})
                    continue  # try next key
                logger.error("Gemini request failed", extra={"model": model_name}, exc_info=True)
                break  # non-rate-limit error, try next model

    return None


# ─── Dispatcher ──────────────────────────────────────────────────────────────

def _generate(system_prompt: str, user_prompt: str, content_type: str, max_tokens: int) -> dict:
    """
    Route to the shared fallback chain.
    Prompt assembly already carries the content-type specific instructions.
    """
    prompt = f"{system_prompt}\n\n{user_prompt}".strip()

    try:
        result = generate_with_fallback(prompt, max_tokens)
        content = result.get("content", "")
        return {
            "text": content,
            "tokens": len(prompt.split()) + len(content.split()),
            "model": result.get("model", "none"),
        }
    except Exception:
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
    brand_profile: dict = None,
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

    status_rules = {
        'post_match_analysis': ['finished'],
        'match_preview': ['scheduled'],
    }
    allowed_statuses = status_rules.get(content_type)
    if allowed_statuses and match.get('status') not in allowed_statuses:
        return {
            "content": "",
            "match": match,
            "content_type": content_type,
            "model": "none",
            "tokens": 0,
            "generation_time_ms": int((time.time() - start) * 1000),
            "user_id": user_id,
            "status": "invalid_match_status",
            "error": (
                "Post-match analysis is only available for finished matches."
                if content_type == "post_match_analysis"
                else "Match preview is only available for upcoming matches."
            ),
        }

    home_team = match.get("home_team", "")
    away_team = match.get("away_team", "")

    # ── Fetch all enrichment context in parallel ──────────────────────────────
    h2h_summary      = None
    squad_home       = None
    squad_away       = None
    standings        = None
    top_scorers      = None

    def _safe(fn, *args, **kwargs):
        try:
            return fn(*args, **kwargs)
        except Exception as e:
            logger.error("Context fetch failed", extra={"function": fn.__name__}, exc_info=True)
            return None

    import contextvars
    ctx = contextvars.copy_context()
    with ThreadPoolExecutor(max_workers=5) as pool:
        f_h2h       = pool.submit(ctx.run, _safe, get_historical_h2h,       home_team, away_team)
        f_squad_h   = pool.submit(ctx.run, _safe, get_squad_context,         home_team)
        f_squad_a   = pool.submit(ctx.run, _safe, get_squad_context,         away_team)
        f_standings = pool.submit(ctx.run, _safe, get_wc_standings_context,  home_team)
        f_scorers   = pool.submit(ctx.run, _safe, get_top_scorers_context)

        h2h_result  = f_h2h.result(timeout=8)
        squad_home  = f_squad_h.result(timeout=8)
        squad_away  = f_squad_a.result(timeout=8)
        standings   = f_standings.result(timeout=8)
        top_scorers = f_scorers.result(timeout=8)

    if h2h_result:
        h2h_summary = h2h_result.get("summary")

    tone = brand_profile or {}

    system_prompt, user_prompt = _content_agent.build_prompt(
        content_type, match,
        h2h_context=h2h_summary,
        squad_home=squad_home,
        squad_away=squad_away,
        standings_context=standings,
        top_scorers_context=top_scorers,
        tone=tone,
    )
    max_tokens = _content_agent.get_max_tokens(content_type)

    llm_result = _generate(system_prompt, user_prompt, content_type, max_tokens)
    elapsed_ms = int((time.time() - start) * 1000)

    if llm_result["model"] == "none":
        return {
            "content": "",
            "match": match,
            "content_type": content_type,
            "model": "none",
            "tokens": 0,
            "generation_time_ms": elapsed_ms,
            "user_id": user_id,
            "status": "error",
            "error": "AI generation service is temporarily at capacity (rate limits reached). Please try again in a few minutes or upgrade to Pro.",
        }

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
