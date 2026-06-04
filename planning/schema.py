from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass(frozen=True)
class PlanStep:
    id: str
    description: str
    tool_name: str
    dependencies: List[str] = field(default_factory=list)
    inputs: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=str(data.get("id", "")).strip(),
            description=str(data.get("description", "")).strip(),
            tool_name=str(data.get("tool_name", "")).strip(),
            dependencies=list(data.get("dependencies", [])),
            inputs=dict(data.get("inputs", {})),
        )

    def to_dict(self):
        return {
            "id": self.id,
            "description": self.description,
            "tool_name": self.tool_name,
            "dependencies": list(self.dependencies),
            "inputs": dict(self.inputs),
        }


@dataclass(frozen=True)
class Plan:
    id: str
    objective: str
    steps: List[PlanStep]
    provider: str = "deterministic"

    @classmethod
    def from_dict(cls, data):
        return cls(
            id=str(data.get("id", "")).strip(),
            objective=str(data.get("objective", "")).strip(),
            steps=[PlanStep.from_dict(step) for step in data.get("steps", [])],
            provider=str(data.get("provider", "unknown")).strip(),
        )

    def to_dict(self):
        return {
            "id": self.id,
            "objective": self.objective,
            "provider": self.provider,
            "steps": [step.to_dict() for step in self.steps],
        }
