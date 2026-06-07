"""Supabase write client for evaluation_log. All moat writes go through here."""

from __future__ import annotations
import os
from typing import Any
from app.core.logging import get_logger

_client_instance = None
logger = get_logger(__name__)


def _get_client():
    global _client_instance
    if _client_instance is None:
        from supabase import create_client
        _client_instance = create_client(
            os.environ["SUPABASE_URL"],
            os.environ["SUPABASE_KEY"],
        )
    return _client_instance


def write_evaluation_log(entry: dict[str, Any]) -> dict[str, Any]:
    """Write one evaluation record to the moat table. Returns inserted row."""
    client = _get_client()
    response = client.table("evaluation_log").insert(entry).execute()
    return response.data[0] if response.data else {}


def get_unevaluated_tracks() -> list[dict[str, Any]]:
    """Fetch tracks that have audio and have not yet been evaluated."""
    client = _get_client()
    try:
        tracks_res = client.table("tracks").select("id, audio_url, title").execute()
        tracks = tracks_res.data or []
    except Exception:
        logger.error("Error fetching tracks", exc_info=True)
        return []

    valid_tracks = [track for track in tracks if track.get("audio_url")]
    if not valid_tracks:
        return []

    try:
        evals_res = client.table("evaluation_log").select("track_id").execute()
        evaluated_ids = {row["track_id"] for row in (evals_res.data or []) if row.get("track_id")}
    except Exception:
        logger.error("Error fetching evaluation logs", exc_info=True)
        evaluated_ids = set()

    return [track for track in valid_tracks if track["id"] not in evaluated_ids]


def get_user(user_id: str) -> dict[str, Any] | None:
    """Fetch user profile from the users table."""
    client = _get_client()
    try:
        res = client.table("users").select("tier, monthly_limit, daily_limit, daily_usage").eq("id", user_id).maybeSingle().execute()
        return res.data
    except Exception as e:
        logger.error(f"Error fetching user {user_id}", exc_info=True)
        return None


def get_monthly_output_count(user_id: str, start_iso: str) -> int:
    """Count content outputs for a user since the start of the month."""
    client = _get_client()
    try:
        res = client.table("content_outputs").select("id", count="exact").eq("user_id", user_id).gte("created_at", start_iso).execute()
        return res.count if res.count is not None else 0
    except Exception as e:
        logger.error(f"Error counting outputs for user {user_id}", exc_info=True)
        return 0


def increment_user_usage(user_id: str, tokens: int = 0, increment_generation: bool = True) -> dict[str, Any]:
    """Call the increment_usage RPC function."""
    client = _get_client()
    try:
        res = client.rpc("increment_usage", {
            "p_user_id": user_id,
            "p_tokens": tokens,
            "p_increment_generation": increment_generation
        }).execute()
        return res.data[0] if isinstance(res.data, list) and res.data else res.data
    except Exception as e:
        logger.error(f"Error incrementing usage for user {user_id}", exc_info=True)
        return {"allowed": True, "daily_usage": 0, "daily_limit": 0}
