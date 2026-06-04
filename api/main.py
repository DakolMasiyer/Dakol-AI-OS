import uuid
import asyncio
import urllib.request
import tempfile
import os as _os
from fastapi import FastAPI
from typing import Optional, Dict, Any
from pydantic import BaseModel
from scripts.router import route_task
from farm.listener_pipeline import process_uploaded_track

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass

app = FastAPI(title="Dakol-AI-OS", version="1.0.0")


# ============================================================
# WORLD CUP AI — REQUEST MODELS
# ============================================================

class WorldCupGenerateRequest(BaseModel):
    match_id: str
    content_type: str = "twitter_thread"
    user_id: str = "anonymous"
    brand_profile: Optional[Dict[str, Any]] = None


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
async def worldcup_generate(payload: WorldCupGenerateRequest):
    """
    Generate AI football content for a given match.
    Chains: FootballDataAgent → WorldCupContentAgent → Gemini (quota-rotated)
    Runs the blocking Gemini call in a thread so the event loop stays free.
    """
    if not payload.match_id:
        return {"error": "match_id is required"}

    from skills.worldcup_skill import generate_worldcup_content
    try:
        result = await asyncio.to_thread(
            generate_worldcup_content,
            match_id=payload.match_id,
            content_type=payload.content_type,
            user_id=payload.user_id,
            brand_profile=payload.brand_profile,
        )
        return result
    except Exception as e:
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
