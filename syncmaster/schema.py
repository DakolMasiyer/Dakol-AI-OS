from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional


@dataclass(frozen=True)
class TrackMetadata:
    title: str = ""
    artist: str = ""
    bpm: Optional[int] = None
    key: str = ""
    mood: List[str] = field(default_factory=list)
    genre: List[str] = field(default_factory=list)
    energy: str = "unknown"
    vocals: str = "unknown"
    tags: List[str] = field(default_factory=list)
    source_text: str = ""

    @classmethod
    def from_dict(cls, data):
        return cls(
            title=str(data.get("title", "") or "").strip(),
            artist=str(data.get("artist", "") or "").strip(),
            bpm=_coerce_optional_int(data.get("bpm")),
            key=str(data.get("key", "") or "").strip(),
            mood=_coerce_string_list(data.get("mood", [])),
            genre=_coerce_string_list(data.get("genre", [])),
            energy=str(data.get("energy", "unknown") or "unknown").strip().lower(),
            vocals=str(data.get("vocals", "unknown") or "unknown").strip().lower(),
            tags=_coerce_string_list(data.get("tags", [])),
            source_text=str(data.get("source_text", "") or "").strip(),
        )

    def to_dict(self):
        return {
            "title": self.title,
            "artist": self.artist,
            "bpm": self.bpm,
            "key": self.key,
            "mood": list(self.mood),
            "genre": list(self.genre),
            "energy": self.energy,
            "vocals": self.vocals,
            "tags": list(self.tags),
            "source_text": self.source_text,
        }

    @property
    def vocal(self):
        return self.vocals


@dataclass(frozen=True)
class MetadataAnalysis:
    metadata: TrackMetadata
    confidence: Dict[str, float] = field(default_factory=dict)
    matched_terms: Dict[str, List[str]] = field(default_factory=dict)
    warnings: List[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data):
        return cls(
            metadata=TrackMetadata.from_dict(data.get("metadata", {})),
            confidence={str(key): float(value) for key, value in data.get("confidence", {}).items()},
            matched_terms={
                str(key): _coerce_string_list(value)
                for key, value in data.get("matched_terms", {}).items()
            },
            warnings=_coerce_string_list(data.get("warnings", [])),
        )

    def to_dict(self):
        return {
            "metadata": self.metadata.to_dict(),
            "confidence": dict(self.confidence),
            "matched_terms": {
                key: list(value)
                for key, value in self.matched_terms.items()
            },
            "warnings": list(self.warnings),
        }


@dataclass(frozen=True)
class Brief:
    title: str = ""
    description: str = ""
    mood: List[str] = field(default_factory=list)
    genre: List[str] = field(default_factory=list)
    tempo: str = ""
    usage: str = ""
    keywords: List[str] = field(default_factory=list)
    budget: str = ""

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        return cls(
            title=str(data.get("title", "") or "").strip(),
            description=str(data.get("description", "") or "").strip(),
            mood=_coerce_string_list(data.get("mood", data.get("moods", []))),
            genre=_coerce_string_list(data.get("genre", data.get("genres", []))),
            tempo=str(data.get("tempo", data.get("bpm", "")) or "").strip(),
            usage=str(data.get("usage", data.get("media_type", "")) or "").strip(),
            keywords=_coerce_string_list(data.get("keywords", data.get("tags", []))),
            budget=str(data.get("budget", "") or "").strip(),
        )

    def to_dict(self):
        return {
            "title": self.title,
            "description": self.description,
            "mood": list(self.mood),
            "genre": list(self.genre),
            "tempo": self.tempo,
            "usage": self.usage,
            "keywords": list(self.keywords),
            "budget": self.budget,
        }


@dataclass(frozen=True)
class ComposerProfile:
    name: str
    genres: List[str] = field(default_factory=list)
    moods: List[str] = field(default_factory=list)
    instruments: List[str] = field(default_factory=list)
    credits: List[str] = field(default_factory=list)
    tracks: List[Dict[str, Any]] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data):
        data = data or {}
        return cls(
            name=str(data.get("name", "") or "").strip(),
            genres=_coerce_string_list(data.get("genres", data.get("genre", []))),
            moods=_coerce_string_list(data.get("moods", data.get("mood", []))),
            instruments=_coerce_string_list(data.get("instruments", [])),
            credits=_coerce_string_list(data.get("credits", [])),
            tracks=list(data.get("tracks") or []),
        )

    def to_dict(self):
        return {
            "name": self.name,
            "genres": list(self.genres),
            "moods": list(self.moods),
            "instruments": list(self.instruments),
            "credits": list(self.credits),
            "tracks": list(self.tracks),
        }


def _coerce_optional_int(value):
    if value in (None, ""):
        return None
    try:
        return int(float(value))
    except (TypeError, ValueError):
        return None


def _coerce_string_list(value):
    if value in (None, ""):
        return []
    if isinstance(value, str):
        values = [value]
    elif isinstance(value, set):
        values = sorted(value, key=str)
    else:
        try:
            values = list(value)
        except TypeError:
            values = [value]

    return [str(item).strip() for item in values if str(item).strip()]
