"""
Quota manager for Gemini API keys.
Tracks daily usage per key, enforces rate limits, handles backoff.
State persists in Supabase and resets at UTC midnight.
"""

from __future__ import annotations
import threading
from datetime import datetime, timezone
from typing import Any

QUOTA_STATE_KEY = "gemini_daily_quota"
DAILY_LIMIT = 1400  # buffer below the 1500 free tier limit
_lock = threading.Lock()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _get_client():
    from farm.supabase_client import _get_client as get_supabase_client
    return get_supabase_client()


def _load_state() -> dict[str, Any]:
    response = (
        _get_client()
        .table("quota_state")
        .select("value")
        .eq("key", QUOTA_STATE_KEY)
        .limit(1)
        .execute()
    )
    rows = response.data or []
    if not rows:
        return {"date": _today(), "keys": {}}
    state = rows[0].get("value") or {}
    if state.get("date") != _today():
        return {"date": _today(), "keys": {}}
    return state


def _save_state(state: dict[str, Any]) -> None:
    _get_client().table("quota_state").upsert(
        {
            "key": QUOTA_STATE_KEY,
            "value": state,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        },
        on_conflict="key",
    ).execute()


def get_available_key() -> str | None:
    """Return the first key with remaining daily quota. None if all exhausted."""
    from farm.key_rotator import _load_keys
    with _lock:
        state = _load_state()
        keys = _load_keys()
        for key in keys:
            key_id = key[-8:]
            info = state["keys"].get(key_id, {"count": 0, "exhausted": False})
            if info.get("exhausted"):
                continue
            if info["count"] >= DAILY_LIMIT:
                info["exhausted"] = True
                state["keys"][key_id] = info
                _save_state(state)
                continue
            return key
    return None


def record_call(key: str) -> None:
    """Increment the call counter for a key."""
    with _lock:
        state = _load_state()
        key_id = key[-8:]
        info = state["keys"].get(key_id, {"count": 0, "exhausted": False})
        info["count"] += 1
        state["keys"][key_id] = info
        _save_state(state)


def mark_exhausted(key: str) -> None:
    """Mark a key as quota-exhausted for today."""
    with _lock:
        state = _load_state()
        key_id = key[-8:]
        info = state["keys"].get(key_id, {"count": 0, "exhausted": False})
        info["exhausted"] = True
        state["keys"][key_id] = info
        _save_state(state)


def quota_summary() -> dict[str, Any]:
    """Return current quota status for all keys."""
    from farm.key_rotator import _load_keys
    with _lock:
        state = _load_state()
        keys = _load_keys()
        summary = {"date": state["date"], "keys": [], "total_remaining": 0}
        for key in keys:
            key_id = key[-8:]
            info = state["keys"].get(key_id, {"count": 0, "exhausted": False})
            remaining = max(0, DAILY_LIMIT - info["count"])
            summary["keys"].append({
                "key_id": f"...{key_id}",
                "calls_today": info["count"],
                "remaining": remaining,
                "exhausted": info.get("exhausted", False),
            })
            if not info.get("exhausted") and remaining > 0:
                summary["total_remaining"] += remaining
        return summary
