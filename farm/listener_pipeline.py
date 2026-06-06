"""
Listening Farm pipeline.
Layer 1: librosa DSP extraction (stdlib WAV fallback).
Layer 2: Gemini multimodal semantic evaluation.
Moat: write every evaluation to evaluation_log via Supabase.
"""

from __future__ import annotations
import os
import tempfile
import urllib.request
from typing import Any

from app.core.logging import get_logger
from farm.briefs import get_active_briefs
from farm.supabase_client import write_evaluation_log

logger = get_logger(__name__)


def process_uploaded_track(track_id: str, audio_url: str, synthetic: bool = False) -> dict[str, Any]:
    """Full pipeline: download → Layer 1 → Layer 2 × all briefs → moat write → return top 5."""
    ext = os.path.splitext(audio_url.split("?")[0])[1] or ".mp3"
    with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
        local_path = tmp.name
    urllib.request.urlretrieve(audio_url, local_path)

    metadata = _layer1_extract(local_path)
    briefs = get_active_briefs()

    def _evaluate_and_log(brief):
        result = _layer2_evaluate(local_path, brief, metadata)
        log_entry = {
            "track_id": track_id,
            "track_source": "generated" if synthetic else "artist_upload",
            "brief_id": brief["brief_id"],
            "placement_type": brief["placement_type"],
            "brief": brief,
            "fit_score": result["fit_score"],
            "strengths": result.get("strengths", []),
            "weaknesses": result.get("weaknesses", []),
            "recommendation": result.get("recommendation", "unknown"),
            "reasoning": result.get("reasoning", ""),
            "bpm_estimate": metadata.get("bpm"),
            "key_estimate": metadata.get("key"),
            "energy_level": metadata.get("energy"),
            "mood_tags": result.get("mood_tags", []),
            "listener_model": "gemini-2.5-flash",
            "synthetic": synthetic,
        }
        write_evaluation_log(log_entry)
        return {"brief": brief, **result}

    from concurrent.futures import ThreadPoolExecutor, as_completed
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(_evaluate_and_log, brief) for brief in briefs]
        evaluations = [f.result() for f in as_completed(futures)]

    top_matches = sorted(evaluations, key=lambda x: x["fit_score"], reverse=True)[:5]
    return {"metadata": metadata, "top_brief_matches": top_matches}


def _layer1_extract(audio_path: str) -> dict[str, Any]:
    """Extract DSP features. Uses librosa when available, falls back to stdlib WAV."""
    try:
        import librosa
        import numpy as np
        y, sr = librosa.load(audio_path, sr=None)
        tempo, _ = librosa.beat.beat_track(y=y, sr=sr)
        rms = float(librosa.feature.rms(y=y).mean())
        centroid = float(librosa.feature.spectral_centroid(y=y, sr=sr).mean())
        bpm = float(np.atleast_1d(tempo)[0])
        return {
            "bpm": bpm,
            "energy": min(rms * 10, 1.0),
            "spectral_centroid": centroid,
            "key": "unknown",
            "backend": "librosa",
        }
    except ImportError:
        return _layer1_wav_fallback(audio_path)


def _layer1_wav_fallback(audio_path: str) -> dict[str, Any]:
    """Standard-library WAV analysis when librosa is not installed."""
    import wave, struct, math
    try:
        with wave.open(audio_path, "r") as f:
            frames = f.readframes(f.getnframes())
            samples = struct.unpack(f"{len(frames) // 2}h", frames)
        rms = math.sqrt(sum(s * s for s in samples) / len(samples)) / 32768
        return {"bpm": 0.0, "energy": min(rms * 10, 1.0), "key": "unknown", "backend": "wave"}
    except Exception:
        return {"bpm": 0.0, "energy": 0.0, "key": "unknown", "backend": "error"}


def _layer2_evaluate(audio_path: str, brief: dict[str, Any], metadata: dict[str, Any]) -> dict[str, Any]:
    """Call Gemini Flash with audio + brief context. Rotates API keys automatically."""
    import json, re
    from google import genai

    ext = os.path.splitext(audio_path)[1].lower()
    mime_map = {".mp3": "audio/mpeg", ".wav": "audio/wav", ".ogg": "audio/ogg", ".flac": "audio/flac", ".m4a": "audio/mp4"}
    mime_type = mime_map.get(ext, "audio/mpeg")

    with open(audio_path, "rb") as f:
        audio_bytes = f.read()

    prompt = f"""You are a music supervisor evaluating a track for a sync placement.

Brief:
- Placement type: {brief['placement_type']}
- Tone required: {brief['tone']}
- Energy required: {brief['energy']}
- Vocal preference: {brief['vocal']}
- Keywords: {', '.join(brief.get('keywords', []))}

Track metadata (DSP analysis):
- Estimated BPM: {metadata.get('bpm', 'unknown')}
- Energy level: {metadata.get('energy', 'unknown')}
- Key: {metadata.get('key', 'unknown')}

Listen to the audio and respond ONLY with valid JSON:
{{
  "fit_score": <float 0.0-1.0>,
  "strengths": [<string>, ...],
  "weaknesses": [<string>, ...],
  "recommendation": "<approve|reject|modify>",
  "reasoning": "<one paragraph natural language judgment>",
  "mood_tags": [<string>, ...]
}}"""

    if os.environ.get("FARM_TEST_MODE") == "true":
        return {
            "fit_score": 0.82,
            "strengths": ["test mode — no Gemini call made"],
            "weaknesses": [],
            "recommendation": "approve",
            "reasoning": "Test mode evaluation. Set FARM_TEST_MODE=false to use real Gemini.",
            "mood_tags": ["test"],
        }

    from google.genai import types
    from farm.quota_manager import get_available_key, record_call, mark_exhausted

    for attempt in range(10):
        api_key = get_available_key()
        if api_key is None:
            return _evaluation_fallback("all keys exhausted for today")
        try:
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=[
                    prompt,
                    types.Part(inline_data=types.Blob(mime_type=mime_type, data=audio_bytes)),
                ],
            )
            record_call(api_key)
            text = response.text.strip()
            json_match = re.search(r"\{.*\}", text, re.DOTALL)
            if json_match:
                return json.loads(json_match.group())
        except Exception as e:
            err = str(e)
            if "429" in err or "RESOURCE_EXHAUSTED" in err:
                logger.warning(
                    "Gemini API key exhausted; marking and retrying",
                    extra={"api_key_suffix": api_key[-8:]},
                )
                mark_exhausted(api_key)
                continue
            logger.error("Gemini evaluation failed", exc_info=True)
            break

    return _evaluation_fallback("all keys exhausted or evaluation failed")


def _evaluation_fallback(reason: str) -> dict[str, Any]:
    return {
        "fit_score": 0.0,
        "strengths": [],
        "weaknesses": [reason],
        "recommendation": "reject",
        "reasoning": f"Evaluation could not be completed: {reason}.",
        "mood_tags": [],
    }
