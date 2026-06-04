"""
Gemini API key rotator. Cycles through all available keys round-robin.
Add keys via env vars: GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3, etc.
"""

from __future__ import annotations
import os
import itertools
from typing import Iterator

_cycle: Iterator[str] | None = None


def _load_keys() -> list[str]:
    keys = []
    primary = os.environ.get("GEMINI_API_KEY", "").strip()
    if primary:
        keys.append(primary)
    i = 2
    while True:
        key = os.environ.get(f"GEMINI_API_KEY_{i}", "").strip()
        if not key:
            break
        keys.append(key)
        i += 1
    
    # Append the paid key at the very end as a fallback
    paid_key = os.environ.get("GEMINI_PAID_API_KEY", "").strip()
    if paid_key:
        keys.append(paid_key)
    return keys


def get_next_key() -> str:
    global _cycle
    keys = _load_keys()
    if not keys:
        raise RuntimeError("No GEMINI_API_KEY found in environment.")
    if _cycle is None:
        _cycle = itertools.cycle(keys)
    return next(_cycle)


def key_count() -> int:
    return len(_load_keys())
