import re
from typing import Any, Dict, Iterable, List, Optional, Tuple

from syncmaster.schema import MetadataAnalysis, TrackMetadata


MOOD_TERMS = {
    "uplifting": ("uplifting", "euphoric", "hopeful", "bright", "anthemic"),
    "dark": ("dark", "ominous", "brooding", "moody", "tense", "gritty"),
    "happy": ("happy", "joyful", "playful", "fun", "feel good", "feel-good"),
    "sad": ("sad", "melancholy", "melancholic", "somber", "heartbreak", "lonely"),
    "romantic": ("romantic", "love", "sensual", "intimate"),
    "calm": ("calm", "peaceful", "ambient", "dreamy", "soft", "gentle"),
    "aggressive": ("aggressive", "angry", "intense", "heavy", "hard-hitting"),
    "confident": ("confident", "bold", "triumphant", "swagger"),
}

GENRE_TERMS = {
    "pop": ("pop", "dance pop", "synthpop", "electropop"),
    "hip-hop": ("hip hop", "hip-hop", "rap", "trap", "boom bap"),
    "r&b": ("r&b", "rnb", "soul", "neo soul", "neo-soul"),
    "rock": ("rock", "indie rock", "alternative", "punk", "guitar-driven"),
    "electronic": ("electronic", "edm", "house", "techno", "synth", "club"),
    "cinematic": ("cinematic", "score", "trailer", "orchestral", "soundtrack"),
    "folk": ("folk", "acoustic", "singer songwriter", "singer-songwriter"),
    "jazz": ("jazz", "swing", "bebop", "standards"),
    "latin": ("latin", "reggaeton", "salsa", "bachata"),
    "country": ("country", "americana", "bluegrass"),
}

ENERGY_TERMS = {
    "low": ("low energy", "slow", "quiet", "minimal", "laid back", "laid-back", "chill"),
    "medium": ("medium energy", "mid energy", "midtempo", "steady", "groove"),
    "high": ("high energy", "energetic", "driving", "explosive", "upbeat", "club", "intense"),
}

VOCAL_TERMS = {
    "instrumental": ("instrumental", "no vocals", "no vocal", "underscore", "bed"),
    "vocal": ("vocal", "vocals", "sung", "singer", "lyrics", "rap verse", "choir"),
}

KEY_PATTERN = re.compile(r"\b([a-g])\s*(#|sharp|b|flat)?\s*(major|minor|maj|min|m)?\b", re.IGNORECASE)
BPM_PATTERN = re.compile(r"\b(?:bpm|tempo)?\s*([1-2]?\d{2}|[1-9]\d)\s*(?:bpm|beats per minute)?\b", re.IGNORECASE)


def analyze_metadata(payload=None, tags=None, text: str = "") -> MetadataAnalysis:
    data = payload if isinstance(payload, dict) else {}
    tag_values = _collect_tags(data, tags)
    source_text = _combined_text(data, tag_values, text)
    normalized_text = _normalize(source_text)

    title = str(data.get("title", "") or data.get("name", "") or "").strip()
    artist = str(data.get("artist", "") or data.get("composer", "") or "").strip()

    bpm, bpm_terms = _detect_bpm(data, normalized_text)
    key, key_terms = _detect_key(data, normalized_text)
    mood, mood_terms = _detect_terms(data, "mood", MOOD_TERMS, normalized_text)
    genre, genre_terms = _detect_terms(data, "genre", GENRE_TERMS, normalized_text)
    energy, energy_terms = _detect_energy(data, normalized_text, bpm)
    vocals, vocal_terms = _detect_vocals(data, normalized_text)

    matched_terms = {
        "bpm": bpm_terms,
        "key": key_terms,
        "mood": mood_terms,
        "genre": genre_terms,
        "energy": energy_terms,
        "vocals": vocal_terms,
    }
    warnings = []
    if bpm is not None and not 1 <= bpm <= 300:
        warnings.append("bpm_out_of_supported_range")
        bpm = None

    metadata = TrackMetadata(
        title=title,
        artist=artist,
        bpm=bpm,
        key=key,
        mood=mood,
        genre=genre,
        energy=energy,
        vocals=vocals,
        tags=_unique_preserving_order(tag_values),
        source_text=source_text.strip(),
    )

    return MetadataAnalysis(
        metadata=metadata,
        confidence=_confidence(metadata, matched_terms),
        matched_terms=matched_terms,
        warnings=warnings,
    )


def tag_metadata(payload=None, tags=None, text: str = "") -> Dict[str, Any]:
    return analyze_metadata(payload=payload, tags=tags, text=text).to_dict()


def _collect_tags(data: Dict[str, Any], tags) -> List[str]:
    values = []
    for key in ("tags", "keywords"):
        values.extend(_as_list(data.get(key)))
    values.extend(_as_list(tags))
    return [str(value).strip() for value in values if str(value).strip()]


def _combined_text(data: Dict[str, Any], tags: List[str], text: str) -> str:
    pieces = [text]
    for key in ("description", "summary", "notes", "lyrics", "title", "name", "artist", "composer"):
        value = data.get(key)
        if isinstance(value, str):
            pieces.append(value)
    pieces.extend(tags)
    return " ".join(piece for piece in pieces if piece)


def _detect_bpm(data: Dict[str, Any], normalized_text: str) -> Tuple[Optional[int], List[str]]:
    for key in ("bpm", "tempo"):
        value = data.get(key)
        if value in (None, ""):
            continue
        try:
            bpm = int(float(value))
            return bpm, [str(value)]
        except (TypeError, ValueError):
            pass

    for match in BPM_PATTERN.finditer(normalized_text):
        bpm = int(match.group(1))
        if 1 <= bpm <= 300:
            return bpm, [match.group(0).strip()]
    return None, []


def _detect_key(data: Dict[str, Any], normalized_text: str) -> Tuple[str, List[str]]:
    explicit = data.get("key") or data.get("musical_key")
    if explicit:
        return _format_key(str(explicit)), [str(explicit)]

    for match in KEY_PATTERN.finditer(normalized_text):
        prefix = normalized_text[max(0, match.start() - 8):match.start()]
        if not (match.group(2) or match.group(3) or "key" in prefix):
            continue
        formatted = _format_key(" ".join(part for part in match.groups() if part))
        if formatted:
            return formatted, [match.group(0).strip()]
    return "", []


def _detect_terms(data: Dict[str, Any], field: str, term_map: Dict[str, Iterable[str]], normalized_text: str):
    explicit_values = _as_list(data.get(field))
    if explicit_values:
        labels = [_canonical_label(value, term_map) for value in explicit_values]
        labels = [label for label in labels if label]
        return _unique_preserving_order(labels), [str(value) for value in explicit_values]

    labels = []
    matches = []
    for label, terms in term_map.items():
        found_terms = [term for term in terms if _contains_term(normalized_text, term)]
        if found_terms:
            labels.append(label)
            matches.extend(found_terms)
    return labels, _unique_preserving_order(matches)


def _detect_energy(data: Dict[str, Any], normalized_text: str, bpm: Optional[int]) -> Tuple[str, List[str]]:
    explicit = str(data.get("energy", "") or "").strip().lower()
    if explicit in {"low", "medium", "high"}:
        return explicit, [explicit]

    labels, matches = _detect_terms(data, "energy", ENERGY_TERMS, normalized_text)
    if labels:
        return labels[-1], matches

    if bpm is None:
        return "unknown", []
    if bpm < 90:
        return "low", [str(bpm)]
    if bpm < 125:
        return "medium", [str(bpm)]
    return "high", [str(bpm)]


def _detect_vocals(data: Dict[str, Any], normalized_text: str) -> Tuple[str, List[str]]:
    for key in ("vocals", "vocal_type"):
        explicit = str(data.get(key, "") or "").strip().lower()
        if explicit in {"vocal", "vocals", "instrumental"}:
            return ("vocal" if explicit in {"vocal", "vocals"} else "instrumental"), [explicit]

    labels, matches = _detect_terms(data, "vocals", VOCAL_TERMS, normalized_text)
    if "instrumental" in labels:
        return "instrumental", matches
    if "vocal" in labels:
        return "vocal", matches
    return "unknown", []


def _confidence(metadata: TrackMetadata, matched_terms: Dict[str, List[str]]) -> Dict[str, float]:
    return {
        "bpm": 1.0 if metadata.bpm is not None else 0.0,
        "key": 1.0 if metadata.key else 0.0,
        "mood": 0.9 if metadata.mood else 0.0,
        "genre": 0.9 if metadata.genre else 0.0,
        "energy": 0.85 if matched_terms.get("energy") else 0.0,
        "vocals": 0.9 if matched_terms.get("vocals") else 0.0,
    }


def _canonical_label(value, term_map: Dict[str, Iterable[str]]) -> str:
    normalized = _normalize(str(value))
    for label, terms in term_map.items():
        if normalized == label or any(normalized == _normalize(term) for term in terms):
            return label
    return normalized


def _format_key(value: str) -> str:
    normalized = _normalize(value)
    match = KEY_PATTERN.search(normalized)
    if not match:
        return value.strip()

    root = match.group(1).upper()
    accidental = match.group(2) or ""
    mode = match.group(3) or ""
    accidental = "#" if accidental in {"#", "sharp"} else ("b" if accidental in {"b", "flat"} else "")
    mode = "minor" if mode in {"minor", "min", "m"} else ("major" if mode in {"major", "maj"} else "")
    return " ".join(part for part in (root + accidental, mode) if part)


def _contains_term(text: str, term: str) -> bool:
    normalized = _normalize(term)
    return re.search(r"(?<!\w)" + re.escape(normalized) + r"(?!\w)", text) is not None


def _normalize(value: str) -> str:
    return re.sub(r"\s+", " ", str(value).lower().replace("_", " ")).strip()


def _as_list(value) -> List[Any]:
    if value in (None, ""):
        return []
    if isinstance(value, set):
        return sorted(value, key=str)
    if isinstance(value, (list, tuple)):
        return list(value)
    return [value]


def _unique_preserving_order(values: Iterable[str]) -> List[str]:
    seen = set()
    unique = []
    for value in values:
        key = str(value).strip().lower()
        if key and key not in seen:
            seen.add(key)
            unique.append(str(value).strip())
    return unique
