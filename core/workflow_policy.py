from typing import Any

class WorkflowFailure(Exception):
    def __init__(self, failure_type: str, message: str):
        super().__init__(f"[{failure_type}] {message}")
        self.failure_type = failure_type

class WorkflowPolicyEngine:
    def __init__(self, allowed_transitions: dict[str, list[str]], max_depth: int = 20):
        self.allowed_transitions = allowed_transitions
        self.max_depth = max_depth

    def verify_transition(self, current_stage: str, next_stage: str) -> None:
        if current_stage not in self.allowed_transitions:
            raise WorkflowFailure("INVALID_TRANSITION", f"Unknown current stage: {current_stage}")
        
        if next_stage not in self.allowed_transitions[current_stage]:
            raise WorkflowFailure(
                "INVALID_TRANSITION", 
                f"Transition from {current_stage} to {next_stage} is explicitly forbidden."
            )

    def verify_depth(self, current_depth: int) -> None:
        if current_depth >= self.max_depth:
            raise WorkflowFailure("POLICY_VIOLATION", f"Max workflow depth exceeded: {self.max_depth}")

    def verify_timeout(self, duration_seconds: float, max_allowed: float = 300.0) -> None:
        if duration_seconds > max_allowed:
            raise WorkflowFailure("EXECUTION_TIMEOUT", f"Execution exceeded maximum timeout of {max_allowed}s.")

    def fail_closed_corruption(self, reason: str) -> None:
        raise WorkflowFailure("WORKFLOW_CORRUPTION", reason)

    def fail_closed_replay_mismatch(self, reason: str) -> None:
        raise WorkflowFailure("REPLAY_MISMATCH", reason)
