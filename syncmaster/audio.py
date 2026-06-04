"""Real-audio analysis for SyncMaster.

The analyzer is local-first and dependency-safe:
- WAV/AIFF files are analyzed with the Python standard library.
- Other formats are converted with ffmpeg when it is installed.
- Optional model tagging is exposed through env-gated hooks and falls back
  without breaking the core metadata pipeline.
"""

from __future__ import annotations

import audioop
import importlib.util
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import wave
from typing import Any

from syncmaster.licensing import recommend_licensing
from syncmaster.metadata import tag_metadata


SUPPORTED_PCM_EXTENSIONS = {".wav", ".wave"}
DEFAULT_SAMPLE_RATE = 22050


def analyze_audio_file(audio_path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Analyze a local audio file and return JSON-serializable features."""

    path = Path(audio_path).expanduser()
    payload = dict(payload or {})
    warnings: list[str] = []

    if not path.is_file():
        raise ValueError(f"Audio file not found: {audio_path}")

    features = _analyze_with_best_backend(path, warnings)

    inferred_payload = _payload_from_features(path, payload, features)
    metadata = tag_metadata(payload=inferred_payload)
    model_tags = analyze_audio_with_optional_model(path, features, metadata)

    if model_tags.get("warnings"):
        warnings.extend(model_tags["warnings"])

    return {
        "audio": features,
        "metadata": metadata,
        "model_tags": model_tags,
        "warnings": _unique(warnings),
        "source": "audio_file",
    }


def analyze_audio_intelligence(payload: dict[str, Any]) -> dict[str, Any]:
    """Combine audio features, metadata, and optional licensing fit."""

    payload = dict(payload or {})
    audio_path = payload.get("audio_path") or payload.get("file_path") or payload.get("path")
    brief = payload.get("brief") or {}

    if audio_path:
        analysis = analyze_audio_file(str(audio_path), payload=payload)
        track = analysis["metadata"]["metadata"]
    else:
        analysis = {
            "audio": None,
            "metadata": tag_metadata(payload=payload),
            "model_tags": analyze_audio_with_optional_model(None, {}, {}),
            "warnings": ["audio_path_missing"],
            "source": "metadata_only",
        }
        track = analysis["metadata"]["metadata"]

    recommendation = recommend_licensing(track, brief) if brief else None

    return {
        **analysis,
        "licensing": recommendation,
        "summary": _summary(track, analysis.get("audio"), recommendation),
    }


def analyze_audio_with_optional_model(
    audio_path: str | Path | None,
    features: dict[str, Any],
    metadata: dict[str, Any],
) -> dict[str, Any]:
    """Optional Phase 8B model hook.

    The default is intentionally disabled so local tests and deployments do not
    download large models. Set SYNCMASTER_AUDIO_TAGGER=huggingface after adding
    transformers/torch and a compatible model to enable this path later.
    """

    provider = os.getenv("SYNCMASTER_AUDIO_TAGGER", "none").strip().lower()
    if provider in {"", "none", "disabled"}:
        return {
            "provider": "none",
            "tags": [],
            "confidence": {},
            "warnings": ["model_tagger_disabled"],
        }

    if provider != "huggingface":
        return {
            "provider": provider,
            "tags": [],
            "confidence": {},
            "warnings": [f"unsupported_model_tagger:{provider}"],
        }

    if shutil.which("python3") is None:
        return {
            "provider": "huggingface",
            "tags": [],
            "confidence": {},
            "warnings": ["python3_unavailable_for_model_tagger"],
        }

    # Keep this hook dependency-safe until a specific HF model is selected.
    return {
        "provider": "huggingface",
        "model": os.getenv("SYNCMASTER_HF_AUDIO_MODEL", ""),
        "tags": [],
        "confidence": {},
        "warnings": ["huggingface_model_hook_not_configured"],
    }


def _convert_to_wav(path: Path, warnings: list[str]) -> Path | None:
    ffmpeg = shutil.which(os.getenv("FFMPEG_BINARY", "ffmpeg"))
    if not ffmpeg:
        warnings.append("ffmpeg_unavailable_non_wav_analysis_limited")
        return None

    output = Path(tempfile.NamedTemporaryFile(suffix=".wav", delete=False).name)
    command = [
        ffmpeg,
        "-y",
        "-i",
        str(path),
        "-ac",
        "1",
        "-ar",
        str(DEFAULT_SAMPLE_RATE),
        "-f",
        "wav",
        str(output),
    ]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True, timeout=60)
        warnings.append("audio_converted_with_ffmpeg")
        return output
    except (subprocess.SubprocessError, OSError) as exc:
        warnings.append(f"ffmpeg_conversion_failed:{exc.__class__.__name__}")
        try:
            output.unlink()
        except OSError:
            pass
        return None


def _analyze_with_best_backend(path: Path, warnings: list[str]) -> dict[str, Any]:
    backend = os.getenv("SYNCMASTER_AUDIO_BACKEND", "auto").strip().lower()
    if backend not in {"auto", "librosa", "wave", "python-wave"}:
        warnings.append(f"unsupported_audio_backend:{backend}")
        backend = "auto"

    if backend in {"auto", "librosa"}:
        try:
            features = _analyze_with_librosa(path, warnings)
            if features is not None:
                return features
        except Exception as exc:
            warnings.append(f"librosa_analysis_failed:{exc.__class__.__name__}")
        if backend == "librosa":
            warnings.append("librosa_backend_requested_but_unavailable")

    working_path = path
    converted_path: Path | None = None
    if path.suffix.lower() not in SUPPORTED_PCM_EXTENSIONS:
        converted_path = _convert_to_wav(path, warnings)
        if converted_path is not None:
            working_path = converted_path

    try:
        return _analyze_pcm_wav(working_path, warnings)
    finally:
        if converted_path is not None:
            try:
                converted_path.unlink()
            except OSError:
                pass


def _analyze_with_librosa(path: Path, warnings: list[str]) -> dict[str, Any] | None:
    if importlib.util.find_spec("librosa") is None:
        warnings.append("librosa_unavailable")
        return None

    try:
        import librosa  # type: ignore
        import numpy as np  # type: ignore

        samples, sample_rate = librosa.load(str(path), sr=None, mono=True)
        if samples.size == 0:
            warnings.append("librosa_empty_audio")
            return None

        duration = float(librosa.get_duration(y=samples, sr=sample_rate))
        rms_values = librosa.feature.rms(y=samples)[0]
        centroid_values = librosa.feature.spectral_centroid(y=samples, sr=sample_rate)[0]
        zcr_values = librosa.feature.zero_crossing_rate(samples)[0]
        onset_envelope = librosa.onset.onset_strength(y=samples, sr=sample_rate)
        tempo_raw, beats = librosa.beat.beat_track(y=samples, sr=sample_rate, onset_envelope=onset_envelope)
        tempo = _coerce_tempo(tempo_raw)
        loudness_dbfs = _dbfs(float(np.sqrt(np.mean(np.square(samples)))), 1.0)
        peak = float(np.max(np.abs(samples)))

        energy = "low"
        rms_mean = float(np.mean(rms_values)) if rms_values.size else 0.0
        if loudness_dbfs > -18 or rms_mean > 0.15 or (tempo is not None and tempo >= 125):
            energy = "high"
        elif loudness_dbfs > -32 or rms_mean > 0.04 or (tempo is not None and tempo >= 90):
            energy = "medium"

        return {
            "path": str(path),
            "duration_seconds": round(duration, 3),
            "sample_rate": int(sample_rate),
            "channels": 1,
            "sample_width_bytes": None,
            "rms": round(rms_mean, 6),
            "peak": round(peak, 6),
            "loudness_dbfs": round(loudness_dbfs, 2),
            "peak_dbfs": round(_dbfs(peak, 1.0), 2),
            "zero_crossing_rate": round(float(np.mean(zcr_values)), 5) if zcr_values.size else 0.0,
            "spectral_centroid_mean": round(float(np.mean(centroid_values)), 3) if centroid_values.size else 0.0,
            "onset_strength_mean": round(float(np.mean(onset_envelope)), 6) if onset_envelope.size else 0.0,
            "beat_count": int(len(beats)),
            "estimated_bpm": tempo,
            "estimated_key": "",
            "energy": energy,
            "analysis_backend": "librosa",
        }
    except Exception as exc:  # pragma: no cover - exact failures depend on optional audio stack.
        warnings.append(f"librosa_analysis_failed:{exc.__class__.__name__}")
        return None


def _analyze_pcm_wav(path: Path, warnings: list[str]) -> dict[str, Any]:
    try:
        with wave.open(str(path), "rb") as audio:
            channels = audio.getnchannels()
            sample_rate = audio.getframerate()
            sample_width = audio.getsampwidth()
            frame_count = audio.getnframes()
            frames = audio.readframes(frame_count)
    except (wave.Error, EOFError) as exc:
        raise ValueError(f"Unsupported audio file for local analysis: {path}") from exc

    duration = frame_count / sample_rate if sample_rate else 0.0
    mono = audioop.tomono(frames, sample_width, 0.5, 0.5) if channels > 1 else frames
    rms = audioop.rms(mono, sample_width) if mono else 0
    peak = audioop.max(mono, sample_width) if mono else 0
    max_amplitude = float(2 ** (8 * sample_width - 1))
    loudness_dbfs = _dbfs(rms, max_amplitude)
    peak_dbfs = _dbfs(peak, max_amplitude)
    zero_crossing_rate = audioop.cross(mono, sample_width) / max(1, frame_count)
    tempo = _estimate_tempo(mono, sample_width, sample_rate)

    energy = "low"
    if loudness_dbfs > -18 or (tempo is not None and tempo >= 125):
        energy = "high"
    elif loudness_dbfs > -32 or (tempo is not None and tempo >= 90):
        energy = "medium"

    return {
        "path": str(path),
        "duration_seconds": round(duration, 3),
        "sample_rate": sample_rate,
        "channels": channels,
        "sample_width_bytes": sample_width,
        "rms": rms,
        "peak": peak,
        "loudness_dbfs": round(loudness_dbfs, 2),
        "peak_dbfs": round(peak_dbfs, 2),
        "zero_crossing_rate": round(zero_crossing_rate, 5),
        "estimated_bpm": tempo,
        "estimated_key": "",
        "energy": energy,
        "analysis_backend": "python-wave",
    }


def _estimate_tempo(mono: bytes, sample_width: int, sample_rate: int) -> int | None:
    if not mono or not sample_rate:
        return None

    window_size = max(1, sample_rate // 20)
    byte_width = sample_width
    frame_count = len(mono) // byte_width
    if frame_count < window_size * 4:
        return None

    energies: list[float] = []
    for start in range(0, frame_count - window_size, window_size):
        chunk = mono[start * byte_width:(start + window_size) * byte_width]
        energies.append(float(audioop.rms(chunk, sample_width)))

    if len(energies) < 8:
        return None

    threshold = (sum(energies) / len(energies)) * 1.35
    peaks = [
        index
        for index, value in enumerate(energies[1:-1], start=1)
        if value > threshold and value >= energies[index - 1] and value >= energies[index + 1]
    ]
    if len(peaks) < 2:
        return None

    intervals = [right - left for left, right in zip(peaks, peaks[1:]) if right > left]
    if not intervals:
        return None

    median_interval = sorted(intervals)[len(intervals) // 2]
    seconds_per_interval = median_interval * (window_size / sample_rate)
    if seconds_per_interval <= 0:
        return None

    bpm = round(60 / seconds_per_interval)
    while bpm < 60:
        bpm *= 2
    while bpm > 180:
        bpm = round(bpm / 2)
    return int(bpm) if 40 <= bpm <= 220 else None


def _payload_from_features(path: Path, payload: dict[str, Any], features: dict[str, Any]) -> dict[str, Any]:
    merged = dict(payload)
    merged.setdefault("title", path.stem.replace("_", " ").replace("-", " "))
    if features.get("estimated_bpm") is not None:
        merged.setdefault("bpm", features["estimated_bpm"])
    if features.get("estimated_key"):
        merged.setdefault("key", features["estimated_key"])
    if features.get("energy") != "unknown":
        merged.setdefault("energy", features["energy"])
    merged.setdefault("duration_seconds", features.get("duration_seconds"))
    merged.setdefault("source_text", "")
    return merged


def _dbfs(amplitude: int | float, max_amplitude: float) -> float:
    if amplitude <= 0 or max_amplitude <= 0:
        return -120.0
    return 20 * math.log10(float(amplitude) / max_amplitude)


def _coerce_tempo(value) -> int | None:
    try:
        if hasattr(value, "__len__") and not isinstance(value, (str, bytes)):
            if len(value) == 0:
                return None
            value = value[0]
        tempo = round(float(value))
    except (TypeError, ValueError):
        return None

    while tempo < 60:
        tempo *= 2
    while tempo > 180:
        tempo = round(tempo / 2)
    return int(tempo) if 40 <= tempo <= 220 else None


def _summary(track: dict[str, Any], audio: dict[str, Any] | None, recommendation) -> str:
    parts = [track.get("title") or "Untitled track"]
    if track.get("bpm"):
        parts.append(f"{track['bpm']} BPM")
    elif audio and audio.get("estimated_bpm"):
        parts.append(f"{audio['estimated_bpm']} BPM estimated")
    if audio and audio.get("duration_seconds"):
        parts.append(f"{audio['duration_seconds']}s")
    if track.get("genre"):
        parts.append(", ".join(track["genre"]))
    if track.get("mood"):
        parts.append("mood: " + ", ".join(track["mood"]))
    if recommendation:
        parts.append(f"sync fit: {recommendation['fit_label']}")
    return " | ".join(parts)


def _unique(values: list[str]) -> list[str]:
    return list(dict.fromkeys(values))


def dumps_compact(value: Any) -> str:
    return json.dumps(value, separators=(",", ":"), sort_keys=True)
