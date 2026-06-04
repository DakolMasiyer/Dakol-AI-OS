"""Deterministic sync licensing recommendations for track metadata and briefs."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
from typing import Any

try:  # Optional phase-local schema support; keep this module usable without it.
    from syncmaster import schema as _schema  # type: ignore
except Exception:  # pragma: no cover - defensive import guard
    _schema = None


Recommendation = dict[str, Any]


def recommend_sync_fit(track_metadata: Any, brief: Any) -> Recommendation:
    """Return a JSON-serializable sync licensing recommendation.

    Inputs may be dictionaries, dataclasses, or simple objects. The function is
    deterministic and uses only local metadata/brief heuristics.
    """

    track = _to_mapping(track_metadata)
    brief_data = _to_mapping(brief)

    score = 50
    reasoning: list[str] = []

    score += _match_score(
        _list_value(track, "moods", "mood", "tags"),
        _list_value(brief_data, "moods", "target_moods", "mood", "tone"),
        18,
        "Mood",
        reasoning,
    )
    score += _match_score(
        _list_value(track, "genres", "genre"),
        _list_value(brief_data, "genres", "genre"),
        14,
        "Genre",
        reasoning,
    )
    score += _tempo_score(track, brief_data, reasoning)
    score += _duration_score(track, brief_data, reasoning)
    score += _vocal_score(track, brief_data, reasoning)

    clearance_notes, clearance_adjustment = _clearance_notes(track, brief_data)
    score += clearance_adjustment

    risks, risk_adjustment = _risks(track, brief_data)
    score += risk_adjustment

    score = max(0, min(100, score))

    return {
        "fit_score": score,
        "usage_suggestions": _usage_suggestions(track, brief_data, score),
        "clearance_notes": clearance_notes,
        "risks": risks,
        "reasoning": reasoning or ["Insufficient metadata for detailed creative matching."],
    }


def recommend_licensing(track_metadata: Any, brief: Any) -> Recommendation:
    """Compatibility wrapper for the broader SyncMaster package API."""

    recommendation = recommend_sync_fit(track_metadata, brief)
    return {
        **recommendation,
        "fit_label": _fit_label(recommendation["fit_score"]),
    }


def _to_mapping(value: Any) -> dict[str, Any]:
    if value is None:
        return {}
    if isinstance(value, dict):
        return dict(value)
    if is_dataclass(value):
        return asdict(value)

    dump = getattr(value, "model_dump", None)
    if callable(dump):
        return dict(dump())

    if hasattr(value, "to_dict") and callable(value.to_dict):
        return dict(value.to_dict())
    if hasattr(value, "__dict__"):
        return {
            key: item
            for key, item in vars(value).items()
            if not key.startswith("_")
        }
    return {}


def _list_value(data: dict[str, Any], *keys: str) -> list[str]:
    values: list[str] = []
    for key in keys:
        raw = data.get(key)
        if raw is None:
            continue
        if isinstance(raw, str):
            values.extend(part.strip().lower() for part in raw.split(","))
        elif isinstance(raw, (list, tuple, set)):
            values.extend(str(part).strip().lower() for part in raw)
        else:
            values.append(str(raw).strip().lower())
    return sorted({value for value in values if value})


def _number_value(data: dict[str, Any], *keys: str) -> float | None:
    for key in keys:
        raw = data.get(key)
        if raw in (None, ""):
            continue
        try:
            return float(raw)
        except (TypeError, ValueError):
            continue
    return None


def _bool_value(data: dict[str, Any], *keys: str) -> bool:
    for key in keys:
        raw = data.get(key)
        if isinstance(raw, bool):
            return raw
        if isinstance(raw, str):
            lowered = raw.strip().lower()
            if lowered in {"yes", "true", "1", "one-stop", "cleared"}:
                return True
            if lowered in {"no", "false", "0", "uncleared"}:
                return False
        if raw is not None:
            return bool(raw)
    return False


def _match_score(
    track_terms: list[str],
    brief_terms: list[str],
    weight: int,
    label: str,
    reasoning: list[str],
) -> int:
    if not track_terms or not brief_terms:
        return 0

    overlap = sorted(set(track_terms) & set(brief_terms))
    if overlap:
        points = round(weight * len(overlap) / max(len(set(brief_terms)), 1))
        reasoning.append(f"{label} overlap: {', '.join(overlap)}.")
        return points

    reasoning.append(f"No direct {label.lower()} overlap found.")
    return -round(weight * 0.4)


def _tempo_score(track: dict[str, Any], brief: dict[str, Any], reasoning: list[str]) -> int:
    bpm = _number_value(track, "bpm", "tempo")
    target = _number_value(brief, "bpm", "tempo", "target_bpm")
    minimum = _number_value(brief, "min_bpm", "tempo_min")
    maximum = _number_value(brief, "max_bpm", "tempo_max")

    if bpm is None:
        return 0
    if minimum is not None and maximum is not None:
        if minimum <= bpm <= maximum:
            reasoning.append(f"Tempo {int(bpm)} BPM is within the requested range.")
            return 10
        reasoning.append(f"Tempo {int(bpm)} BPM is outside the requested range.")
        return -8
    if target is not None:
        distance = abs(bpm - target)
        if distance <= 6:
            reasoning.append(f"Tempo is close to the target at {int(bpm)} BPM.")
            return 8
        if distance <= 14:
            reasoning.append(f"Tempo is workable but not exact at {int(bpm)} BPM.")
            return 3
        reasoning.append(f"Tempo differs materially at {int(bpm)} BPM.")
        return -5
    return 0


def _duration_score(track: dict[str, Any], brief: dict[str, Any], reasoning: list[str]) -> int:
    duration = _number_value(track, "duration_seconds", "duration", "length_seconds")
    target = _number_value(brief, "duration_seconds", "duration", "target_duration")
    if duration is None or target is None:
        return 0

    delta = abs(duration - target)
    if delta <= 10:
        reasoning.append("Duration is ready for the requested placement length.")
        return 6
    if duration > target:
        reasoning.append("Track can likely be edited down to the requested length.")
        return 2
    reasoning.append("Track may be short for the requested placement length.")
    return -3


def _vocal_score(track: dict[str, Any], brief: dict[str, Any], reasoning: list[str]) -> int:
    preference = str(brief.get("vocal_preference", brief.get("vocals", ""))).lower()
    if not preference:
        return 0

    instrumental = _bool_value(track, "instrumental")
    vocal_type = str(track.get("vocal_type", track.get("vocals", ""))).lower()
    has_vocals = not instrumental and vocal_type not in {"", "none", "instrumental"}

    if "instrumental" in preference:
        if instrumental or not has_vocals:
            reasoning.append("Vocal profile matches an instrumental brief.")
            return 7
        reasoning.append("Vocals may compete with dialogue for an instrumental brief.")
        return -8
    if "vocal" in preference and has_vocals:
        reasoning.append("Vocal profile matches the brief.")
        return 5
    return 0


def _clearance_notes(track: dict[str, Any], brief: dict[str, Any]) -> tuple[list[str], int]:
    notes: list[str] = []
    adjustment = 0

    if _bool_value(track, "one_stop", "one_stop_clearance"):
        notes.append("One-stop clearance indicated; verify master and publishing authority.")
        adjustment += 8
    else:
        notes.append("Confirm master and publishing owners before quoting.")
        adjustment -= 3

    if _bool_value(track, "pre_cleared", "sync_pre_cleared"):
        notes.append("Track is marked pre-cleared for sync review.")
        adjustment += 4

    owners = [
        str(track.get(key)).strip()
        for key in ("master_owner", "publishing_owner", "publisher")
        if track.get(key)
    ]
    if owners:
        notes.append("Rights contacts available: " + ", ".join(owners) + ".")
        adjustment += 2

    territory = brief.get("territory") or brief.get("territories")
    if territory:
        notes.append(f"Check availability for requested territory: {territory}.")

    if brief.get("exclusivity"):
        notes.append("Exclusivity request needs separate fee and hold-period approval.")
        adjustment -= 4

    return notes, adjustment


def _risks(track: dict[str, Any], brief: dict[str, Any]) -> tuple[list[dict[str, str]], int]:
    risks: list[dict[str, str]] = []
    adjustment = 0

    if _bool_value(track, "samples", "contains_samples", "sampled"):
        risks.append({"level": "high", "note": "Track indicates samples that require source clearance."})
        adjustment -= 18

    if _bool_value(track, "explicit", "explicit_lyrics"):
        risks.append({"level": "medium", "note": "Explicit content may require clean edits or client approval."})
        adjustment -= 8

    restrictions = track.get("territory_restrictions") or track.get("restrictions")
    if restrictions:
        risks.append({"level": "medium", "note": f"Known restrictions: {restrictions}."})
        adjustment -= 8

    deadline = str(brief.get("deadline", "")).lower()
    if deadline in {"urgent", "asap", "rush"} and not _bool_value(track, "one_stop", "pre_cleared"):
        risks.append({"level": "medium", "note": "Rush brief with incomplete clearance data."})
        adjustment -= 6

    if not risks:
        risks.append({"level": "low", "note": "No major metadata-based licensing risks detected."})

    return risks, adjustment


def _usage_suggestions(track: dict[str, Any], brief: dict[str, Any], score: int) -> list[str]:
    media_type = str(brief.get("media_type", brief.get("usage", "placement"))).strip() or "placement"
    suggestions: list[str] = []

    if score >= 75:
        suggestions.append(f"Prioritize for {media_type}; creative and clearance signals are strong.")
    elif score >= 55:
        suggestions.append(f"Keep as a secondary option for {media_type} with targeted edits or checks.")
    else:
        suggestions.append(f"Use cautiously for {media_type}; request alternates before pitching.")

    if _bool_value(track, "instrumental"):
        suggestions.append("Pitch under dialogue, product demos, or montage sections.")
    elif _bool_value(track, "explicit", "explicit_lyrics"):
        suggestions.append("Prepare a clean edit before client review.")
    else:
        suggestions.append("Review hook and edit points for a 15, 30, or 60 second cutdown.")

    return suggestions


def _fit_label(score: int) -> str:
    if score >= 80:
        return "strong"
    if score >= 60:
        return "moderate"
    if score >= 40:
        return "limited"
    return "poor"
