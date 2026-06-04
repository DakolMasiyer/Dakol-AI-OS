import json
import os
from collections import defaultdict
from datetime import datetime
from typing import Optional

from memory.log import MEMORY_FILE, load_memory


BASE_DIR = os.path.dirname(os.path.dirname(__file__))
LEARNING_STATE_FILE = os.path.join(BASE_DIR, "memory", "learning_state.json")
FEEDBACK_SCORE_ADJUSTMENTS = {
    "good": 0.2,
    "bad": -0.35,
    "wrong_model": -0.55,
    "retry_needed": -0.25,
}


def load_learning_state(path: str = LEARNING_STATE_FILE) -> dict:
    try:
        with open(path, "r") as file:
            data = json.load(file)
            return data if isinstance(data, dict) else _empty_learning_state()
    except (FileNotFoundError, json.JSONDecodeError):
        return _empty_learning_state()


def save_learning_state(state: dict, path: str = LEARNING_STATE_FILE) -> None:
    with open(path, "w") as file:
        json.dump(state, file, indent=2)


def update_learning_state(logs_path: str = MEMORY_FILE, state_path: str = LEARNING_STATE_FILE) -> dict:
    logs = _load_logs_from_path(logs_path)
    state = analyze_logs(logs)
    save_learning_state(state, state_path)
    return state


def analyze_logs(entries: list[dict]) -> dict:
    state = _empty_learning_state()
    scored_events = [score_event(entry) for entry in entries]

    state["event_count"] = len(scored_events)
    state["updated_at"] = datetime.now().isoformat()

    intent_stats = defaultdict(_stats_bucket)
    model_stats = defaultdict(_stats_bucket)
    agent_stats = defaultdict(_stats_bucket)

    for event in scored_events:
        intent = event["intent"]
        model = event["model_used"]
        best_agent = event["best_agent"]

        _add_event(intent_stats[intent], event)
        _add_event(model_stats[model], event)

        if best_agent != "unknown":
            _add_event(agent_stats[best_agent], event)

        if event["score"] < 0.5 or event["has_error"]:
            state["low_confidence_patterns"].append(
                {
                    "task": event["task"],
                    "intent": intent,
                    "model_used": model,
                    "score": event["score"],
                    "has_error": event["has_error"],
                    "feedback": event["feedback"],
                }
            )

    state["intents"] = _finalize_group_stats(intent_stats)
    state["models"] = _finalize_group_stats(model_stats)
    state["agents"] = _finalize_group_stats(agent_stats)
    state["model_bias"] = _build_model_bias(state["intents"])
    state["agent_bias"] = _build_agent_bias(state["agents"])
    state["low_confidence_patterns"] = state["low_confidence_patterns"][-20:]

    return state


def score_event(entry: dict) -> dict:
    output = str(entry.get("output", ""))
    agent_result = entry.get("agent_result") or {}
    fusion = agent_result.get("fusion_output") or {}
    route_decision = agent_result.get("route_decision") or {}

    intent = route_decision.get("intent") or fusion.get("final_intent") or "unknown"
    model_used = entry.get("model_used", "unknown")
    best_agent = fusion.get("best_agent", "unknown")
    fusion_confidence = _as_float(fusion.get("confidence"), 0.0)
    route_confidence = _as_float(route_decision.get("confidence"), 0.0)
    has_error = _has_error(output)
    feedback = _feedback_label(entry.get("feedback"))

    score = 0.5
    if route_confidence:
        score += min(route_confidence, 1.0) * 0.2
    if fusion_confidence:
        score += min(fusion_confidence, 1.0) * 0.25
    if best_agent != "unknown":
        score += 0.05
    if has_error:
        score -= 0.5
    score += FEEDBACK_SCORE_ADJUSTMENTS.get(feedback, 0.0)

    return {
        "event_id": entry.get("event_id"),
        "timestamp": entry.get("timestamp"),
        "task": entry.get("task", ""),
        "intent": intent,
        "model_used": model_used,
        "best_agent": best_agent,
        "score": round(max(0.0, min(score, 1.0)), 3),
        "has_error": has_error,
        "route_confidence": route_confidence,
        "fusion_confidence": fusion_confidence,
        "feedback": feedback,
    }


def get_model_bias_for_intent(intent: str, state: Optional[dict] = None) -> dict:
    state = state or load_learning_state()
    return state.get("model_bias", {}).get(intent, {})


def get_agent_weight_multiplier(agent_name: str, state: Optional[dict] = None) -> float:
    state = state or load_learning_state()
    bias = state.get("agent_bias", {}).get(agent_name, {})
    sample_size = int(bias.get("sample_size", 0) or 0)

    if sample_size < 3:
        return 1.0

    return _clamp(_as_float(bias.get("weight_multiplier"), 1.0), 0.75, 1.35)


def _load_logs_from_path(path: str) -> list[dict]:
    if path == MEMORY_FILE:
        return load_memory()

    try:
        with open(path, "r") as file:
            data = json.load(file)
            return data if isinstance(data, list) else []
    except (FileNotFoundError, json.JSONDecodeError):
        return []


def _empty_learning_state() -> dict:
    return {
        "version": 1,
        "updated_at": None,
        "event_count": 0,
        "intents": {},
        "models": {},
        "agents": {},
        "model_bias": {},
        "agent_bias": {},
        "low_confidence_patterns": [],
    }


def _stats_bucket() -> dict:
    return {
        "count": 0,
        "score_total": 0.0,
        "errors": 0,
        "models": defaultdict(int),
        "model_scores": defaultdict(float),
        "agents": defaultdict(int),
    }


def _add_event(bucket: dict, event: dict) -> None:
    bucket["count"] += 1
    bucket["score_total"] += event["score"]
    bucket["errors"] += int(event["has_error"])
    bucket["models"][event["model_used"]] += 1
    bucket["model_scores"][event["model_used"]] += event["score"]
    bucket["agents"][event["best_agent"]] += 1


def _finalize_group_stats(groups: dict) -> dict:
    finalized = {}
    for name, bucket in groups.items():
        count = bucket["count"]
        finalized[name] = {
            "count": count,
            "average_score": round(bucket["score_total"] / count, 3) if count else 0.0,
            "error_rate": round(bucket["errors"] / count, 3) if count else 0.0,
            "models": dict(bucket["models"]),
            "model_scores": _average_model_scores(bucket),
            "agents": dict(bucket["agents"]),
        }

    return finalized


def _build_model_bias(intent_stats: dict) -> dict:
    bias = {}
    for intent, stats in intent_stats.items():
        if intent == "unknown":
            continue

        models = {model: count for model, count in stats.get("models", {}).items() if model != "unknown"}
        model_scores = {
            model: score
            for model, score in stats.get("model_scores", {}).items()
            if model != "unknown" and model in models
        }
        if not models or not model_scores:
            continue

        best_model = max(
            model_scores,
            key=lambda model: (model_scores[model], models.get(model, 0)),
        )
        bias[intent] = {
            "preferred_model": best_model,
            "confidence": model_scores[best_model],
            "sample_size": models[best_model],
        }

    return bias


def _build_agent_bias(agent_stats: dict) -> dict:
    return {
        agent: {
            "average_score": stats["average_score"],
            "sample_size": stats["count"],
            "weight_multiplier": _agent_weight_multiplier(stats),
        }
        for agent, stats in agent_stats.items()
    }


def _agent_weight_multiplier(stats: dict) -> float:
    average_score = _as_float(stats.get("average_score"), 0.5)
    multiplier = 1.0 + ((average_score - 0.5) * 0.6)
    return round(_clamp(multiplier, 0.75, 1.35), 3)


def _has_error(output: str) -> bool:
    lowered = output.lower()
    return any(marker in lowered for marker in ["error:", "traceback", "exception", "failed"])


def _average_model_scores(bucket: dict) -> dict:
    averages = {}
    for model, total_score in bucket["model_scores"].items():
        count = bucket["models"].get(model, 0)
        if count:
            averages[model] = round(total_score / count, 3)

    return averages


def _feedback_label(feedback) -> Optional[str]:
    if isinstance(feedback, str):
        return feedback
    if isinstance(feedback, dict):
        return feedback.get("value") or feedback.get("label")
    return None


def _as_float(value, fallback: float) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return fallback


def _clamp(value: float, minimum: float, maximum: float) -> float:
    return max(minimum, min(value, maximum))
