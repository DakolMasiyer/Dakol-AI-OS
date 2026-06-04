"""
Quota manager for Gemini API keys.
Tracks daily usage per key, enforces rate limits, handles backoff.
State persists in memory/quota_state.json and resets at UTC midnight.
"""

from __future__ import annotations
import json
import os
import threading
from datetime import datetime, timezone
from typing import Any

STATE_FILE = os.path.join(os.path.dirname(__file__), "..", "memory", "quota_state.json")
DAILY_LIMIT = 1400  # buffer below the 1500 free tier limit
_lock = threading.Lock()


def _today() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")


def _load_state() -> dict[str, Any]:
    try:
        with open(STATE_FILE) as f:
            state = json.load(f)
        if state.get("date") != _today():
            return {"date": _today(), "keys": {}}
        return state
    except (FileNotFoundError, json.JSONDecodeError):
        return {"date": _today(), "keys": {}}


def _save_state(state: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


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
