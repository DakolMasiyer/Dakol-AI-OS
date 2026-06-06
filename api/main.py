import uuid
import asyncio
import urllib.request
import tempfile
import os as _os
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from typing import Optional, Dict, Any
from pydantic import BaseModel
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from app.core.logging import configure_logging, get_logger
from scripts.router import route_task
from farm.listener_pipeline import process_uploaded_track
from skills.model_router import AllModelsUnavailableError, generate_with_fallback
import skills.worldcup_skill as worldcup_skill

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

configure_logging()
logger = get_logger(__name__)
app = FastAPI(title="Dakol-AI-OS", version="1.0.0")


def _generate_with_fallback_adapter(system_prompt: str, user_prompt: str, _content_type: str, max_tokens: int):
    prompt = f"{system_prompt}\n\n{user_prompt}".strip()
    routed = generate_with_fallback(prompt, max_tokens)
    return {
        "text": routed["content"],
        "tokens": len(routed["content"].split()),
        "model": routed["model"],
        "used_fallback": routed["used_fallback"],
    }


worldcup_skill._generate = _generate_with_fallback_adapter


def _user_id_rate_limit_key(request: Request) -> str:
    user_id = request.headers.get("x-user-id")
    if user_id:
        return f"user:{user_id}"
    return f"ip:{get_remote_address(request)}"


def _retry_after_seconds(exc: RateLimitExceeded) -> int:
    retry_after = getattr(exc, "retry_after", None)
    if retry_after is None:
        headers = getattr(exc, "headers", None) or {}
        retry_after = headers.get("Retry-After")
    try:
        return max(1, int(float(retry_after)))
    except (TypeError, ValueError):
        return 60


limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter


@app.exception_handler(RateLimitExceeded)
async def rate_limit_exceeded_handler(request: Request, exc: RateLimitExceeded):
    retry_after = _retry_after_seconds(exc)
    return JSONResponse(
        status_code=429,
        content={"error": "rate_limit", "retry_after": retry_after},
        headers={"Retry-After": str(retry_after)},
    )


# ============================================================
# WORLD CUP AI — REQUEST MODELS
# ============================================================

class WorldCupGenerateRequest(BaseModel):
    match_id: str
    content_type: str = "twitter_thread"
    user_id: str = "anonymous"
    brand_profile: Optional[Dict[str, Any]] = None


class WorldCupPostRequest(BaseModel):
    user_id: str
    platform: str
    content: str
    content_type: str


class TaskRequest(BaseModel):
    task: str


class EvaluateRequest(BaseModel):
    track_id: str
    audio_url: str
    synthetic: bool = False


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/task")
def handle_task(payload: TaskRequest):
    if not payload.task or len(payload.task) > 2000:
        return {"error": "invalid task"}
    result = route_task(payload.task)
    return {"output": result}


@app.post("/syncmaster/evaluate")
def evaluate_track(payload: EvaluateRequest):
    track_id = payload.track_id if payload.track_id else str(uuid.uuid4())
    try:
        uuid.UUID(track_id)
    except ValueError:
        track_id = str(uuid.uuid4())
    try:
        result = process_uploaded_track(
            track_id,
            payload.audio_url,
            synthetic=payload.synthetic,
        )
        return result
    except Exception as e:
        return {"error": str(e), "track_id": track_id}


@app.post("/syncmaster/batch-run")
def batch_run_evaluate():
    """Daily automated job: pulls unevaluated tracks from Supabase and evaluates them against briefs."""
    from farm.supabase_client import get_unevaluated_tracks
    from farm.listener_pipeline import process_uploaded_track
    
    try:
        unevaluated = get_unevaluated_tracks()
    except Exception as e:
        return {"error": f"Failed to retrieve unevaluated tracks: {e}", "evaluated": []}

    results = []
    for track in unevaluated:
        track_id = track.get("id")
        audio_url = track.get("audio_url")
        title = track.get("title", "Untitled Track")
        
        if not track_id or not audio_url:
            continue
            
        try:
            # Process track against all active briefs
            eval_res = process_uploaded_track(track_id, audio_url, synthetic=False)
            results.append({
                "track_id": track_id,
                "title": title,
                "status": "success",
                "matches_count": len(eval_res.get("top_brief_matches", []))
            })
        except Exception as e:
            results.append({
                "track_id": track_id,
                "title": title,
                "status": "failed",
                "error": str(e)
            })

    return {
        "status": "ok",
        "processed_count": len(results),
        "evaluated": results
    }


@app.get("/syncmaster/quota")
def quota_status():
    from farm.quota_manager import quota_summary
    return quota_summary()


@app.post("/syncmaster/debug")
def debug_evaluate(payload: EvaluateRequest):
    import wave, struct, math
    report = {"audio_url": payload.audio_url, "steps": {}, "test_mode": _os.environ.get("FARM_TEST_MODE") == "true"}

    # Generate a tiny 3-second WAV locally — no download needed for infra testing
    use_generated = payload.audio_url == "local://test"
    if use_generated:
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            local_path = tmp.name
        with wave.open(local_path, "w") as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(44100)
            samples = [int(32767 * math.sin(2 * math.pi * 440 * i / 44100)) for i in range(44100 * 3)]
            f.writeframes(struct.pack(f"{len(samples)}h", *samples))
        report["steps"]["download"] = {"status": "ok", "size_kb": _os.path.getsize(local_path) // 1024, "source": "generated"}
    else:
        try:
            ext = _os.path.splitext(payload.audio_url.split("?")[0])[1] or ".mp3"
            with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                local_path = tmp.name
            urllib.request.urlretrieve(payload.audio_url, local_path)
            size_kb = _os.path.getsize(local_path) // 1024
            report["steps"]["download"] = {"status": "ok", "size_kb": size_kb}
        except Exception as e:
            report["steps"]["download"] = {"status": "failed", "error": str(e)}
            return report

    try:
        from farm.listener_pipeline import _layer1_extract
        metadata = _layer1_extract(local_path)
        report["steps"]["layer1_dsp"] = {"status": "ok", "metadata": metadata}
    except Exception as e:
        report["steps"]["layer1_dsp"] = {"status": "failed", "error": str(e)}
        metadata = {}

    try:
        from farm.listener_pipeline import _layer2_evaluate
        from farm.briefs import BRIEF_LIBRARY
        result = _layer2_evaluate(local_path, BRIEF_LIBRARY[0], metadata)
        report["steps"]["layer2_gemini"] = {"status": "ok", "result": result}
    except Exception as e:
        report["steps"]["layer2_gemini"] = {"status": "failed", "error": str(e)}

    try:
        from farm.supabase_client import write_evaluation_log
        write_evaluation_log({
            "track_id": "00000000-0000-0000-0000-000000000001",
            "brief_id": "debug",
            "fit_score": 0.0,
            "synthetic": True,
        })
        report["steps"]["supabase_write"] = {"status": "ok"}
    except Exception as e:
        report["steps"]["supabase_write"] = {"status": "failed", "error": str(e)}

    return report


# ============================================================
# WORLD CUP AI — ENDPOINTS
# ============================================================

@app.post("/worldcup/generate")
@limiter.limit("10/minute", key_func=get_remote_address)
@limiter.limit("30/minute", key_func=_user_id_rate_limit_key)
async def worldcup_generate(request: Request, payload: WorldCupGenerateRequest):
    """
    Generate AI football content for a given match.
    Chains: FootballDataAgent → WorldCupContentAgent → Gemini (quota-rotated)
    Runs the blocking Gemini call in a thread so the event loop stays free.
    """
    if not payload.match_id:
        return {"error": "match_id is required"}

    from skills.worldcup_skill import generate_worldcup_content
    try:
        start = time.perf_counter()
        result = await asyncio.to_thread(
            generate_worldcup_content,
            match_id=payload.match_id,
            content_type=payload.content_type,
            user_id=payload.user_id,
            brand_profile=payload.brand_profile,
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)
        logger.info(
            "Generate request completed",
            extra={
                "user_id": payload.user_id,
                "content_type": payload.content_type,
                "llm_response_time_ms": result.get("generation_time_ms", elapsed_ms),
            },
        )
        if result.get("status") == "invalid_match_status":
            raise HTTPException(status_code=400, detail=result["error"])
        return result
    except AllModelsUnavailableError as e:
        logger.warning(
            "All generation models unavailable",
            extra={"user_id": payload.user_id, "content_type": payload.content_type},
        )
        return JSONResponse(
            status_code=503,
            content={
                "error": "all_models_unavailable",
                "message": str(e),
            },
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "Generate request failed",
            extra={"user_id": payload.user_id, "content_type": payload.content_type},
        )
        return {"error": str(e), "status": "error"}


@app.get("/worldcup/matches")
def worldcup_matches():
    """Return all available World Cup matches (live API or mock WC2026)."""
    from skills.worldcup_skill import list_available_matches
    try:
        return {"matches": list_available_matches(), "status": "ok"}
    except Exception as e:
        return {"error": str(e), "matches": [], "status": "error"}


@app.get("/worldcup/content-types")
def worldcup_content_types():
    """Return all supported content generation types."""
    from skills.worldcup_skill import list_content_types
    return {"content_types": list_content_types()}


@app.post("/worldcup/post")
async def worldcup_post(payload: WorldCupPostRequest):
    """Post generated football content to a connected social account."""
    try:
        from skills.posting_skill import post_generated_content

        return await asyncio.to_thread(
            post_generated_content,
            user_id=payload.user_id,
            platform=payload.platform,
            content=payload.content,
        )
    except Exception as e:
        return {"error": str(e), "status": "error"}
