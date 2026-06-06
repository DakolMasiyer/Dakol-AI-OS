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


_PROFILE_EMBEDDING_CACHE = {}


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
    provider = embedding_provider or _configured_embedding_provider()
    if provider:
        decision = _route_with_embeddings(task, provider)
        if decision:
            return _apply_learning_bias(decision)

    return _apply_learning_bias(_route_with_lexical_similarity(task))


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
    cache_key = (
        provider_name,
        os.getenv("OPENAI_EMBEDDING_MODEL", "text-embedding-3-small"),
    )

    if cache_key not in _PROFILE_EMBEDDING_CACHE:
        _PROFILE_EMBEDDING_CACHE[cache_key] = _embed_texts(profile_texts, provider_name)

    task_embedding = _embed_texts([task], provider_name)[0]
    return task_embedding, _PROFILE_EMBEDDING_CACHE[cache_key]


def _configured_embedding_provider():
    provider = os.getenv("SEMANTIC_ROUTER_EMBEDDINGS", "").strip().lower()
    if provider in {"", "0", "false", "off", "none"}:
        return None

    if provider == "openai":
        return provider

    return None


def _apply_learning_bias(decision: RouteDecision) -> RouteDecision:
    try:
        from memory.learning import get_model_bias_for_intent

        bias = get_model_bias_for_intent(decision.intent)
    except Exception:
        return decision

    preferred_model = bias.get("preferred_model")
    sample_size = int(bias.get("sample_size", 0) or 0)
    confidence = float(bias.get("confidence", 0.0) or 0.0)

    if not preferred_model or preferred_model == decision.model:
        return decision

    if sample_size < 3 or confidence < 0.75:
        return decision

    return RouteDecision(
        model=preferred_model,
        intent=decision.intent,
        confidence=decision.confidence,
        matched_terms=decision.matched_terms,
        scoring_method=decision.scoring_method,
        embedding_provider=decision.embedding_provider,
        learning_applied=True,
        original_model=decision.model,
    )


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
