import json
import math
import struct
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch
import wave

from syncmaster.audio import analyze_audio_file, analyze_audio_intelligence


class SyncMasterAudioTests(unittest.TestCase):
    def test_analyzes_generated_wav_without_optional_dependencies(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "dark_cinematic_120bpm.wav"
            _write_click_wav(audio_path, bpm=120)

            with patch("syncmaster.audio._analyze_with_librosa", return_value=None):
                result = analyze_audio_file(
                    str(audio_path),
                    payload={
                        "title": "Night Lift",
                        "description": "Dark cinematic instrumental cue",
                    },
                )

        json.dumps(result)
        self.assertEqual(result["source"], "audio_file")
        self.assertEqual(result["audio"]["analysis_backend"], "python-wave")
        self.assertEqual(result["audio"]["sample_rate"], 8000)
        self.assertEqual(result["metadata"]["metadata"]["title"], "Night Lift")
        self.assertEqual(result["metadata"]["metadata"]["bpm"], 120)
        self.assertIn("dark", result["metadata"]["metadata"]["mood"])
        self.assertIn("cinematic", result["metadata"]["metadata"]["genre"])
        self.assertIn("model_tagger_disabled", result["warnings"])

    def test_analyzes_wav_with_librosa_backend_when_available(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "dark_cinematic_128bpm.wav"
            _write_click_wav(audio_path, bpm=128)

            with patch(
                "syncmaster.audio._analyze_with_librosa",
                return_value={
                    "path": str(audio_path),
                    "duration_seconds": 2.5,
                    "sample_rate": 22050,
                    "channels": 1,
                    "sample_width_bytes": None,
                    "rms": 0.2,
                    "peak": 0.9,
                    "loudness_dbfs": -12.5,
                    "peak_dbfs": -1.0,
                    "zero_crossing_rate": 0.031,
                    "spectral_centroid_mean": 1400.0,
                    "onset_strength_mean": 0.4,
                    "beat_count": 5,
                    "estimated_bpm": 128,
                    "estimated_key": "C minor",
                    "energy": "high",
                    "analysis_backend": "librosa",
                },
            ):
                result = analyze_audio_file(
                    str(audio_path),
                    payload={"description": "Dark cinematic instrumental cue"},
                )

        json.dumps(result)
        self.assertEqual(result["audio"]["analysis_backend"], "librosa")
        self.assertEqual(result["audio"]["estimated_bpm"], 128)
        self.assertEqual(result["audio"]["estimated_key"], "C minor")
        self.assertEqual(result["metadata"]["metadata"]["bpm"], 128)
        self.assertEqual(result["metadata"]["metadata"]["key"], "C minor")
        self.assertEqual(result["metadata"]["metadata"]["energy"], "high")

    def test_falls_back_to_python_wave_when_librosa_analysis_raises(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = Path(temp_dir) / "dark_cinematic_120bpm.wav"
            _write_click_wav(audio_path, bpm=120)

            with patch("syncmaster.audio._analyze_with_librosa", side_effect=RuntimeError("bad decode")):
                result = analyze_audio_file(
                    str(audio_path),
                    payload={"description": "Dark cinematic instrumental cue"},
                )

        self.assertEqual(result["audio"]["analysis_backend"], "python-wave")
        self.assertEqual(result["audio"]["estimated_bpm"], 120)
        self.assertIn("librosa_analysis_failed:RuntimeError", result["warnings"])
        self.assertEqual(result["metadata"]["metadata"]["bpm"], 120)

    def test_audio_intelligence_metadata_only_fallback(self):
        result = analyze_audio_intelligence(
            {
                "title": "Morning Cue",
                "description": "Uplifting pop 118 bpm instrumental",
                "brief": {"genres": ["pop"], "moods": ["uplifting"], "target_bpm": 118},
            }
        )

        self.assertEqual(result["source"], "metadata_only")
        self.assertEqual(result["metadata"]["metadata"]["bpm"], 118)
        self.assertEqual(result["licensing"]["fit_label"], "strong")
        self.assertIn("audio_path_missing", result["warnings"])


def _write_click_wav(path: Path, bpm: int, seconds: float = 2.5, sample_rate: int = 8000) -> None:
    beat_interval = 60 / bpm
    total_frames = int(seconds * sample_rate)
    samples = []
    for index in range(total_frames):
        t = index / sample_rate
        beat_position = t % beat_interval
        if beat_position < 0.025:
            value = int(22000 * math.sin(2 * math.pi * 880 * t))
        else:
            value = int(800 * math.sin(2 * math.pi * 220 * t))
        samples.append(struct.pack("<h", value))

    with wave.open(str(path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(sample_rate)
        audio.writeframes(b"".join(samples))


if __name__ == "__main__":
    unittest.main()
