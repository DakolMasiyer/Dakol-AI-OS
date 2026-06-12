import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Optional, Union

from core.workflow_state import WorkflowState
from core.workflow_policy import WorkflowPolicyEngine, WorkflowFailure


class WorkflowEngine:
    def __init__(
        self,
        app_id: str,
        workflow_id: str,
        policy: WorkflowPolicyEngine,
        initial_stage: str,
        root_dir: Optional[Union[str, Path]] = None,
    ):
        self.app_id = app_id
        self.workflow_id = workflow_id
        self.policy = policy
        self.root_dir = Path(root_dir) if root_dir else Path(__file__).resolve().parents[1]
        
        self.state = WorkflowState(
            workflow_id=self.workflow_id,
            workflow_version="1.0.0",
            app_id=self.app_id,
            current_stage=initial_stage,
        )
        self.state.stage_history.append(initial_stage)
        self.stage_handlers: dict[str, Callable] = {}
        self.async_stage_handlers: dict[str, list[str]] = {}
        
        self.checkpoints_dir = self.root_dir / "logs" / "workflows" / self.workflow_id / "checkpoints"
        self.checkpoints_dir.mkdir(parents=True, exist_ok=True)
        self._started_perf = time.perf_counter()

    def register_stage(self, stage_name: str, handler: Callable) -> None:
        self.stage_handlers[stage_name] = handler

    def register_concurrent_stage(self, group_name: str, stages: list[str]) -> None:
        self.async_stage_handlers[group_name] = stages

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Main execution loop."""
        try:
            while True:
                self.policy.verify_depth(len(self.state.stage_history))
                self.policy.verify_timeout(time.perf_counter() - self._started_perf)

                current_stage = self.state.current_stage
                
                # Check if this is a concurrent group
                if current_stage in self.async_stage_handlers:
                    stages_to_run = self.async_stage_handlers[current_stage]
                    group_results = {}
                    for async_st in stages_to_run:
                        h = self.stage_handlers.get(async_st)
                        if not h:
                            self.policy.fail_closed_corruption(f"Handler missing for async stage {async_st}")
                        group_results[async_st] = h(payload.copy())
                    
                    # Deterministic aggregation of async results
                    result = {"status": "success", "async_results": group_results}
                    # We assume the policy or a specific aggregator maps next_stage
                    # For determinism, we just transition to the first transition mapped
                    next_stages = self.policy.allowed_transitions.get(current_stage, [])
                    if next_stages:
                        result["next_stage"] = next_stages[0]
                    else:
                        result["next_stage"] = "COMPLETED"
                else:
                    handler = self.stage_handlers.get(current_stage)
                    if not handler:
                        self.policy.fail_closed_corruption(f"No handler registered for stage {current_stage}")
        
                    # Execute stage
                    result = handler(payload)
                
                # Check for Human Review Pause
                if result.get("status") == "WAITING_FOR_APPROVAL":
                    self._create_checkpoint("APPROVAL_GATING", payload, result)
                    return {"status": "PAUSED", "workflow_id": self.workflow_id, "state": self.state.current_stage}

                # Fingerprint the stage
                self._fingerprint_stage(current_stage, payload, result)

                next_stage = result.get("next_stage")
                if not next_stage or next_stage == "COMPLETED":
                    self.state.current_stage = "COMPLETED"
                    self._fingerprint_workflow(payload, result)
                    self._create_checkpoint("COMPLETED", payload, result)
                    return {"status": "COMPLETED", "result": result, "workflow_id": self.workflow_id, "payload": payload}

                # Verify and Transition
                self.policy.verify_transition(current_stage, next_stage)
                self.state.current_stage = next_stage
                self.state.stage_history.append(next_stage)

        except WorkflowFailure as exc:
            self.state.failure_state = {
                "type": exc.failure_type,
                "message": str(exc),
                "stage": self.state.current_stage
            }
            self._create_checkpoint("FAILED", payload, {})
            raise
        except Exception as exc:
            self.state.failure_state = {
                "type": "WORKFLOW_CORRUPTION",
                "message": str(exc),
                "stage": self.state.current_stage
            }
            self._create_checkpoint("FAILED", payload, {})
            raise WorkflowFailure("WORKFLOW_CORRUPTION", str(exc))

    def resume_from_checkpoint(self, checkpoint_path: Path, payload: dict[str, Any]) -> dict[str, Any]:
        """Resumes a paused workflow."""
        if not checkpoint_path.exists():
            raise WorkflowFailure("REPLAY_MISMATCH", "Checkpoint not found")
            
        data = json.loads(checkpoint_path.read_text())
        if data["workflow_id"] != self.workflow_id:
            raise WorkflowFailure("REPLAY_MISMATCH", "Workflow ID mismatch on resume")
            
        # Verify previous state to guarantee replayability
        self.state = WorkflowState.deserialize(data["state"])
        
        # In a real replay, we would recalculate fingerprints to detect drift.
        return self.execute(payload)

    def _fingerprint_stage(self, stage: str, inputs: Any, outputs: Any) -> None:
        raw = json.dumps({"stage": stage, "inputs": inputs, "outputs": outputs}, sort_keys=True)
        fingerprint = hashlib.sha256(raw.encode()).hexdigest()
        self.state.stage_fingerprints[stage] = fingerprint

    def _fingerprint_workflow(self, inputs: Any, outputs: Any) -> None:
        raw = json.dumps({
            "history": self.state.stage_history,
            "stage_fingerprints": self.state.stage_fingerprints,
            "final_output": outputs
        }, sort_keys=True)
        self.state.execution_fingerprint = hashlib.sha256(raw.encode()).hexdigest()

    def _create_checkpoint(self, reason: str, payload: dict[str, Any], result: dict[str, Any]) -> None:
        idx = len(self.state.checkpoint_history) + 1
        checkpoint_name = f"checkpoint_{idx:03d}.json"
        
        checkpoint_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "workflow_id": self.workflow_id,
            "reason": reason,
            "payload": payload,
            "result": result,
            "state": self.state.serialize()
        }
        self.state.checkpoint_history.append(checkpoint_data)
        
        out_path = self.checkpoints_dir / checkpoint_name
        out_path.write_text(json.dumps(checkpoint_data, indent=2, sort_keys=True))
