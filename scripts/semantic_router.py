import math
import os
import re
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class RouteDecision:
    model: str
    intent: str
    confidence: float
    matched_terms: list[str]
    scoring_method: str = "lexical"
    embedding_provider: str = ""
    learning_applied: bool = False
    original_model: str = ""
    recommendation: Optional[dict] = None
    route: str = ""
    execution_target: str = ""

    def to_dict(self) -> dict:
        return {
            "model": self.model,
            "intent": self.intent,
            "confidence": self.confidence,
            "matched_terms": self.matched_terms,
            "scoring_method": self.scoring_method,
            "embedding_provider": self.embedding_provider,
            "learning_applied": self.learning_applied,
            "original_model": self.original_model,
            "recommendation": self.recommendation,
            "route": self.route,
            "execution_target": self.execution_target,
        }


@dataclass(frozen=True)
class IntentProfile:
    intent: str
    model: str
    examples: tuple[str, ...]
    priority: float = 1.0


INTENT_PROFILES = (
    IntentProfile(
        intent="software_engineering",
        model="codex",
        priority=1.2,
        examples=(
            "implement a function",
            "write code",
            "build a FastAPI endpoint",
            "debug a Python script",
            "refactor the repository",
            "create tests",
            "fix an API integration",
            "inspect files and modify code",
        ),
    ),
    IntentProfile(
        intent="system_architecture",
        model="claude",
        priority=1.15,
        examples=(
            "design the architecture",
            "plan an implementation roadmap",
            "reason about a pipeline",
            "create a strategy",
            "evaluate licensing workflow",
            "synthesize complex requirements",
            "design agent fusion",
            "compare tradeoffs",
        ),
    ),
    IntentProfile(
        intent="sync_metadata",
        model="local",
        priority=1.1,
        examples=(
            "analyze music metadata",
            "tag a music track",
            "classify BPM tempo key mood genre",
            "explain sync licensing metadata",
            "describe a song",
            "audio track tagging",
            "quick metadata analysis",
        ),
    ),
    IntentProfile(
        intent="general_explanation",
        model="local",
        examples=(
            "explain a concept",
            "summarize this task",
            "answer a simple question",
            "provide a quick description",
            "general analysis",
            "local fallback",
        ),
    ),
)


import hashlib
import threading

class IsolatedEmbeddingCache:
    """
    Deterministic cache isolation strategy.
    Keyed by (input_hash, model_version).
    Reset per process OR versioned per run.
    MUST NOT persist across logical runs.
    """
    def __init__(self):
        self._cache = {}

    def get(self, key):
        # cache is execution-safe and does not influence learning feedback loops
        return self._cache.get(key)

    def set(self, key, value):
        # cache is execution-safe and does not influence learning feedback loops
        self._cache[key] = value

    def clear(self):
        self._cache.clear()

_EMBEDDING_CACHE = IsolatedEmbeddingCache()


SYNONYMS = {
    "coding": "code",
    "program": "code",
    "programming": "code",
    "endpoint": "api",
    "service": "api",
    "bug": "debug",
    "repair": "fix",
    "roadmap": "plan",
    "blueprint": "architecture",
    "workflow": "pipeline",
    "orchestration": "fusion",
    "orchestrator": "fusion",
    "llm": "model",
    "song": "track",
    "music": "audio",
    "tempo": "bpm",
    "moods": "mood",
    "genres": "genre",
    "tags": "tag",
    "tagging": "tag",
}


def route_task_semantically(task: str, embedding_provider=None) -> RouteDecision:
    # Clear the embedding cache to ensure it MUST NOT persist across logical runs
    _EMBEDDING_CACHE.clear()

    provider = embedding_provider or _configured_embedding_provider()
    decision = None
    if provider:
        decision = _route_with_embeddings(task, provider)

    if not decision:
        decision = _route_with_lexical_similarity(task)

    # Base/static decision with initial fields populated
    static_decision = RouteDecision(
        model=decision.model,
        intent=decision.intent,
        confidence=decision.confidence,
        matched_terms=decision.matched_terms,
        scoring_method=decision.scoring_method,
        embedding_provider=decision.embedding_provider,
        learning_applied=False,
        original_model=decision.model,
        route=decision.intent,
        execution_target=decision.model,
        recommendation=None
    )

    # Construct recommendation object from learning state without modifying decision path
    # and ONLY if we are not inside the runtime execution path.
    from core.invariants import is_in_execution_path
    if is_in_execution_path():
        # During execution path, accessing the learning state is strictly forbidden.
        rec = {
            "recommended_model": static_decision.model,
            "confidence": 0.0,
            "reason": "Learning state access bypassed in execution path."
        }
    else:
        try:
            from memory.learning import get_learning_recommendations
            recs = get_learning_recommendations()
            model_recs = recs.get("model", {})
            bias = model_recs.get(static_decision.intent, {})
            preferred_model = bias.get("recommended_model")
            confidence = float(bias.get("confidence", 0.0) or 0.0)
            reason = bias.get("reason", "")

            if preferred_model:
                rec = {
                    "recommended_model": preferred_model,
                    "confidence": confidence,
                    "reason": reason or f"Recommended model {preferred_model} for intent '{static_decision.intent}'."
                }
            else:
                rec = {
                    "recommended_model": static_decision.model,
                    "confidence": 0.0,
                    "reason": f"No model preference found for intent '{static_decision.intent}'."
                }
        except Exception as exc:
            rec = {
                "recommended_model": static_decision.model,
                "confidence": 0.0,
                "reason": f"Error retrieving recommendation: {exc}"
            }

    final_decision = RouteDecision(
        model=static_decision.model,
        intent=static_decision.intent,
        confidence=static_decision.confidence,
        matched_terms=static_decision.matched_terms,
        scoring_method=static_decision.scoring_method,
        embedding_provider=static_decision.embedding_provider,
        learning_applied=False,
        original_model=static_decision.model,
        recommendation=rec,
        route=static_decision.route,
        execution_target=static_decision.execution_target
    )

    return final_decision


def _route_with_lexical_similarity(task: str) -> RouteDecision:
    task_vector = _vectorize(task)
    if not task_vector:
        return RouteDecision(
            model="local",
            intent="general_explanation",
            confidence=0.0,
            matched_terms=[],
        )

    scored_profiles = []
    for profile in INTENT_PROFILES:
        profile_text = " ".join(profile.examples)
        profile_vector = _vectorize(profile_text)
        score = _cosine_similarity(task_vector, profile_vector) * profile.priority
        scored_profiles.append((score, profile, _matched_terms(task_vector, profile_vector)))

    score, profile, matched_terms = max(scored_profiles, key=lambda item: item[0])

    if score < 0.08:
        return RouteDecision(
            model="local",
            intent="general_explanation",
            confidence=round(score, 3),
            matched_terms=matched_terms,
        )

    return RouteDecision(
        model=profile.model,
        intent=profile.intent,
        confidence=round(min(score, 1.0), 3),
        matched_terms=matched_terms,
    )


def _route_with_embeddings(task: str, provider) -> Optional[RouteDecision]:
    try:
        task_embedding, profile_embeddings = _get_route_embeddings(task, provider)
    except Exception:
        return None

    if not task_embedding or len(profile_embeddings) != len(INTENT_PROFILES):
        return None

    task_vector = _vectorize(task)
    scored_profiles = []
    for index, profile in enumerate(INTENT_PROFILES):
        score = _dense_cosine_similarity(task_embedding, profile_embeddings[index]) * profile.priority
        profile_vector = _vectorize(" ".join(profile.examples))
        scored_profiles.append((score, profile, _matched_terms(task_vector, profile_vector)))

    score, profile, matched_terms = max(scored_profiles, key=lambda item: item[0])
    provider_name = getattr(provider, "__name__", str(provider))

    if score < 0.2:
        return None

    return RouteDecision(
        model=profile.model,
        intent=profile.intent,
        confidence=round(min(score, 1.0), 3),
        matched_terms=matched_terms,
        scoring_method="embedding",
        embedding_provider=provider_name,
    )


def _get_route_embeddings(task: str, provider) -> tuple[list[float], list[list[float]]]:
    profile_texts = [" ".join(profile.examples) for profile in INTENT_PROFILES]

    if callable(provider):
        embeddings = provider([task] + profile_texts)
        return embeddings[0], embeddings[1:]

    provider_name = str(provider)
    
    # Key cache by (input_hash, model_version)
    model_version = os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small")
    profile_texts_str = "".join(profile_texts)
    input_hash = hashlib.sha256(profile_texts_str.encode('utf-8')).hexdigest()
    cache_key = (input_hash, model_version)

    cached_val = _EMBEDDING_CACHE.get(cache_key)
    if not cached_val:
        cached_val = _embed_texts(profile_texts, provider_name)
        _EMBEDDING_CACHE.set(cache_key, cached_val)

    task_embedding = _embed_texts([task], provider_name)[0]
    return task_embedding, cached_val


def _configured_embedding_provider():
    provider = os.getenv("SEMANTIC_ROUTER_EMBEDDINGS", "").strip().lower()
    if provider in {"", "0", "false", "off", "none"}:
        return None

    if provider == "openai":
        return provider

    return None


# Removed learning bias direct mutation code path


def _embed_texts(texts: list[str], provider: str) -> list[list[float]]:
    if provider == "openai":
        return _embed_with_openai(texts)

    raise ValueError(f"Unsupported embedding provider: {provider}")


def _embed_with_openai(texts: list[str]) -> list[list[float]]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY is not configured")

    from openai import OpenAI

    client = OpenAI(api_key=api_key)
    response = client.embeddings.create(
        model=os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
        input=texts,
    )
    return [item.embedding for item in response.data]


def _vectorize(text: str) -> dict[str, float]:
    tokens = [_normalize_token(token) for token in re.findall(r"[a-zA-Z0-9_]+", text.lower())]
    tokens = [token for token in tokens if len(token) > 1 and token not in _STOPWORDS]

    vector = {}
    for token in tokens:
        vector[token] = vector.get(token, 0.0) + 1.0

    for left, right in zip(tokens, tokens[1:]):
        phrase = f"{left}_{right}"
        vector[phrase] = vector.get(phrase, 0.0) + 1.5

    return vector


def _normalize_token(token: str) -> str:
    token = SYNONYMS.get(token, token)

    if token.endswith("ies") and len(token) > 4:
        token = f"{token[:-3]}y"
    elif token.endswith("ing") and len(token) > 5:
        token = token[:-3]
    elif token.endswith("ed") and len(token) > 4:
        token = token[:-2]
    elif token.endswith("s") and len(token) > 3:
        token = token[:-1]

    return SYNONYMS.get(token, token)


def _cosine_similarity(left: dict[str, float], right: dict[str, float]) -> float:
    overlap = set(left) & set(right)
    dot = sum(left[key] * right[key] for key in overlap)
    left_norm = math.sqrt(sum(value * value for value in left.values()))
    right_norm = math.sqrt(sum(value * value for value in right.values()))

    if not left_norm or not right_norm:
        return 0.0

    return dot / (left_norm * right_norm)


def _dense_cosine_similarity(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0

    dot = sum(left_value * right_value for left_value, right_value in zip(left, right))
    left_norm = math.sqrt(sum(value * value for value in left))
    right_norm = math.sqrt(sum(value * value for value in right))

    if not left_norm or not right_norm:
        return 0.0

    return dot / (left_norm * right_norm)


def _matched_terms(left: dict[str, float], right: dict[str, float]) -> list[str]:
    matches = sorted(set(left) & set(right), key=lambda term: (-left[term], term))
    return matches[:8]


_STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "for",
    "from",
    "how",
    "i",
    "in",
    "into",
    "is",
    "it",
    "of",
    "on",
    "or",
    "our",
    "the",
    "this",
    "to",
    "with",
    "you",
}
