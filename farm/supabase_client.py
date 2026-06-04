"""Supabase write client for evaluation_log. All moat writes go through here."""

from __future__ import annotations
import os
from typing import Any

_client_instance = None


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
    """Fetch all tracks that have not been evaluated against briefs yet."""
    client = _get_client()
    try:
        # Fetch tracks
        tracks_res = client.table("tracks").select("id, audio_url, title").execute()
        tracks = tracks_res.data or []
    except Exception as e:
        print(f"[supabase_client] Error fetching tracks: {e}")
        return []

    valid_tracks = [t for t in tracks if t.get("audio_url")]
    if not valid_tracks:
        return []

    try:
        # Fetch evaluated track IDs
        evals_res = client.table("evaluation_log").select("track_id").execute()
        evaluated_ids = {row["track_id"] for row in evals_res.data if row.get("track_id")}
    except Exception as e:
        print(f"[supabase_client] Error fetching evaluation logs: {e}")
        evaluated_ids = set()

    # Filter to only return tracks that have not been evaluated
    return [t for t in valid_tracks if t["id"] not in evaluated_ids]

