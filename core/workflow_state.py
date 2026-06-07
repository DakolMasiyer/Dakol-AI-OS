import json
from dataclasses import dataclass, field, asdict
from typing import Any, Optional

@dataclass
class WorkflowState:
    workflow_id: str
    workflow_version: str
    app_id: str
    current_stage: str
    stage_history: list[str] = field(default_factory=list)
    execution_fingerprint: Optional[str] = None
    stage_fingerprints: dict[str, str] = field(default_factory=dict)
    policy_decisions: list[dict[str, Any]] = field(default_factory=list)
    checkpoint_history: list[dict[str, Any]] = field(default_factory=list)
    failure_state: Optional[dict[str, Any]] = None

    def serialize(self) -> str:
        """Return a replay-safe serialization of the workflow state."""
        return json.dumps(asdict(self), sort_keys=True)

    @classmethod
    def deserialize(cls, data: str) -> "WorkflowState":
        parsed = json.loads(data)
        return cls(**parsed)
