import uuid
import asyncio
import contextvars
import urllib.request
import tempfile
import os as _os
import time
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from typing import Optional, Dict, Any
from pydantic import BaseModel
from runtime.environment import ensure_runtime_environment

RUNTIME_MANIFEST = ensure_runtime_environment(component="web")
from slowapi import Limiter
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from app.core.logging import configure_logging, get_logger
from app.core.tracing import TracingMiddleware
from core.api import route_task
from farm.listener_pipeline import process_uploaded_track
from skills.model_router import AllModelsUnavailableError, generate_with_fallback
import skills.worldcup_skill as worldcup_skill
from api.gateway.auth import require_auth
from api.gateway.router import gateway_router
from api.control_plane.routes import control_plane_router
from api.gateway.middleware import GatewayMiddleware

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

configure_logging()
logger = get_logger(__name__)
app = FastAPI(title="Dakol-AI-OS", version="1.0.0")
app.add_middleware(TracingMiddleware)
app.add_middleware(GatewayMiddleware)
app.state.runtime_manifest = RUNTIME_MANIFEST
logger.info(
    "Runtime environment validated",
    extra={
        "runtime_fingerprint": RUNTIME_MANIFEST["fingerprint"],
        "python_version": RUNTIME_MANIFEST["python_version"],
        "environment": RUNTIME_MANIFEST["environment"],
        "dependencies": RUNTIME_MANIFEST["dependencies"],
    },
)

app.include_router(gateway_router, prefix="/api")
app.include_router(control_plane_router, prefix="/api")

# Mount control plane UI securely (basic mounting for now)
import os
admin_ui_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "admin_ui")
app.mount("/admin", StaticFiles(directory=admin_ui_path, html=True), name="admin_ui")

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


class AnalyzeProfileRequest(BaseModel):
    url: Optional[str] = None
    handle: Optional[str] = None
    platform: Optional[str] = None


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
        
    from workflows.definitions import create_listening_farm_ingestion_workflow
    try:
        engine = create_listening_farm_ingestion_workflow("listening_farm", workflow_id=track_id)
        # Execute workflow synchronously for now
        res = engine.execute({
            "track_id": track_id,
            "audio_url": payload.audio_url,
            "synthetic": payload.synthetic
        })
        
        # If it completed, the evaluation result is in the payload
        if res.get("status") == "COMPLETED":
            return res.get("payload", {}).get("evaluation_result", {})
            
        return {"status": "error", "message": f"Workflow ended with status: {res.get('status')}"}
    except Exception as e:
        return {"error": str(e), "track_id": track_id}


class SyncmasterSubmitRequest(BaseModel):
    catalog_id: str
    items: list[dict[str, Any]]


@app.post("/syncmaster/submit")
def submit_catalog(payload: SyncmasterSubmitRequest):
    from workflows.definitions import create_syncmaster_submission_workflow
    try:
        engine = create_syncmaster_submission_workflow("syncmaster")
        res = engine.execute({
            "catalog_id": payload.catalog_id,
            "items": payload.items
        })
        
        return res
    except Exception as e:
        return {"error": str(e), "status": "failed"}


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
    import wave, struct, math, io
    from core.storage.local_storage import LocalStorageBackend
    
    storage = LocalStorageBackend()
    report = {"audio_url": payload.audio_url, "steps": {}, "test_mode": _os.environ.get("FARM_TEST_MODE") == "true"}

    use_generated = payload.audio_url == "local://test"
    if use_generated:
        track_id = "debug_gen_" + str(int(time.time()))
        logical_path = storage.generate_storage_path("farm/debug", f"{track_id}.wav")
        buffer = io.BytesIO()
        with wave.open(buffer, "w") as f:
            f.setnchannels(1); f.setsampwidth(2); f.setframerate(44100)
            samples = [int(32767 * math.sin(2 * math.pi * 440 * i / 44100)) for i in range(44100 * 3)]
            f.writeframes(struct.pack(f"{len(samples)}h", *samples))
        
        content = buffer.getvalue()
        storage.save_file(logical_path, content)
        report["steps"]["download"] = {"status": "ok", "size_kb": len(content) // 1024, "source": "generated"}
    else:
        try:
            ext = _os.path.splitext(payload.audio_url.split("?")[0])[1] or ".mp3"
            track_id = "debug_dl_" + str(int(time.time()))
            logical_path = storage.generate_storage_path("farm/debug", f"{track_id}{ext}")
            
            with urllib.request.urlopen(payload.audio_url) as resp:
                content = resp.read()
            storage.save_file(logical_path, content)
            
            report["steps"]["download"] = {"status": "ok", "size_kb": len(content) // 1024}
        except Exception as e:
            report["steps"]["download"] = {"status": "failed", "error": str(e)}
            return report

    try:
        from farm.listener_pipeline import _layer1_extract
        metadata = _layer1_extract(logical_path, storage)
        report["steps"]["layer1_dsp"] = {"status": "ok", "metadata": metadata}
    except Exception as e:
        report["steps"]["layer1_dsp"] = {"status": "failed", "error": str(e)}
        metadata = {}

    try:
        from farm.listener_pipeline import _layer2_evaluate
        from farm.briefs import BRIEF_LIBRARY
        result = _layer2_evaluate(logical_path, BRIEF_LIBRARY[0], metadata, storage)
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
async def worldcup_generate(
    request: Request,
    payload: WorldCupGenerateRequest,
    auth_user: Dict[str, Any] = Depends(require_auth),
):
    """
    Generate AI football content for a given match.
    Chains: FootballDataAgent → WorldCupContentAgent → Gemini (quota-rotated)
    Runs the blocking Gemini call in a thread so the event loop stays free.
    """
    if not payload.match_id:
        return {"error": "match_id is required"}

    # Identity always comes from the verified JWT sub claim, never from the request body.
    user_id = auth_user["sub"]
    if user_id == "anonymous":
        raise HTTPException(status_code=401, detail="Authentication required")

    from farm.supabase_client import get_user, get_monthly_output_count, increment_user_usage
    from datetime import datetime, timezone

    usage = increment_user_usage(user_id, tokens=0)
    if not usage.get("allowed", True):
        daily_limit = usage.get("daily_limit", 0)
        return JSONResponse(
            status_code=402,
            content={
                "error": f"You have reached your daily limit of {daily_limit} free generations. Please upgrade to Pro for unlimited access.",
                "status": "error",
                "code": "LIMIT_REACHED"
            }
        )

    db_user = get_user(user_id)
    if db_user and db_user.get("tier") != "pro":
        tier = db_user.get("tier", "free")
        custom_limit = db_user.get("monthly_limit")
        limits = {"free": 30, "starter": 200}
        monthly_limit = custom_limit if custom_limit is not None else limits.get(tier)

        if monthly_limit is not None:
            now = datetime.now(timezone.utc)
            start = datetime(now.year, now.month, 1, tzinfo=timezone.utc)
            if now.month == 12:
                reset = datetime(now.year + 1, 1, 1, tzinfo=timezone.utc)
            else:
                reset = datetime(now.year, now.month + 1, 1, tzinfo=timezone.utc)

            count = get_monthly_output_count(user_id, start.isoformat())
            if count >= monthly_limit:
                return JSONResponse(
                    status_code=402,
                    content={
                        "error": "monthly_limit_exceeded",
                        "reset_at": reset.isoformat()
                    }
                )

    from workflows.definitions import create_worldcup_generation_workflow
    try:
        start = time.perf_counter()
        engine = create_worldcup_generation_workflow("worldcup_ai")

        ctx = contextvars.copy_context()
        res = await asyncio.to_thread(
            ctx.run,
            engine.execute,
            {
                "match_id": payload.match_id,
                "content_type": payload.content_type,
                "user_id": user_id,
                "brand_profile": payload.brand_profile,
                "auto_publish": False,
            }
        )
        elapsed_ms = int((time.perf_counter() - start) * 1000)

        if res.get("status") == "COMPLETED":
            result = res.get("payload", {}).get("generation_result", {})
        else:
            result = {"status": "error", "error": f"Workflow failed or paused: {res.get('status')}"}

        logger.info(
            "Generate workflow completed",
            extra={
                "user_id": user_id,
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
            extra={"user_id": user_id, "content_type": payload.content_type},
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
            extra={"user_id": user_id, "content_type": payload.content_type},
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


@app.post("/worldcup/analyze-profile")
@limiter.limit("10/minute", key_func=get_remote_address)
async def worldcup_analyze_profile(
    request: Request,
    payload: AnalyzeProfileRequest,
    auth_user: Dict[str, Any] = Depends(require_auth),
):
    """Infer brand voice (tone, style notes, hashtags) from a public social profile.

    Best-effort and non-fatal: always returns a usable result so onboarding can
    proceed even when the profile can't be fetched.
    """
    from skills.profile_analyzer import analyze_profile

    try:
        return await asyncio.to_thread(
            analyze_profile,
            url=payload.url,
            handle=payload.handle,
            platform=payload.platform,
        )
    except Exception:
        logger.warning("analyze-profile failed", exc_info=True)
        return {
            "tone_key": "analytical",
            "style_notes": "",
            "suggested_hashtags": [],
            "coverage": "inferred",
            "status": "ok",
        }


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
