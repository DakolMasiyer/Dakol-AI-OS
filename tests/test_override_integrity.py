import unittest
from core.grading.rubrics import Rubric
from core.grading.scoring import FinalGrade
from core.grading.overrides import OverrideRecord, OverrideHistory

class OverrideIntegrityTests(unittest.TestCase):
    def setUp(self):
        self.original_grade = FinalGrade(
            rubric_id="rubric-1",
            rubric_version="v1",
            section_scores={"A": 0.5},
            final_score=0.5,
            passed=False
        )

    def test_override_is_append_only(self):
        history = OverrideHistory(self.original_grade)
        
        override = OverrideRecord(
            original_grade=self.original_grade,
            reviewer_id="human-1",
            reasoning="AI missed context X",
            new_final_score=0.9,
            new_passed=True
        )
        
        history.append_override(override)
        
        final_decision = history.get_finalized_decision()
        self.assertEqual(final_decision.final_score, 0.9)
        self.assertTrue(final_decision.passed)
        
        # Original grade must remain completely unchanged
        self.assertEqual(history.original_grade.final_score, 0.5)

    def test_override_requires_reasoning(self):
        with self.assertRaises(ValueError):
            OverrideRecord(
                original_grade=self.original_grade,
                reviewer_id="human-1",
                reasoning="",
                new_final_score=0.9,
                new_passed=True
            )

    def test_override_mismatch_fails(self):
        history = OverrideHistory(self.original_grade)
        
        wrong_grade = FinalGrade("rubric-1", "v1", {"A": 0.9}, 0.9, True)
        override = OverrideRecord(
            original_grade=wrong_grade,
            reviewer_id="human-1",
            reasoning="Mismatch",
            new_final_score=1.0,
            new_passed=True
        )
        
        with self.assertRaises(ValueError):
            history.append_override(override)
