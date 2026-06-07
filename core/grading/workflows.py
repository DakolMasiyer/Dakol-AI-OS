import uuid
from typing import Any, Optional
from pathlib import Path
from dataclasses import asdict
from core.api import WorkflowEngine, WorkflowPolicyEngine
from core.grading.rubrics import Rubric
from core.grading.scoring import WeightedScoringEngine, SectionScore, FinalGrade

GRADING_TRANSITIONS = {
    "SUBMISSION_RECEIVED": ["RUBRIC_VALIDATION"],
    "RUBRIC_VALIDATION": ["SECTION_SCORING"],
    "SECTION_SCORING": ["FINAL_SCORE_AGGREGATION"],
    "FINAL_SCORE_AGGREGATION": ["PASS_FAIL_EVALUATION"],
    "PASS_FAIL_EVALUATION": ["REVIEW_CHECKPOINT"],
    "REVIEW_CHECKPOINT": ["GRADE_FINALIZATION"],
    "GRADE_FINALIZATION": ["COMPLETED"],
}

class GradingWorkflow:
    def __init__(self, rubric: Rubric, workflow_id: Optional[str] = None, root_dir: Optional[Path] = None):
        self.rubric = rubric
        self.workflow_id = workflow_id or f"grading-wf-{uuid.uuid4().hex[:8]}"
        
        self.policy = WorkflowPolicyEngine(allowed_transitions=GRADING_TRANSITIONS)
        self.engine = WorkflowEngine(
            app_id="core.grading",
            workflow_id=self.workflow_id,
            policy=self.policy,
            initial_stage="SUBMISSION_RECEIVED",
            root_dir=root_dir
        )
        self.scoring_engine = WeightedScoringEngine(self.rubric)
        
        self.engine.register_stage("SUBMISSION_RECEIVED", self.stage_submission_received)
        self.engine.register_stage("RUBRIC_VALIDATION", self.stage_rubric_validation)
        self.engine.register_stage("SECTION_SCORING", self.stage_section_scoring)
        self.engine.register_stage("FINAL_SCORE_AGGREGATION", self.stage_final_score_aggregation)
        self.engine.register_stage("PASS_FAIL_EVALUATION", self.stage_pass_fail_evaluation)
        self.engine.register_stage("REVIEW_CHECKPOINT", self.stage_review_checkpoint)
        self.engine.register_stage("GRADE_FINALIZATION", self.stage_grade_finalization)

    def execute(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self.engine.execute(payload)

    def stage_submission_received(self, payload: dict[str, Any]) -> dict[str, Any]:
        if "submission_id" not in payload:
            raise ValueError("submission_id is required")
        return {"status": "success", "next_stage": "RUBRIC_VALIDATION"}

    def stage_rubric_validation(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Validate that the requested rubric version matches our engine's rubric
        if payload.get("rubric_version") and payload["rubric_version"] != self.rubric.rubric_version:
            raise ValueError("Rubric version mismatch")
        return {"status": "success", "next_stage": "SECTION_SCORING"}

    def stage_section_scoring(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Mocked or deterministic scoring would happen here
        # For evaluation, we expect payload["section_scores"] to exist
        return {"status": "success", "next_stage": "FINAL_SCORE_AGGREGATION"}

    def stage_final_score_aggregation(self, payload: dict[str, Any]) -> dict[str, Any]:
        scores = payload.get("section_scores", [])
        section_scores = [SectionScore(section_id=k, score=v) for k, v in scores.items()]
        
        final_grade = self.scoring_engine.evaluate(section_scores)
        payload["final_grade"] = asdict(final_grade)
        
        return {"status": "success", "next_stage": "PASS_FAIL_EVALUATION"}

    def stage_pass_fail_evaluation(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Log the threshold result
        return {"status": "success", "next_stage": "REVIEW_CHECKPOINT"}

    def stage_review_checkpoint(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Always yield for review if human override is needed, otherwise proceed
        if payload.get("requires_review"):
            if payload.get("human_reviewed"):
                return {"status": "APPROVED", "next_stage": "GRADE_FINALIZATION"}
            return {"status": "WAITING_FOR_APPROVAL", "next_stage": "GRADE_FINALIZATION"}
        return {"status": "success", "next_stage": "GRADE_FINALIZATION"}

    def stage_grade_finalization(self, payload: dict[str, Any]) -> dict[str, Any]:
        # Final trace generation
        return {"status": "success", "final_grade": payload["final_grade"], "next_stage": "COMPLETED"}
