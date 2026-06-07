import uuid
from typing import Any, Optional

from apps.syncmaster_ai.app import SyncMasterAI
from core.api import WorkflowEngine, WorkflowPolicyEngine

SYNCMASTER_TRANSITIONS = {
    "METADATA_VALIDATION": ["GENRE_CLASSIFICATION"],
    "GENRE_CLASSIFICATION": ["MOOD_ANALYSIS"],
    "MOOD_ANALYSIS": ["SYNC_SCORING"],
    "SYNC_SCORING": ["RECOMMENDATION_GENERATION"],
    "RECOMMENDATION_GENERATION": ["HUMAN_APPROVAL"],
    "HUMAN_APPROVAL": ["REPORT_GENERATION"],
    "REPORT_GENERATION": ["COMPLETED"],
}

class SyncMasterOrchestratedWorkflow:
    def __init__(self, workflow_id: Optional[str] = None):
        self.app = SyncMasterAI()
        self.workflow_id = workflow_id or f"syncmaster-wf-{uuid.uuid4().hex[:8]}"
        
        self.policy = WorkflowPolicyEngine(allowed_transitions=SYNCMASTER_TRANSITIONS)
        self.engine = WorkflowEngine(
            app_id=self.app.manifest.app_id,
            workflow_id=self.workflow_id,
            policy=self.policy,
            initial_stage="METADATA_VALIDATION"
        )
        
        # Register stages
        self.engine.register_stage("METADATA_VALIDATION", self.stage_metadata_validation)
        self.engine.register_stage("GENRE_CLASSIFICATION", self.stage_genre_classification)
        self.engine.register_stage("MOOD_ANALYSIS", self.stage_mood_analysis)
        self.engine.register_stage("SYNC_SCORING", self.stage_sync_scoring)
        self.engine.register_stage("RECOMMENDATION_GENERATION", self.stage_recommendation_generation)
        self.engine.register_stage("HUMAN_APPROVAL", self.stage_human_approval)
        self.engine.register_stage("REPORT_GENERATION", self.stage_report_generation)

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.engine.execute(payload)

    # -------------------
    # STAGES
    # -------------------
    def stage_metadata_validation(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "success", "next_stage": "GENRE_CLASSIFICATION"}

    def stage_genre_classification(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "success", "next_stage": "MOOD_ANALYSIS"}

    def stage_mood_analysis(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "success", "next_stage": "SYNC_SCORING"}

    def stage_sync_scoring(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Orchestrate real tools if needed, but mock deterministically
        return {"status": "success", "score": 95, "next_stage": "RECOMMENDATION_GENERATION"}

    def stage_recommendation_generation(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "success", "next_stage": "HUMAN_APPROVAL"}

    def stage_human_approval(self, payload: dict[str, Any]) -> dict[str, Any]:
        # If payload contains human_approval == True, we proceed. Otherwise pause.
        if payload.get("human_approval") is True:
            return {"status": "APPROVED", "next_stage": "REPORT_GENERATION"}
        return {"status": "WAITING_FOR_APPROVAL", "next_stage": "REPORT_GENERATION"}

    def stage_report_generation(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "success", "report": "Generated Sync Report", "next_stage": "COMPLETED"}
