"""Deterministic composer and track matching for SyncMaster briefs."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import re
from typing import Any, Iterable

try:  # pragma: no cover - optional integration point for future schema work.
    from syncmaster import schema as _schema  # noqa: F401
except Exception:  # pragma: no cover
    _schema = None


FIELD_WEIGHTS = {
    "mood": 25.0,
    "genre": 20.0,
    "tempo": 20.0,
    "instrument": 15.0,
    "vocal": 10.0,
    "keywords": 10.0,
}

TOKEN_RE = re.compile(r"[a-z0-9]+")
TEMPO_RE = re.compile(r"\d+(?:\.\d+)?")


def match_to_brief(
    brief: Any,
    candidates: Iterable[Any],
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Return JSON-serializable candidate matches ranked against a brief.

    Inputs can be dictionaries, dataclasses, or objects with attributes. The
    returned list is sorted by score descending, then by stable candidate label.
    """

    matches = [_score_candidate(brief, candidate) for candidate in candidates]
    matches.sort(
        key=lambda match: (
            -match["score"],
            str(match["candidate"].get("id") or ""),
            str(match["candidate"].get("title") or match["candidate"].get("name") or ""),
        )
    )

    ranked = []
    for index, match in enumerate(matches[:limit] if limit is not None else matches, start=1):
        ranked.append({"rank": index, **match})
    return ranked


def rank_matches(
    brief: Any,
    tracks_or_composers: Iterable[Any],
    limit: int | None = None,
) -> list[dict[str, Any]]:
    """Alias for callers that prefer result-oriented naming."""

    return match_to_brief(brief, tracks_or_composers, limit=limit)


def _score_candidate(brief: Any, candidate: Any) -> dict[str, Any]:
    reasons: list[str] = []
    score = 0.0

    score += _score_token_field(
        brief,
        candidate,
        field="mood",
        brief_keys=("mood", "moods"),
        candidate_keys=("mood", "moods"),
        reasons=reasons,
    )
    score += _score_token_field(
        brief,
        candidate,
        field="genre",
        brief_keys=("genre", "genres"),
        candidate_keys=("genre", "genres", "style", "styles"),
        reasons=reasons,
    )
    score += _score_tempo(brief, candidate, reasons)
    score += _score_token_field(
        brief,
        candidate,
        field="instrument",
        brief_keys=("instrument", "instruments", "instrumentation"),
        candidate_keys=("instrument", "instruments", "instrumentation"),
        reasons=reasons,
    )
    score += _score_vocal(brief, candidate, reasons)
    score += _score_token_field(
        brief,
        candidate,
        field="keywords",
        brief_keys=("keyword", "keywords", "tags"),
        candidate_keys=("keyword", "keywords", "tags", "themes"),
        reasons=reasons,
    )

    if not reasons:
        reasons.append("no brief criteria matched")

    return {
        "candidate": _candidate_summary(candidate),
        "score": round(min(score, 100.0), 2),
        "reasons": reasons,
    }


def _score_token_field(
    brief: Any,
    candidate: Any,
    field: str,
    brief_keys: tuple[str, ...],
    candidate_keys: tuple[str, ...],
    reasons: list[str],
) -> float:
    expected = _tokens_from_keys(brief, brief_keys)
    if not expected:
        return 0.0

    actual = _tokens_from_keys(candidate, candidate_keys)
    if not actual:
        reasons.append(f"missing {field}")
        return 0.0

    matched = expected & actual
    if not matched:
        reasons.append(f"{field} mismatch")
        return 0.0

    ratio = len(matched) / len(expected)
    matched_text = ", ".join(sorted(matched))
    reasons.append(f"matched {field}: {matched_text}")
    return FIELD_WEIGHTS[field] * ratio


def _score_tempo(brief: Any, candidate: Any, reasons: list[str]) -> float:
    target = _tempo_range(brief, ("tempo", "bpm", "tempo_bpm", "target_tempo"))
    if target is None:
        return 0.0

    tempo = _tempo_value(candidate, ("tempo", "bpm", "tempo_bpm"))
    if tempo is None:
        reasons.append("missing tempo")
        return 0.0

    low, high = target
    if low <= tempo <= high:
        if low == high:
            reasons.append(f"matched tempo: {round(tempo, 1):g} bpm")
        else:
            reasons.append(f"matched tempo: {round(tempo, 1):g} bpm in {round(low, 1):g}-{round(high, 1):g}")
        return FIELD_WEIGHTS["tempo"]

    distance = low - tempo if tempo < low else tempo - high
    partial = max(0.0, 1.0 - (distance / 40.0))
    if partial > 0:
        reasons.append(f"near tempo: {round(tempo, 1):g} bpm")
    else:
        reasons.append("tempo mismatch")
    return FIELD_WEIGHTS["tempo"] * partial


def _score_vocal(brief: Any, candidate: Any, reasons: list[str]) -> float:
    expected = _vocal_value(_first_present(brief, ("vocal", "vocals", "vocal_type", "voice")))
    if expected is None:
        return 0.0

    actual = _vocal_value(_first_present(candidate, ("vocal", "vocals", "vocal_type", "voice")))
    if actual is None:
        reasons.append("missing vocal")
        return 0.0

    if expected == actual:
        reasons.append(f"matched vocal: {expected}")
        return FIELD_WEIGHTS["vocal"]

    reasons.append("vocal mismatch")
    return 0.0


def _candidate_summary(candidate: Any) -> dict[str, Any]:
    keys = ("id", "title", "name", "composer", "artist", "type")
    compact = {}
    for key in keys:
        value = _get_value(candidate, key)
        if value is not None:
            compact[key] = _json_safe(value)

    if compact:
        return compact

    label = getattr(candidate, "__class__", type(candidate)).__name__
    return {"name": label}


def _tokens_from_keys(item: Any, keys: tuple[str, ...]) -> set[str]:
    tokens: set[str] = set()
    for key in keys:
        value = _get_value(item, key)
        if value is not None:
            tokens.update(_tokens(value))
    return tokens


def _tokens(value: Any) -> set[str]:
    if value is None:
        return set()
    if isinstance(value, str):
        return set(TOKEN_RE.findall(value.lower()))
    if isinstance(value, dict):
        values = value.values()
    elif isinstance(value, (list, tuple, set, frozenset)):
        values = value
    else:
        values = (value,)

    found: set[str] = set()
    for item in values:
        found.update(_tokens(item))
    return found


def _tempo_range(item: Any, keys: tuple[str, ...]) -> tuple[float, float] | None:
    low = _tempo_value(item, ("tempo_min", "min_tempo", "min_bpm", "bpm_min"))
    high = _tempo_value(item, ("tempo_max", "max_tempo", "max_bpm", "bpm_max"))
    if low is not None and high is not None:
        return (min(low, high), max(low, high))

    value = _first_present(item, keys)
    if isinstance(value, (list, tuple)) and len(value) >= 2:
        parsed = [_number(part) for part in value[:2]]
        if parsed[0] is not None and parsed[1] is not None:
            return (min(parsed), max(parsed))

    if isinstance(value, str):
        numbers = [float(number) for number in TEMPO_RE.findall(value)]
        if len(numbers) >= 2:
            return (min(numbers[0], numbers[1]), max(numbers[0], numbers[1]))
        if len(numbers) == 1:
            tempo = numbers[0]
            return (tempo, tempo)

    tempo = _number(value)
    if tempo is None:
        return None
    return (tempo, tempo)


def _tempo_value(item: Any, keys: tuple[str, ...]) -> float | None:
    value = _first_present(item, keys)
    if isinstance(value, (list, tuple)) and value:
        value = value[0]
    if isinstance(value, str):
        match = TEMPO_RE.search(value)
        if match:
            return float(match.group(0))
    return _number(value)


def _vocal_value(value: Any) -> str | None:
    tokens = _tokens(value)
    if not tokens:
        return None
    if {"instrumental", "no", "none"} & tokens:
        return "instrumental"
    if {"vocal", "vocals", "voice", "sung", "singer", "male", "female"} & tokens:
        return "vocal"
    return " ".join(sorted(tokens))


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _first_present(item: Any, keys: tuple[str, ...]) -> Any:
    for key in keys:
        value = _get_value(item, key)
        if value is not None:
            return value
    return None


def _get_value(item: Any, key: str) -> Any:
    mapping = _as_mapping(item)
    if key in mapping:
        return mapping[key]
    return getattr(item, key, None)


def _as_mapping(item: Any) -> dict[str, Any]:
    if item is None:
        return {}
    if is_dataclass(item):
        return asdict(item)
    if isinstance(item, dict):
        return item
    if hasattr(item, "dict") and callable(item.dict):
        try:
            value = item.dict()
            if isinstance(value, dict):
                return value
        except Exception:
            pass
    if hasattr(item, "model_dump") and callable(item.model_dump):
        try:
            value = item.model_dump()
            if isinstance(value, dict):
                return value
        except Exception:
            pass
    return {}


def _json_safe(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    return str(value)
