import json
import unittest

from syncmaster import MetadataAnalysis, TrackMetadata, analyze_metadata, tag_metadata


class SyncMasterMetadataTests(unittest.TestCase):
    def test_analyzes_structured_payload_and_text_tags(self):
        analysis = analyze_metadata(
            {
                "title": "Night Drive",
                "artist": "Dakol",
                "bpm": "128",
                "key": "c# minor",
                "description": "Dark high energy club track with no vocals.",
                "tags": ["electronic", "tense"],
            }
        )

        self.assertIsInstance(analysis, MetadataAnalysis)
        self.assertEqual(analysis.metadata.title, "Night Drive")
        self.assertEqual(analysis.metadata.artist, "Dakol")
        self.assertEqual(analysis.metadata.bpm, 128)
        self.assertEqual(analysis.metadata.key, "C# minor")
        self.assertEqual(analysis.metadata.energy, "high")
        self.assertEqual(analysis.metadata.vocals, "instrumental")
        self.assertIn("dark", analysis.metadata.mood)
        self.assertIn("electronic", analysis.metadata.genre)

    def test_extracts_metadata_from_free_text(self):
        analysis = analyze_metadata(
            text="Uplifting cinematic orchestral cue, 92 BPM in A major, vocal choir, hopeful and triumphant."
        )

        self.assertEqual(analysis.metadata.bpm, 92)
        self.assertEqual(analysis.metadata.key, "A major")
        self.assertEqual(analysis.metadata.energy, "medium")
        self.assertEqual(analysis.metadata.vocals, "vocal")
        self.assertEqual(analysis.metadata.mood, ["uplifting", "confident"])
        self.assertEqual(analysis.metadata.genre, ["cinematic"])

    def test_explicit_fields_override_text_inference(self):
        analysis = analyze_metadata(
            {
                "bpm": 74,
                "energy": "high",
                "mood": ["calm"],
                "genre": ["folk"],
                "vocals": "instrumental",
                "description": "Fast angry rap vocals at 140 bpm.",
            }
        )

        self.assertEqual(analysis.metadata.bpm, 74)
        self.assertEqual(analysis.metadata.energy, "high")
        self.assertEqual(analysis.metadata.mood, ["calm"])
        self.assertEqual(analysis.metadata.genre, ["folk"])
        self.assertEqual(analysis.metadata.vocals, "instrumental")

    def test_outputs_are_json_serializable_dicts(self):
        output = tag_metadata(
            payload={"tempo": 88, "musical_key": "G maj"},
            tags=["acoustic", "sad", "instrumental"],
        )

        json.dumps(output)
        self.assertEqual(output["metadata"]["bpm"], 88)
        self.assertEqual(output["metadata"]["key"], "G major")
        self.assertEqual(output["metadata"]["genre"], ["folk"])
        self.assertEqual(output["metadata"]["mood"], ["sad"])
        self.assertEqual(output["metadata"]["vocals"], "instrumental")

    def test_schema_round_trips_from_dict(self):
        metadata = TrackMetadata.from_dict(
            {
                "title": "Cue",
                "bpm": "100",
                "mood": "happy",
                "genre": ["pop"],
                "tags": ("bright", "vocal"),
            }
        )
        analysis = MetadataAnalysis.from_dict(
            {
                "metadata": metadata.to_dict(),
                "confidence": {"bpm": 1},
                "matched_terms": {"mood": "happy"},
                "warnings": [],
            }
        )

        self.assertEqual(analysis.metadata.bpm, 100)
        self.assertEqual(analysis.metadata.mood, ["happy"])
        self.assertEqual(analysis.matched_terms["mood"], ["happy"])

    def test_free_text_key_detection_avoids_article_false_positive(self):
        analysis = analyze_metadata(text="A dark cinematic bed with instrumental texture.")

        self.assertEqual(analysis.metadata.key, "")
        self.assertEqual(analysis.metadata.vocals, "instrumental")


if __name__ == "__main__":
    unittest.main()
