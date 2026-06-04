import json
import importlib.util
from pathlib import Path
import unittest
from dataclasses import dataclass


LICENSING_PATH = Path(__file__).resolve().parents[1] / "syncmaster" / "licensing.py"
SPEC = importlib.util.spec_from_file_location("syncmaster_licensing_under_test", LICENSING_PATH)
licensing = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(licensing)
recommend_sync_fit = licensing.recommend_sync_fit


class SyncMasterLicensingTests(unittest.TestCase):
    def test_recommendation_contract_is_json_serializable(self):
        recommendation = recommend_sync_fit(
            {
                "title": "Morning Lift",
                "bpm": 118,
                "genres": ["pop", "indie"],
                "moods": ["uplifting", "bright"],
                "instrumental": True,
                "duration_seconds": 62,
                "one_stop": True,
                "pre_cleared": True,
                "master_owner": "Dakol Music",
                "publishing_owner": "Dakol Publishing",
            },
            {
                "media_type": "brand film",
                "target_moods": ["uplifting", "confident"],
                "genres": ["pop"],
                "min_bpm": 110,
                "max_bpm": 124,
                "duration_seconds": 60,
                "vocal_preference": "instrumental",
                "territory": "Worldwide",
            },
        )

        json.dumps(recommendation)
        self.assertEqual(
            set(recommendation),
            {"fit_score", "usage_suggestions", "clearance_notes", "risks", "reasoning"},
        )
        self.assertGreaterEqual(recommendation["fit_score"], 75)
        self.assertTrue(recommendation["usage_suggestions"])
        self.assertTrue(recommendation["clearance_notes"])
        self.assertTrue(recommendation["risks"])
        self.assertTrue(recommendation["reasoning"])

    def test_recommendation_is_deterministic(self):
        track = {
            "bpm": "96",
            "genres": "hip hop, electronic",
            "moods": ["tense", "dark"],
            "vocals": "vocal",
            "one_stop": False,
        }
        brief = {
            "media_type": "trailer",
            "genres": ["electronic"],
            "moods": ["dark"],
            "target_bpm": 100,
            "vocal_preference": "vocal",
        }

        first = recommend_sync_fit(track, brief)
        second = recommend_sync_fit(track, brief)

        self.assertEqual(first, second)

    def test_samples_and_explicit_content_lower_fit_and_report_risks(self):
        clean = recommend_sync_fit(
            {
                "bpm": 120,
                "genres": ["pop"],
                "moods": ["happy"],
                "instrumental": True,
                "one_stop": True,
            },
            {
                "media_type": "ad",
                "genres": ["pop"],
                "moods": ["happy"],
                "target_bpm": 120,
                "vocal_preference": "instrumental",
            },
        )
        risky = recommend_sync_fit(
            {
                "bpm": 120,
                "genres": ["pop"],
                "moods": ["happy"],
                "instrumental": True,
                "one_stop": True,
                "samples": True,
                "explicit": True,
            },
            {
                "media_type": "ad",
                "genres": ["pop"],
                "moods": ["happy"],
                "target_bpm": 120,
                "vocal_preference": "instrumental",
            },
        )

        self.assertLess(risky["fit_score"], clean["fit_score"])
        self.assertIn("samples", " ".join(risk["note"] for risk in risky["risks"]).lower())
        self.assertIn("explicit", " ".join(risk["note"] for risk in risky["risks"]).lower())

    def test_accepts_dataclass_inputs_without_schema_dependency(self):
        @dataclass
        class Track:
            bpm: int
            genres: list[str]
            moods: list[str]
            instrumental: bool
            one_stop: bool

        @dataclass
        class Brief:
            genres: list[str]
            moods: list[str]
            min_bpm: int
            max_bpm: int
            vocal_preference: str

        recommendation = recommend_sync_fit(
            Track(
                bpm=88,
                genres=["cinematic"],
                moods=["emotional"],
                instrumental=True,
                one_stop=True,
            ),
            Brief(
                genres=["cinematic"],
                moods=["emotional"],
                min_bpm=80,
                max_bpm=95,
                vocal_preference="instrumental",
            ),
        )

        self.assertGreaterEqual(recommendation["fit_score"], 75)


if __name__ == "__main__":
    unittest.main()
