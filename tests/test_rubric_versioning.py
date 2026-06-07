import unittest
from dataclasses import FrozenInstanceError
from core.grading.rubrics import Rubric

class RubricVersioningTests(unittest.TestCase):
    def test_rubric_is_immutable(self):
        rubric = Rubric(
            rubric_id="rubric-1",
            rubric_version="v1",
            section_weights={"A": 1.0},
            pass_threshold=0.8
        )
        
        with self.assertRaises(FrozenInstanceError):
            rubric.rubric_version = "v2"

    def test_rubric_invalid_weights(self):
        with self.assertRaises(ValueError):
            Rubric(
                rubric_id="rubric-2",
                rubric_version="v1",
                section_weights={"A": 0.5, "B": 0.4},  # Sums to 0.9
                pass_threshold=0.8
            )

    def test_rubric_serialization_preserves_version(self):
        rubric = Rubric(
            rubric_id="rubric-1",
            rubric_version="v1",
            section_weights={"A": 1.0},
            pass_threshold=0.8
        )
        data = rubric.serialize()
        restored = Rubric.deserialize(data)
        self.assertEqual(restored.rubric_version, "v1")
        self.assertEqual(restored.created_at, rubric.created_at)
