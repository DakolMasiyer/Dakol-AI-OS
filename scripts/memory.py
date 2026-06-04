"""Compatibility wrapper for the canonical memory logger.

Older code imported memory helpers from ``scripts.memory``. Keep that import
path working, but route all behavior through ``memory.log`` so there is only
one logger implementation.
"""

from memory import log as _memory_log


MEMORY_FILE = _memory_log.MEMORY_FILE


def _with_legacy_memory_file(func, *args):
    canonical_memory_file = _memory_log.MEMORY_FILE
    _memory_log.MEMORY_FILE = MEMORY_FILE
    try:
        return func(*args)
    finally:
        _memory_log.MEMORY_FILE = canonical_memory_file


def load_memory():
    return _with_legacy_memory_file(_memory_log.load_memory)


def save_memory(data):
    return _with_legacy_memory_file(_memory_log.save_memory, data)


def log_event(task, model, output, agent_result=None):
    return _with_legacy_memory_file(_memory_log.log_event, task, model, output, agent_result)


def record_feedback(event_id, feedback, note=None):
    return _with_legacy_memory_file(_memory_log.record_feedback, event_id, feedback, note)
