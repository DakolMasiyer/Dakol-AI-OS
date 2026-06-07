import unittest
from core.grading.rubrics import Rubric
from core.grading.scoring import WeightedScoringEngine, SectionScore

class WeightedScoringTests(unittest.TestCase):
    def setUp(self):
        self.rubric = Rubric(
            rubric_id="rubric-1",
            rubric_version="v1",
            section_weights={"A": 0.5, "B": 0.3, "C": 0.2},
            pass_threshold=0.8
        )
        self.engine = WeightedScoringEngine(self.rubric)

    def test_deterministic_scoring(self):
        scores = [
            SectionScore("A", 1.0),
            SectionScore("B", 0.8),
            SectionScore("C", 0.5)
        ]
        # (1.0 * 0.5) + (0.8 * 0.3) + (0.5 * 0.2)
        # 0.5 + 0.24 + 0.10 = 0.84
        result = self.engine.evaluate(scores)
        
        self.assertEqual(result.final_score, 0.84)
        self.assertTrue(result.passed)

    def test_missing_sections_fail(self):
        scores = [SectionScore("A", 1.0)]
        with self.assertRaises(ValueError):
            self.engine.evaluate(scores)

    def test_invalid_score_bounds(self):
        scores = [
            SectionScore("A", 1.5),
            SectionScore("B", 0.8),
            SectionScore("C", 0.5)
        ]
        with self.assertRaises(ValueError):
            self.engine.evaluate(scores)
