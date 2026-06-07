import uuid
from typing import Any, Optional

from apps.listening_farm_ai.app import ListeningFarmAI
from core.api import WorkflowEngine, WorkflowPolicyEngine

LISTENING_FARM_TRANSITIONS = {
    "METADATA_EXTRACTION": ["TREND_ANALYSIS"],
    "TREND_ANALYSIS": ["SIMILARITY_SCORING"],
    "SIMILARITY_SCORING": ["RECOMMENDATION_SIMULATION"],
    "RECOMMENDATION_SIMULATION": ["SIGNAL_RANKING"],
    "SIGNAL_RANKING": ["COMPLETED"],
}

class ListeningFarmWorkflow:
    def __init__(self, workflow_id: Optional[str] = None):
        self.app = ListeningFarmAI()
        self.workflow_id = workflow_id or f"listenfarm-wf-{uuid.uuid4().hex[:8]}"
        
        self.policy = WorkflowPolicyEngine(allowed_transitions=LISTENING_FARM_TRANSITIONS)
        self.engine = WorkflowEngine(
            app_id=self.app.manifest.app_id,
            workflow_id=self.workflow_id,
            policy=self.policy,
            initial_stage="METADATA_EXTRACTION"
        )
        
        self.engine.register_stage("METADATA_EXTRACTION", self.stage_metadata_extraction)
        self.engine.register_stage("TREND_ANALYSIS", self.stage_trend_analysis)
        self.engine.register_stage("SIMILARITY_SCORING", self.stage_similarity_scoring)
        self.engine.register_stage("RECOMMENDATION_SIMULATION", self.stage_recommendation_simulation)
        self.engine.register_stage("SIGNAL_RANKING", self.stage_signal_ranking)

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.engine.execute(payload)

    def stage_metadata_extraction(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "success", "next_stage": "TREND_ANALYSIS"}

    def stage_trend_analysis(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "success", "next_stage": "SIMILARITY_SCORING"}

    def stage_similarity_scoring(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "success", "next_stage": "RECOMMENDATION_SIMULATION"}

    def stage_recommendation_simulation(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "success", "next_stage": "SIGNAL_RANKING"}

    def stage_signal_ranking(self, payload: dict[str, Any]) -> dict[str, Any]:
        return {"status": "success", "report": "Ranked Signals", "next_stage": "COMPLETED"}
