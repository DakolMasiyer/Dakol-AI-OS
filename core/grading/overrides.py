import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from core.grading.scoring import FinalGrade

@dataclass(frozen=True)
class OverrideRecord:
    original_grade: FinalGrade
    reviewer_id: str
    reasoning: str
    new_final_score: float
    new_passed: bool
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        if not self.reviewer_id:
            raise ValueError("reviewer_id is mandatory for overrides")
        if not self.reasoning:
            raise ValueError("reasoning is mandatory for overrides")
        if not (0.0 <= self.new_final_score <= 1.0):
            raise ValueError("new_final_score must be between 0.0 and 1.0")

    def serialize(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    @classmethod
    def deserialize(cls, data: str) -> "OverrideRecord":
        parsed = json.loads(data)
        # Reconstruct FinalGrade
        original_grade_data = parsed.pop("original_grade")
        parsed["original_grade"] = FinalGrade(**original_grade_data)
        return cls(**parsed)

class OverrideHistory:
    def __init__(self, original_grade: FinalGrade):
        self.original_grade = original_grade
        self.overrides: list[OverrideRecord] = []

    def append_override(self, override: OverrideRecord) -> None:
        """Appends a new override immutably."""
        if override.original_grade != self.original_grade:
            raise ValueError("Override original_grade mismatch")
        self.overrides.append(override)

    def get_finalized_decision(self) -> FinalGrade:
        """Returns the final outcome, factoring in any overrides."""
        if not self.overrides:
            return self.original_grade
        
        latest_override = self.overrides[-1]
        
        # Construct a synthetic FinalGrade for the override
        # We preserve the original section scores but update final_score and passed.
        return FinalGrade(
            rubric_id=self.original_grade.rubric_id,
            rubric_version=self.original_grade.rubric_version,
            section_scores=self.original_grade.section_scores,
            final_score=latest_override.new_final_score,
            passed=latest_override.new_passed
        )

    def serialize(self) -> str:
        return json.dumps({
            "original_grade": asdict(self.original_grade),
            "overrides": [asdict(o) for o in self.overrides]
        }, sort_keys=True)
