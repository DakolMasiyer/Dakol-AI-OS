import json
import unittest
from dataclasses import dataclass
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

MATCHING_PATH = Path(__file__).resolve().parents[1] / "syncmaster" / "matching.py"
MATCHING_SPEC = spec_from_file_location("syncmaster_matching_under_test", MATCHING_PATH)
matching = module_from_spec(MATCHING_SPEC)
MATCHING_SPEC.loader.exec_module(matching)

match_to_brief = matching.match_to_brief
rank_matches = matching.rank_matches


@dataclass
class Track:
    id: str
    title: str
    mood: list[str]
    genre: str
    bpm: int
    instruments: list[str]
    vocals: str
    keywords: list[str]


class SyncMasterMatchingTests(unittest.TestCase):
    def test_ranks_tracks_by_brief_fit(self):
        brief = {
            "mood": ["uplifting", "confident"],
            "genre": "cinematic pop",
            "tempo": "118-126 bpm",
            "instruments": ["piano", "strings"],
            "vocal": "instrumental",
            "keywords": ["launch", "premium"],
        }
        candidates = [
            {
                "id": "track_b",
                "title": "Dark Pulse",
                "mood": ["tense"],
                "genre": "electronic",
                "bpm": 140,
                "instruments": ["synth"],
                "vocal": "vocal",
                "keywords": ["night"],
            },
            {
                "id": "track_a",
                "title": "Open Sky",
                "mood": ["uplifting", "confident"],
                "genre": "cinematic pop",
                "bpm": 122,
                "instruments": ["piano", "strings", "drums"],
                "vocal": "instrumental",
                "keywords": ["premium", "launch", "brand"],
            },
        ]

        matches = match_to_brief(brief, candidates)

        self.assertEqual(matches[0]["rank"], 1)
        self.assertEqual(matches[0]["candidate"]["id"], "track_a")
        self.assertEqual(matches[0]["score"], 100.0)
        self.assertIn("matched mood: confident, uplifting", matches[0]["reasons"])
        self.assertIn("matched tempo: 122 bpm in 118-126", matches[0]["reasons"])
        self.assertLess(matches[1]["score"], matches[0]["score"])

    def test_matches_composer_profile_without_track_schema(self):
        brief = {
            "moods": ["warm"],
            "genres": ["jazz"],
            "tempo_min": 80,
            "tempo_max": 100,
            "instrumentation": ["piano"],
            "voice": "vocal",
            "tags": ["restaurant"],
        }
        composer = {
            "id": "composer_1",
            "name": "Maya Stone",
            "styles": ["jazz", "soul"],
            "moods": ["warm", "intimate"],
            "tempo": 92,
            "instruments": ["piano", "upright bass"],
            "vocals": "female vocal",
            "themes": ["restaurant", "evening"],
            "type": "composer",
        }

        matches = rank_matches(brief, [composer])

        self.assertEqual(matches[0]["candidate"]["name"], "Maya Stone")
        self.assertGreater(matches[0]["score"], 90)
        self.assertIn("matched vocal: vocal", matches[0]["reasons"])

    def test_accepts_dataclass_candidates_and_limits_results(self):
        brief = {"genre": "ambient", "tempo": 70, "vocal": "instrumental"}
        candidates = [
            Track("z", "Zed", ["calm"], "ambient", 70, ["pad"], "instrumental", []),
            Track("a", "Alpha", ["calm"], "ambient", 70, ["pad"], "instrumental", []),
            Track("b", "Beta", ["calm"], "rock", 130, ["guitar"], "vocal", []),
        ]

        matches = match_to_brief(brief, candidates, limit=2)

        self.assertEqual([match["candidate"]["id"] for match in matches], ["a", "z"])
        self.assertEqual([match["rank"] for match in matches], [1, 2])

    def test_output_is_json_serializable(self):
        brief = {"keywords": ["sync", "brand"]}
        candidates = [{"id": "one", "keywords": {"primary": "sync brand"}}]

        matches = match_to_brief(brief, candidates)

        encoded = json.dumps(matches, sort_keys=True)
        self.assertIn('"score"', encoded)
        self.assertIn('"reasons"', encoded)


if __name__ == "__main__":
    unittest.main()
