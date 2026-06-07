import json
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Dict

class RubricMutationError(Exception):
    """Raised when an attempt is made to mutate a rubric."""
    pass

@dataclass(frozen=True)
class Rubric:
    rubric_id: str
    rubric_version: str
    section_weights: dict[str, float]
    pass_threshold: float
    grading_rules: dict[str, str] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    def __post_init__(self):
        # Ensure weights sum to 1.0 (or close due to floating point)
        total_weight = sum(self.section_weights.values())
        if abs(total_weight - 1.0) > 0.001:
            raise ValueError("Rubric section_weights must sum to 1.0")
        
        if not (0.0 <= self.pass_threshold <= 1.0):
            raise ValueError("Rubric pass_threshold must be between 0.0 and 1.0")

    def serialize(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    @classmethod
    def deserialize(cls, data: str) -> "Rubric":
        parsed = json.loads(data)
        return cls(**parsed)
