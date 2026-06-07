from dataclasses import dataclass, asdict
from typing import Dict
from core.grading.rubrics import Rubric

@dataclass(frozen=True)
class SectionScore:
    section_id: str
    score: float  # Expected between 0.0 and 1.0

@dataclass(frozen=True)
class FinalGrade:
    rubric_id: str
    rubric_version: str
    section_scores: dict[str, float]
    final_score: float
    passed: bool

class WeightedScoringEngine:
    def __init__(self, rubric: Rubric):
        self.rubric = rubric

    def evaluate(self, section_scores: list[SectionScore]) -> FinalGrade:
        """
        Deterministically evaluates section scores against the rubric.
        Fails if there are missing or extraneous sections.
        """
        score_map = {s.section_id: s.score for s in section_scores}
        
        # Verify complete set of sections
        rubric_sections = set(self.rubric.section_weights.keys())
        provided_sections = set(score_map.keys())
        
        if rubric_sections != provided_sections:
            missing = rubric_sections - provided_sections
            extra = provided_sections - rubric_sections
            raise ValueError(f"Section mismatch. Missing: {missing}, Extra: {extra}")

        # Compute weighted total
        total = 0.0
        for section_id, score in score_map.items():
            if not (0.0 <= score <= 1.0):
                raise ValueError(f"Score for {section_id} must be between 0.0 and 1.0")
            weight = self.rubric.section_weights[section_id]
            total += score * weight

        # Normalize and round deterministically (round to 4 decimal places)
        final_score = round(total, 4)
        passed = final_score >= self.rubric.pass_threshold

        return FinalGrade(
            rubric_id=self.rubric.rubric_id,
            rubric_version=self.rubric.rubric_version,
            section_scores=score_map,
            final_score=final_score,
            passed=passed
        )
